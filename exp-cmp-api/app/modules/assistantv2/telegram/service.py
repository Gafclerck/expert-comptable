"""Service des liaisons Telegram : tokens jetables, bindings `chat_id ->
user`, journal d'idempotence des updates.

Utilise par les deux cotes :
- l'API REST (router) : creation de token, etat du lien, debranchement ;
- le worker de polling dedie : consommation du token (`/start <TOKEN>`),
  liaison, lookup du user par chat, journal exactly-once.

Les evenements `telegram.binding.created`/`telegram.binding.removed` sont
publies ici mais ne sont persistes que si `attach_audit_listeners()` a ete
appele dans CE processus (le bus est par processus — le worker doit donc le
faire lui-meme au demarrage, cf. docs/TELEGRAM_INTEGRATION.md).
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.events import publish
from app.modules.assistantv2.telegram.models import (
    TelegramBinding,
    TelegramLinkToken,
    TelegramMessage,
)
from app.modules.identity.models import User, UserStatus

TOKEN_LENGTH = 12
SESSION_ID_PREFIX = "tg:"


def session_id_for(chat_id: int) -> str:
    """Session de l'assistant v2 propre a un chat Telegram (persistance Redis du
    plan en cours entre deux messages)."""
    return f"{SESSION_ID_PREFIX}{chat_id}"


def _new_token() -> str:
    return secrets.token_urlsafe(9)  # ~12 caracteres, unicite garantie par la contrainte


def _as_utc(dt: datetime) -> datetime:
    """Normalise en datetime UTC aware : SQLite relit les colonnes
    `DateTime(timezone=True)` comme naives (Postgres, lui, aware)."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def create_link_token(db: Session, user: User) -> TelegramLinkToken:
    """Genere un token jetable pour l'utilisateur. Invalide les precedents
    tokens non utilises du meme utilisateur (mono-liaison de fait)."""
    now = datetime.now(timezone.utc)
    for old in (
        db.query(TelegramLinkToken)
        .filter(TelegramLinkToken.user_id == user.id, TelegramLinkToken.used_at.is_(None))
        .all()
    ):
        old.used_at = now
    record = TelegramLinkToken(
        token=_new_token(),
        user_id=user.id,
        expires_at=now + timedelta(minutes=settings.TELEGRAM_LINK_TOKEN_TTL_MINUTES),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def find_link_token(db: Session, token: str) -> TelegramLinkToken | None:
    """Retourne le token SANS le consommer s'il est encore valide (existant,
    non utilise, non expire), None sinon. Permet de valider le compte lie
    avant de bruler le token (bug 6)."""
    record = db.query(TelegramLinkToken).filter(TelegramLinkToken.token == token).first()
    if record is None or record.used_at is not None or _as_utc(record.expires_at) <= datetime.now(timezone.utc):
        return None
    return record


def consume_link_token(db: Session, token: str) -> TelegramLinkToken | None:
    """Marque le token comme utilise s'il est encore valide (existant, non
    utilise, non expire). Retourne le token consomme, None sinon."""
    record = find_link_token(db, token)
    if record is None:
        return None
    record.used_at = datetime.now(timezone.utc)
    db.commit()
    return record


def create_binding(
    db: Session,
    chat_id: int,
    *,
    token: TelegramLinkToken,
    tg_username: str | None = None,
    tg_user_id: int | None = None,
) -> TelegramBinding:
    """Cree (ou re-affecte) la liaison pour ce chat et publie
    `telegram.binding.created`. Leve ValueError si le compte du token est
    introuvable ou inactif (message a relayer tel quel a l'utilisateur)."""
    user = db.get(User, token.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise ValueError("Le compte associe au token est introuvable ou inactif")
    binding = db.query(TelegramBinding).filter(TelegramBinding.chat_id == chat_id).first()
    if binding is None:
        binding = TelegramBinding(
            chat_id=chat_id,
            user_id=user.id,
            tg_username=tg_username,
            tg_user_id=tg_user_id,
        )
        db.add(binding)
        db.commit()
        db.refresh(binding)
    else:
        binding.user_id = user.id
        binding.active = True
        binding.tg_username = tg_username
        binding.tg_user_id = tg_user_id
        binding.last_seen_at = None
        db.commit()
    # Le commit precede le publish : l'audit ouvre sa propre session (SQLite
    # est single-writer ; les autres modules suivent la meme regle).
    publish(
        "telegram.binding.created",
        actor_id=str(user.id),
        entity_id=str(binding.id),
        new_values={"chat_id": chat_id, "user_id": str(user.id)},
    )
    db.commit()
    db.refresh(binding)
    return binding


def get_active_binding(db: Session, chat_id: int) -> TelegramBinding | None:
    return (
        db.query(TelegramBinding)
        .filter(TelegramBinding.chat_id == chat_id, TelegramBinding.active.is_(True))
        .first()
    )


def get_binding_for_user(db: Session, user_id: uuid.UUID) -> TelegramBinding | None:
    """Lien ACTIF le plus recent du compte. Un lien debranche n'est plus
    renvoye par "me" (le listing admin, lui, conserve l'historique)."""
    return (
        db.query(TelegramBinding)
        .filter(TelegramBinding.user_id == user_id, TelegramBinding.active.is_(True))
        .order_by(TelegramBinding.linked_at.desc())
        .first()
    )


def deactivate_binding(db: Session, binding: TelegramBinding, actor: User) -> None:
    binding.active = False
    db.commit()
    publish(
        "telegram.binding.removed",
        actor_id=str(actor.id),
        entity_id=str(binding.id),
        new_values={"chat_id": binding.chat_id, "active": False},
    )


def touch_last_seen(db: Session, binding: TelegramBinding) -> None:
    binding.last_seen_at = datetime.now(timezone.utc)
    db.commit()


def list_bindings(db: Session, skip: int = 0, limit: int = 50) -> list[TelegramBinding]:
    return (
        db.query(TelegramBinding)
        .order_by(TelegramBinding.linked_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# --- Journal d'idempotence (exactly-once) ---


def is_already_processed(db: Session, update_id: int) -> bool:
    return (
        db.query(TelegramMessage)
        .filter(TelegramMessage.update_id == update_id)
        .first()
        is not None
    )


def record_message(
    db: Session,
    *,
    chat_id: int,
    update_id: int,
    message_id: int | None,
    direction: str,
) -> None:
    db.add(
        TelegramMessage(
            chat_id=chat_id,
            update_id=update_id,
            message_id=message_id,
            direction=direction,
        )
    )
    db.commit()


# --- Vue API ---


def binding_to_admin(binding: TelegramBinding) -> dict:
    return {
        "id": binding.id,
        "chat_id": binding.chat_id,
        "user_id": binding.user_id,
        "tg_username": binding.tg_username,
        "active": binding.active,
        "linked_at": binding.linked_at,
        "last_seen_at": binding.last_seen_at,
    }


def binding_to_me(binding: TelegramBinding | None) -> dict:
    if binding is None:
        return {"linked": False}
    return {
        "linked": True,
        "chat_id": binding.chat_id,
        "user_id": binding.user_id,
        "tg_username": binding.tg_username,
        "active": binding.active,
        "linked_at": binding.linked_at,
        "last_seen_at": binding.last_seen_at,
    }