"""Tests du canal Telegram (Phase 1) :

- flux REST de liaison (token jetable, etat du lien, debranchement, audit) ;
- worker : /start <TOKEN>, lookup du user, delegation a
  `assistantv2_service.chat`, exactement-une-fois (journal update_id),
  comptes inactifs refuses, chats non prives ignores, avance de l'offset.

Aucun acces reseau : le client Telegram est injecte (fake) et le moteur
assistant est neutralise (chat suturé) pour que les assertions portent sur le
cablage du worker, pas sur le moteur (teste ailleurs, test_assistantv2.py).
"""
import time

import httpx
import pytest

from app.core.db import session as session_factory
from app.modules.assistantv2 import service as assistantv2_service
from app.modules.assistantv2.schemas import AssistantReplyV2
from app.modules.assistantv2.telegram import service as telegram_service
from app.modules.assistantv2.telegram.worker import TelegramWorker
from app.modules.audit.models import AuditAction, AuditLog
from app.modules.identity.models import User, UserStatus
from tests.helpers import auth_headers

CHAT_ID = 111_222_333


def _update(update_id, chat_id, text, *, chat_type="private", message_id=1, username="joe"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "from": {"id": 42, "username": username},
            "chat": {"id": chat_id, "type": chat_type},
            "text": text,
        },
    }


def _audit_actions(entity_type: str) -> list[str]:
    db = session_factory()
    try:
        return [
            row.action.value
            for row in db.query(AuditLog).filter(AuditLog.entity_type == entity_type).all()
        ]
    finally:
        db.close()


class _FakeTelegramClient:
    def __init__(self, updates=None):
        self.updates = updates or []
        self.sent: list[tuple[int, str]] = []
        self.fail_send = False

    def get_updates(self, offset=None, **kwargs):
        return self.updates

    def send_message(self, chat_id, text):
        if self.fail_send:
            raise httpx.HTTPError("envoi KO")
        self.sent.append((chat_id, text))
        return 1


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch):
    store: dict[str, str] = {}

    class _Fake:
        def get(self, key):
            return store.get(key)

        def set(self, key, value, ex=None):
            store[key] = value

        def delete(self, key):
            store.pop(key, None)

    monkeypatch.setattr("app.modules.assistantv2.session_store.get_redis_client", lambda: _Fake())
    return store


def _link_root(db, token: str, chat_id: int = CHAT_ID) -> None:
    """Simule le consommateur du token (le worker) : `/start <TOKEN>`."""
    worker = TelegramWorker(client=_FakeTelegramClient())
    worker.handle_update(_update(update_id=1, chat_id=chat_id, text=f"/start {token}"))
    db.rollback()


# --- Flux REST --------------------------------------------------------------


def test_token_me_unlink_flow(client, root):
    res = client.post("/api/telegram/bindings/token", headers=auth_headers(root))
    assert res.status_code == 201
    payload = res.json()
    assert payload["token"]
    assert "instruction" in payload

    me = client.get("/api/telegram/bindings/me", headers=auth_headers(root)).json()
    assert me["linked"] is False

    db = session_factory()
    _link_root(db, payload["token"])
    db.close()

    me = client.get("/api/telegram/bindings/me", headers=auth_headers(root)).json()
    assert me["linked"] is True
    assert me["chat_id"] == CHAT_ID
    assert me["active"] is True

    bindings = client.get("/api/telegram/bindings", headers=auth_headers(root)).json()
    assert len(bindings) == 1
    assert bindings[0]["chat_id"] == CHAT_ID

    res = client.delete("/api/telegram/bindings/me", headers=auth_headers(root))
    assert res.status_code == 204

    # Bug 5 : "me" reflete le lien ACTIF ; apres debranchement, plus de lien.
    me = client.get("/api/telegram/bindings/me", headers=auth_headers(root)).json()
    assert me["linked"] is False


def test_token_me_requires_auth(client):
    assert client.post("/api/telegram/bindings/token").status_code == 401
    assert client.get("/api/telegram/bindings/me").status_code == 401
    assert client.get("/api/telegram/bindings").status_code == 401


def test_bindings_listing_requires_root(client, co_owner):
    res = client.get("/api/telegram/bindings", headers=auth_headers(co_owner))
    assert res.status_code == 403


def test_binding_audited(client, root):
    res = client.post("/api/telegram/bindings/token", headers=auth_headers(root)).json()
    db = session_factory()
    _link_root(db, res["token"])
    db.close()

    assert _audit_actions("telegram_bindings") == ["CREATE"]

    client.delete("/api/telegram/bindings/me", headers=auth_headers(root))
    assert sorted(_audit_actions("telegram_bindings")) == ["CREATE", "UPDATE"]


# --- Worker -----------------------------------------------------------------


def test_worker_send_not_linked(root):
    worker = TelegramWorker(client=_FakeTelegramClient())
    worker.handle_update(_update(update_id=10, chat_id=CHAT_ID, text="solde de la caisse"))
    assert worker.client.sent and "Compte non lie" in worker.client.sent[0][1]


def test_worker_start_links_then_chat_delegates(root, monkeypatch):
    db = session_factory()
    token = telegram_service.create_link_token(db, root).token
    db.close()

    calls: list[tuple] = []
    sent_by_worker: list[str] = []

    def fake_chat(db_, user, message, session_id):
        calls.append((user.id, message, session_id))
        return AssistantReplyV2(text=f"Reponse pour {message}", session_id=session_id)

    monkeypatch.setattr("app.modules.assistantv2.service.chat", fake_chat)

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))
    assert "Compte lie" in client.sent[0][1]

    client.sent.clear()
    worker.handle_update(_update(update_id=2, chat_id=CHAT_ID, text="Solde de la caisse assurance"))
    assert calls == [(root.id, "Solde de la caisse assurance", f"tg:{CHAT_ID}")]
    assert [t for _, t in client.sent] == ["Reponse pour Solde de la caisse assurance"]


def test_worker_start_token_mono_usage(root):
    db = session_factory()
    token = telegram_service.create_link_token(db, root).token

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))
    client.sent.clear()
    worker.handle_update(_update(update_id=2, chat_id=123_456, text=f"/start {token}"))
    assert client.sent and "Token invalide" in client.sent[0][1]
    db.close()


def test_worker_exactly_once_on_redelivery(root, monkeypatch):
    db = session_factory()
    token = telegram_service.create_link_token(db, root).token
    db.close()

    calls: list[tuple] = []

    def fake_chat(db_, user, message, session_id):
        calls.append((user.id, message))
        return AssistantReplyV2(text="ok", session_id=session_id)

    monkeypatch.setattr("app.modules.assistantv2.service.chat", fake_chat)

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))

    update = _update(update_id=2, chat_id=CHAT_ID, text="depense 5000 pour carburant")
    worker.handle_update(update)
    worker.handle_update(update)  # re-delivree par Telegram apres crash (meme update_id)
    assert len(calls) == 1


def test_worker_refuses_inactive_user(root, monkeypatch):
    db = session_factory()
    token = telegram_service.create_link_token(db, root).token
    db.close()

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))

    db = session_factory()
    user = db.get(User, root.id)
    user.status = UserStatus.INACTIVE
    db.commit()
    db.close()

    calls: list[tuple] = []

    def fake_chat(db_, user, message, session_id):
        calls.append(1)
        return AssistantReplyV2(text="ok", session_id=session_id)

    monkeypatch.setattr("app.modules.assistantv2.service.chat", fake_chat)
    client.sent.clear()
    worker.handle_update(_update(update_id=2, chat_id=CHAT_ID, text="solde caisse"))
    assert calls == []
    assert client.sent and "inactif" in client.sent[0][1]

    db = session_factory()
    user = db.get(User, root.id)
    user.status = UserStatus.ACTIVE
    db.commit()
    db.close()


def test_worker_ignores_non_private_chats(root, monkeypatch):
    calls: list[tuple] = []

    def fake_chat(db_, user, message, session_id):
        calls.append(1)
        return AssistantReplyV2(text="ok", session_id=session_id)

    monkeypatch.setattr("app.modules.assistantv2.service.chat", fake_chat)

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text="solde", chat_type="group"))
    assert calls == []
    assert client.sent == []


def test_worker_run_once_advances_offset():
    client = _FakeTelegramClient(
        updates=[
            _update(update_id=100, chat_id=CHAT_ID, text="salut"),
            _update(update_id=101, chat_id=CHAT_ID, text="encore"),
        ]
    )
    worker = TelegramWorker(client=client)
    processed = worker.run_once()
    assert processed == 2
    assert worker._load_offset() == 102


def test_worker_stop_resets_session(root, _fake_redis):
    from app.modules.assistantv2.plan import Plan

    session_store = __import__("app.modules.assistantv2.session_store", fromlist=["session_store"])
    session_store.save_plan(Plan(session_id=f"tg:{CHAT_ID}", user_message="x"))

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker._attach_listeners()  # sans effet si deja fait via app.main
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text="/stop"))
    assert f"tg:{CHAT_ID}" not in _fake_redis
    assert client.sent and "reinitialisee" in client.sent[0][1]


# --- Regressions (bugs detectes en relecture) ---------------------------------


def test_worker_run_once_does_not_advance_offset_on_failure(monkeypatch):
    """Bug 4 : si le traitement d'un update echoue (ex. ecriture du journal),
    l'offset ne doit PAS etre avance, sinon Telegram ne re-livrera jamais cet
    update (commande perdue)."""
    client = _FakeTelegramClient(
        updates=[_update(update_id=100, chat_id=CHAT_ID, text="salut")]
    )
    worker = TelegramWorker(client=client)
    worker.run_once()
    assert worker._load_offset() == 101

    client.updates = [_update(update_id=101, chat_id=CHAT_ID, text="depense 5000")]

    def broken_record(*args, **kwargs):
        raise RuntimeError("DB down")

    monkeypatch.setattr(TelegramWorker, "_record_in", staticmethod(broken_record))
    worker.run_once()
    assert worker._load_offset() == 101  # pas d'avance apres echec


def test_worker_send_failure_logs_without_raising(root, monkeypatch):
    """Bug 3 : un echec d'envoi de la reponse (apres execution reussie) ne doit
    ni faire planter handle_update, ni bloquer l'avance de l'offset (sinon
    Telegram re-livre l'update et le journal le saute : succes silencieux)."""
    db = session_factory()
    token = telegram_service.create_link_token(db, root).token
    db.close()

    calls: list[tuple] = []

    def fake_chat(db_, user, message, session_id):
        calls.append(1)
        return AssistantReplyV2(text="ok", session_id=session_id)

    monkeypatch.setattr("app.modules.assistantv2.service.chat", fake_chat)
    monkeypatch.setattr("app.modules.assistantv2.telegram.worker.time", _noop_time())

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))

    client.sent.clear()
    client.fail_send = True
    worker.handle_update(_update(update_id=2, chat_id=CHAT_ID, text="solde caisse"))
    assert calls == [1]  # la commande a ete executee
    assert client.sent == []  # la reponse n'a pas pu partir, echec logge


def test_worker_run_forever_terminates_on_401(monkeypatch):
    """Bug 2 : si Telegram rejette le token en cours de route (401), le worker
    doit s'arreter (code 2) et non boucler indefiniment a poller en 401."""
    from httpx import HTTPStatusError, Request, Response

    client = _FakeTelegramClient()

    def get_updates_401(offset=None, **kwargs):
        raise HTTPStatusError(
            "401 Unauthorized",
            request=Request("GET", "http://test"),
            response=Response(401),
        )

    client.get_updates = get_updates_401
    monkeypatch.setattr(
        "app.modules.assistantv2.telegram.worker.time", _noop_time(raise_on_sleep=True)
    )
    code = TelegramWorker(client=client).run_forever()
    assert code == 2


def test_worker_restart_no_replay_no_loss(root, monkeypatch, _fake_redis):
    """Phase 2 AC : couper le worker puis le relancer (nouvelle instance,
    offset Redis perdu) -> aucune commande rejouee (journal), aucune update
    perdue (reprise depuis max(update_id) du journal), conversation reprise
    depuis Redis (plan non purge)."""
    from app.modules.assistantv2.plan import Plan

    db = session_factory()
    token = telegram_service.create_link_token(db, root).token
    db.close()

    calls: list[tuple] = []

    def fake_chat(db_, user, message, session_id):
        calls.append((message, session_id))
        return AssistantReplyV2(text="ok", session_id=session_id)

    monkeypatch.setattr("app.modules.assistantv2.service.chat", fake_chat)

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)  # process 1
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))

    # Une session en cours (plan Redis) doit survivre au redemarrage.
    session_store = __import__("app.modules.assistantv2.session_store", fromlist=["session_store"])
    session_store.save_plan(Plan(session_id=f"tg:{CHAT_ID}", user_message="depense 5000"))

    client.updates = [_update(update_id=300, chat_id=CHAT_ID, text="depense 5000 carburant")]
    worker.run_once()
    assert [m for m, _ in calls] == ["depense 5000 carburant"]

    # Crash du process (Redis survit) : l'offset Redis disparait de maniere
    # imprevisible, Telegram re-livre 300 puis un nouveau 301. Le plan de la
    # conversation est toujours la (a rejouer par le process relance).
    _fake_redis.pop("assistantv2:telegram:offset", None)
    client.updates = [
        _update(update_id=300, chat_id=CHAT_ID, text="depense 5000 carburant"),
        _update(update_id=301, chat_id=CHAT_ID, text="depense 2000 carburant"),
    ]
    worker2 = TelegramWorker(client=client)  # process 2, memes tables + Redis
    assert worker2._load_offset() == 301  # reintroduit depuis le journal
    worker2.run_once()

    assert [m for m, _ in calls] == ["depense 5000 carburant", "depense 2000 carburant"]
    assert all(sid == f"tg:{CHAT_ID}" for _, sid in calls)
    assert f"assistantv2:plan:tg:{CHAT_ID}" in _fake_redis  # conversation reprise


def test_worker_start_inactive_does_not_consume_token(root):
    """Bug 6 : un compte inactif refuse la liaison SANS bruler le token
    (sinon l'utilisateur doit en regenerer un apres reactivation)."""
    db = session_factory()
    token = telegram_service.create_link_token(db, root).token
    user = db.get(User, root.id)
    user.status = UserStatus.INACTIVE
    db.commit()
    db.close()

    client = _FakeTelegramClient()
    worker = TelegramWorker(client=client)
    worker.handle_update(_update(update_id=1, chat_id=CHAT_ID, text=f"/start {token}"))
    assert client.sent and "inactif" in client.sent[0][1]

    db = session_factory()
    user = db.get(User, root.id)
    user.status = UserStatus.ACTIVE
    db.commit()
    db.close()

    db = session_factory()
    record = telegram_service.consume_link_token(db, token)
    db.close()
    assert record is not None  # token encore consommable


class _noop_time:
    def __init__(self, raise_on_sleep=False):
        self._raise = raise_on_sleep

    def sleep(self, seconds):
        if self._raise:
            raise RuntimeError("boucle infinie : le worker aurait du s'arreter")