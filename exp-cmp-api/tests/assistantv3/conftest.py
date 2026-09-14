"""Fixtures partagees par tous les tests assistantv3 (core, insurance,
poultry, extensibility). Ce fichier est le SEUL a toucher pour ajouter du
setup partage a un nouveau business ; les fixtures de tests/conftest.py (db,
root, assurance, poulets, client) restent disponibles ici automatiquement,
pytest cascade les conftest.py des dossiers parents.
"""
import json
from decimal import Decimal

import pytest

from app.core.config import settings
from app.modules.ledger import service as ledger_service
from app.modules.ledger.models import CategoryType
from app.modules.poultry import service as poultry_service
from tests.helpers import auth_headers


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _tool_call_message(calls: list[tuple[str, dict]]) -> dict:
    return {
        "choices": [{
            "message": {
                "tool_calls": [
                    {
                        "id": f"call_{i}",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args, default=str)},
                    }
                    for i, (name, args) in enumerate(calls)
                ]
            }
        }]
    }


def _no_tool_message() -> dict:
    return {"choices": [{"message": {"content": "Je ne comprends pas la demande."}}]}


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

    monkeypatch.setattr("app.modules.assistantv3.session_store.get_redis_client", lambda: _Fake())


@pytest.fixture(autouse=True)
def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_LLM_API_KEY", "fake-key-for-tests")
    monkeypatch.setattr("app.modules.assistantv3.orchestrator.get_formulator", lambda: None)


@pytest.fixture
def llm(monkeypatch):
    queue: list[dict] = []
    calls = {"tool_calls": 0, "other": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        if json and "tools" in json:
            calls["tool_calls"] += 1
            if not queue:
                raise AssertionError("Appel LLM (tool-calling) inattendu : file de reponses vide")
            return _FakeResponse(queue.pop(0))
        calls["other"] += 1
        return _FakeResponse({"choices": [{"message": {"content": ""}}]})

    monkeypatch.setattr("httpx.post", fake_post)
    return {"queue": queue, "calls": calls}


def create_client_and_contract(client, root):
    client_out = client.post(
        "/api/insurance/clients", headers=auth_headers(root), json={"full_name": "Tagoun"}
    ).json()
    contract = client.post(
        f"/api/insurance/clients/{client_out['id']}/contracts",
        headers=auth_headers(root),
        json={
            "matricule": "MAT-E2E",
            "contract_type": "assurance-auto",
            "premium": "100000",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    ).json()
    return client_out, contract


def seed_poultry_purchase(db, root, poulets, quantity=24, amount=Decimal("120000")):
    account = ledger_service.list_accounts(db, root, poulets.id)[0]
    category = next(c for c in ledger_service.list_categories(db) if c.type == CategoryType.DEBIT)
    unit_price = (amount / quantity).quantize(Decimal("0.01"))
    poultry_service.create_approvisionnement(
        db, root, quantity=quantity, unit_price=unit_price, note=None, account_id=account.id, category_id=category.id
    )
