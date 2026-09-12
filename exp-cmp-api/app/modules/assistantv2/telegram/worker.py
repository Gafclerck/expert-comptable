"""Worker de polling Telegram pour l'assistant v2 (process dedie).

- `get_updates` en long polling ; l'offset n'est avance qu'apres traitement
  du lot (update_id + 1).
- **Exactly-once** : le journal `TelegramMessage` (unicite sur `update_id`)
  est enregistre AVANT toute execution, pour qu'un crash entre execution et
  ack (re-delivrance par Telegram) ne provoque jamais de double
  comptabilisation. Contre-partie acceptee : un crash a cet instant perd la
  commande (jamais verifiee deux fois).
- Commande `/start <TOKEN>` = liaison deep-link ; lookup `chat_id -> user
  actif` ; delegation a `assistantv2_service.chat`, sessions `tg:<chat_id>`
  persistees dans Redis (session_store).
- Reproduit le cablage evenements de `app.main` (attach_audit_listeners /
  attach_ledger_listeners) : le bus est par processus, sans cela aucun audit
  ne serait persist pour les commandes venues de Telegram.

Lancer : python -m app.modules.assistantv2.telegram (depuis exp-cmp-api/).
"""
import logging
import signal
import time
from threading import Lock

import httpx

from app.core.db import session as session_factory
from app.modules.assistantv2 import service as assistantv2_service
from app.modules.assistantv2 import session_store
from app.modules.assistantv2.telegram import service as telegram_service
from app.modules.assistantv2.telegram.client import TelegramAPIError, TelegramClient
from app.modules.assistantv2.telegram.models import TelegramMessage
from app.modules.identity.models import User, UserStatus
from sqlalchemy import func

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_MESSAGE_CHARS = 1000  # ChatIn.max_length du moteur v2
MAX_CHUNK_CHARS = 4096  # limite API Telegram (sendMessage)
MAX_SEND_ATTEMPTS = 3  # retries d'envoi bornes (429/retry_after, reseau)

_HELP = (
    "Assistant comptable. Commandes :\n"
    "/start <TOKEN> : lier ton compte (token genere dans le back-office)\n"
    "/aide : cette aide\n"
    "/stop : reinitialiser la conversation\n"
    "Pose ensuite ta question en langage naturel "
    "(ex. \"solde de la caisse assurance\")."
)

_NOT_LINKED = (
    "Compte non lie. Rends-toi dans le back-office, genere un token de "
    "liaison puis envoie /start <TOKEN>."
)

_OFFSET_KEY = "assistantv2:telegram:offset"


def _split_chunks(text: str, size: int = MAX_CHUNK_CHARS) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def _private_chat(update: dict) -> dict | None:
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return None
    if not chat.get("id"):
        return None
    return chat


class TelegramWorker:
    """Point d'entree du worker : cycle get_updates + dispatch message."""

    def __init__(self, client: TelegramClient | None = None):
        self.client = client or TelegramClient()
        self._locks: dict[int, Lock] = {}
        self._locks_guard = Lock()
        self._stopped = False

    # -- cycle de polling ----------------------------------------------------

    def run_forever(self) -> int:
        self._attach_listeners()
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "_stopped", True))
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "_stopped", True))
        while not self._stopped:
            try:
                processed = self.run_once()
            except httpx.HTTPStatusError as exc:
                # Bug 2 : token rejete en cours de route (revocation...).
                # Pas de boucle qui poll en 401 : on sort (code 2) et la
                # supervision du processus decide de la reprise.
                if exc.response.status_code == 401:
                    logger.error("Token Telegram rejete par l'API (401) : arret du worker.")
                    return 2
                logger.warning("Erreur HTTP Telegram : %s", exc)
                time.sleep(2)
                continue
            except TelegramAPIError as exc:
                retry_after = exc.parameters.get("retry_after")
                if "unauthorized" in str(exc.description).lower():
                    logger.error("Token Telegram rejete par l'API : arret du worker.")
                    return 2
                logger.error("getUpdates refuse par Telegram : %s", exc.description)
                time.sleep(min(int(retry_after) if retry_after else 5, 30))
                continue
            except httpx.HTTPError as exc:
                logger.warning("Reseau Telegram indisponible : %s", exc)
                time.sleep(2)
                continue
            if processed == 0:
                time.sleep(0.2)
        logger.info("Worker arrete proprement.")
        return 0

    def run_once(self) -> int:
        """Un cycle getUpdates : traite chaque update puis avance l'offset.
        En cas d'echec de traitement, l'offset n'est PAS avance (bug 4) afin
        que Telegram re-livre l'update au cycle suivant, et le reste du lot
        est abandonne pour cette fois (re-essai avec le meme offset)."""
        updates = self.client.get_updates(offset=self._load_offset())
        processed = 0
        for update in updates:
            update_id = int(update.get("update_id") or 0)
            try:
                self.handle_update(update)
            except Exception:
                logger.exception(
                    "Update %s non traite : offset non avance, re-essai au prochain cycle",
                    update_id,
                )
                break
            self._save_offset(update_id + 1)
            processed += 1
        return processed

    def handle_update(self, update: dict) -> None:
        """Traite UN update : dedup exactement-une-fois + dispatch. Public
        pour les tests (aucun reseau requis en dehors du client injecte)."""
        update_id = int(update.get("update_id") or 0)
        chat = _private_chat(update)
        if chat is None:
            return
        chat_id = int(chat["id"])
        with self._lock_for(chat_id):
            if self._is_processed(update_id):
                return
            message = update.get("message") or {}
            sender = message.get("from") or {}
            self._record_in(update_id, chat_id, message.get("message_id"))
            text = str(message.get("text") or message.get("caption") or "").strip()
            self._dispatch(chat_id, text, sender)

    # -- dispatch ------------------------------------------------------------

    def _dispatch(self, chat_id: int, text: str, sender: dict) -> None:
        if not text:
            self._send(chat_id, "Message vide ignore.")
        elif text.startswith("/start"):
            self._handle_start(chat_id, text, sender)
        elif text in ("/aide", "/help"):
            self._send(chat_id, _HELP)
        elif text == "/stop":
            try:
                session_store.delete_plan(telegram_service.session_id_for(chat_id))
            except Exception:
                logger.warning("Redis indisponible : session non purgee")
            self._send(chat_id, "Conversation reinitialisee.")
        else:
            self._chat(chat_id, text)

    def _handle_start(self, chat_id: int, text: str, sender: dict) -> None:
        parts = text.split(None, 1)
        token = parts[1].strip() if len(parts) > 1 else ""
        if not token:
            self._send(chat_id, _HELP)
            return
        db = session_factory()
        try:
            # Bug 6 : on valide le compte SANS consommer le token, pour ne pas
            # bruler un token inutilisable (compte inactif) -> l'utilisateur
            # peut reagir apres reactivation sans en regenerer un.
            record = telegram_service.find_link_token(db, token)
            if record is None:
                self._send(chat_id, "Token invalide, expire ou deja utilise.")
                return
            user = db.get(User, record.user_id)
            if user is None or user.status != UserStatus.ACTIVE:
                self._send(chat_id, "Le compte associe au token est introuvable ou inactif.")
                return
            consumed = telegram_service.consume_link_token(db, token)
            binding = telegram_service.create_binding(
                db,
                chat_id,
                token=consumed,
                tg_username=sender.get("username"),
                tg_user_id=sender.get("id"),
            )
            self._send(chat_id, "Compte lie. Pose ta question ou envoie /aide.")
        finally:
            db.close()

    def _chat(self, chat_id: int, text: str) -> None:
        db = session_factory()
        try:
            binding = telegram_service.get_active_binding(db, chat_id)
            if binding is None:
                self._send(chat_id, _NOT_LINKED)
                return
            user = db.get(User, binding.user_id)
            if user is None or user.status != UserStatus.ACTIVE:
                self._send(chat_id, "Ton compte est inactif ou introuvable.")
                return
            reply = assistantv2_service.chat(
                db,
                user,
                text[:MAX_MESSAGE_CHARS],
                telegram_service.session_id_for(chat_id),
            )
            telegram_service.touch_last_seen(db, binding)
        except Exception as exc:
            # Bug 3 corrige : un echec d'envoi en aval ne doit pas remonter
            # ici (le detail de l'erreur reste dans les logs serveur, jamais
            # expose a l'utilisateur du bot).
            logger.exception("Erreur lors du traitement du message")
            self._send(chat_id, "Une erreur interne est survenue. Reessaie ou utilise l'application web.")
            return
        finally:
            db.close()
        self._send(chat_id, reply.text)

    def _send(self, chat_id: int, text: str) -> None:
        for chunk in _split_chunks(text):
            self._send_chunk(chat_id, chunk)

    def _send_chunk(self, chat_id: int, message: str) -> None:
        """Envoie avec retries bornes et conscients de `retry_after` (Phase 2 :
        anti 429/flood de la Bot API). Ne leve JAMAIS (bug 3) : un echec final
        est logue, jamais propage a run_once (sinon Telegram re-livrerait un
        update deja journalise -> succes silencieux)."""
        attempts = 0
        while True:
            attempts += 1
            try:
                self.client.send_message(chat_id, message)
                return
            except TelegramAPIError as exc:
                retry_after = exc.parameters.get("retry_after")
                if retry_after is not None and attempts < MAX_SEND_ATTEMPTS:
                    try:
                        wait = min(int(retry_after), 30)
                    except (TypeError, ValueError):
                        wait = 5
                    time.sleep(wait)
                    continue
                logger.error(
                    "Envoi Telegram refuse apres %s tentative(s) : %s",
                    attempts,
                    exc.description,
                )
                return
            except httpx.HTTPError as exc:
                if attempts >= MAX_SEND_ATTEMPTS:
                    logger.error(
                        "Envoi Telegram indisponible apres %s tentative(s) : %s",
                        attempts,
                        exc,
                    )
                    return
                time.sleep(1)

    # -- exactly-once --------------------------------------------------------

    @staticmethod
    def _is_processed(update_id: int) -> bool:
        db = session_factory()
        try:
            return telegram_service.is_already_processed(db, update_id)
        finally:
            db.close()

    @staticmethod
    def _record_in(update_id: int, chat_id: int, message_id: int | None) -> None:
        db = session_factory()
        try:
            telegram_service.record_message(
                db, chat_id=chat_id, update_id=update_id, message_id=message_id, direction="in"
            )
        finally:
            db.close()

    # -- offset persiste (Redis, best-effort) --------------------------------

    def _load_offset(self) -> int | None:
        """Offset persiste dans Redis si present ; sinon reprise depuis le
        journal SQL (max(update_id) + 1). Recouvre la perte de Redis sans
        rejouer 24h d'updates (le journal les de-dupliquerait de toute facon)."""
        offset: int | None = None
        try:
            raw = session_store.get_redis_client().get(_OFFSET_KEY)
            offset = int(raw) if raw is not None else None
        except Exception:
            offset = None
        if offset is None:
            offset = self._journal_max_update_id()
        return offset

    @staticmethod
    def _journal_max_update_id() -> int | None:
        """Haut de fourchette du journal : aucun update <= max n'est a rejouer
        (le traitement est sequentiel et mono-offset, donc monotone)."""
        db = session_factory()
        try:
            mx = db.query(func.max(TelegramMessage.update_id)).scalar()
        finally:
            db.close()
        return int(mx) + 1 if mx is not None else None

    def _save_offset(self, offset: int) -> None:
        try:
            session_store.get_redis_client().set(_OFFSET_KEY, str(offset))
        except Exception:
            pass

    # -- divers --------------------------------------------------------------

    def _attach_listeners(self) -> None:
        from app.modules.audit.service import attach_listeners as attach_audit_listeners
        from app.modules.ledger.service import attach_listeners as attach_ledger_listeners

        attach_audit_listeners()
        attach_ledger_listeners()

    def _lock_for(self, chat_id: int) -> Lock:
        with self._locks_guard:
            return self._locks.setdefault(chat_id, Lock())