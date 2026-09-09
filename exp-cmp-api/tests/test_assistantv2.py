"""Tests du moteur assistant v2, appele directement via
`assistantv2_service.chat(db, actor, message, session_id)` (le router n'est
pas branche sur app.main, voir app/modules/assistantv2/__init__.py). La
creation de donnees de base (client, contrat) passe par le `client` HTTP
existant (routes insurance/ledger/poultry deja montees dans app.main et sans
rapport avec l'appel LLM). L'appel LLM de l'orchestrateur et celui du
formulateur passent tous deux par `httpx.post` : le fixture `llm` ne fait
repondre que les appels contenant "tools" dans le payload (l'orchestrateur),
et neutralise le formulateur par defaut (voir `_enable_llm`) pour que les
assertions portent sur le texte statique, deterministe.
"""
import json
from decimal import Decimal

import pytest

from app.core.config import settings
from app.modules.assistantv2 import service as assistantv2_service
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

    monkeypatch.setattr("app.modules.assistantv2.session_store.get_redis_client", lambda: _Fake())


@pytest.fixture(autouse=True)
def _enable_llm(monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_LLM_API_KEY", "fake-key-for-tests")
    # Neutralise par defaut la formulation LLM : les assertions portent sur le
    # texte statique deterministe, sauf dans le test dedie a la formulation.
    monkeypatch.setattr("app.modules.assistantv2.orchestrator.get_formulator", lambda: None)


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


def _create_client_and_contract(client, root):
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


def _seed_poultry_purchase(db, root, poulets, quantity=24, amount=Decimal("120000")):
    account = ledger_service.list_accounts(db, root, poulets.id)[0]
    category = next(c for c in ledger_service.list_categories(db) if c.type == CategoryType.DEBIT)
    unit_price = (amount / quantity).quantize(Decimal("0.01"))
    poultry_service.create_approvisionnement(
        db, root, quantity=quantity, unit_price=unit_price, note=None, account_id=account.id, category_id=category.id
    )


def test_paiement_simple_demande_confirmation_puis_execute(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))

    reply = assistantv2_service.chat(db, root, "Encaisser 40 000 de Tagoun pour le contrat MAT-E2E", None)
    assert reply.confirmation_required is True
    assert reply.pending_action == "record_payment"

    reply2 = assistantv2_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["record_payment"]
    assert "40 000" in reply2.text
    assert "60 000" in reply2.text


def test_confirmation_refusee_annule_sans_effet(db, root, assurance, client, llm):
    _, contract = _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))

    reply = assistantv2_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assert reply.confirmation_required is True

    reply2 = assistantv2_service.chat(db, root, "non", reply.session_id)
    assert reply2.text == "Action annulee."

    remaining = client.get(f"/api/insurance/contracts/{contract['id']}", headers=auth_headers(root)).json()
    assert float(remaining["remaining_amount"]) == 100000  # aucun paiement enregistre


def test_plusieurs_tool_calls_dans_le_meme_message(db, root, assurance, poulets, client, llm):
    _seed_poultry_purchase(db, root, poulets)
    llm["queue"].append(_tool_call_message([
        ("get_stock", {}),
        ("get_balance", {"business": "assurance"}),
    ]))
    # Les deux outils sont non critiques et s'executent sans interruption : la
    # boucle interne redonne la main au LLM, qui ici n'a plus rien a faire.
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(
        db, root, "Combien de poulets me reste-t-il, et quel est le solde de la caisse assurance ?", None
    )

    assert set(reply.executed_tools) == {"get_stock", "get_balance"}
    assert "poulet" in reply.text.lower()
    assert "FCFA" in reply.text
    assert llm["calls"]["tool_calls"] == 2  # 1 tour avec les 2 outils + 1 tour de cloture


def test_solde_toutes_les_caisses_sans_precision(db, root, assurance, poulets, llm):
    llm["queue"].append(_tool_call_message([("get_balance", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Quels sont les soldes de mes caisses ?", None)

    assert reply.executed_tools == ["get_balance"]
    assert "Assurance" in reply.text
    assert "Poulets" in reply.text


def test_clarification_puis_confirmation_sans_rappeler_le_llm(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E"})]))  # amount manquant

    reply = assistantv2_service.chat(db, root, "Encaisser pour le contrat MAT-E2E", None)
    assert reply.clarification is True
    assert reply.missing_field == "amount"

    reply2 = assistantv2_service.chat(db, root, "40000", reply.session_id)
    assert reply2.confirmation_required is True
    assert reply2.pending_action == "record_payment"

    reply3 = assistantv2_service.chat(db, root, "oui", reply2.session_id)
    assert reply3.clarification is False
    assert "40 000" in reply3.text
    assert "60 000" in reply3.text

    # Un seul appel LLM au total : la clarification et la confirmation sont
    # resolues de facon deterministe, sans redemander au LLM.
    assert llm["calls"]["tool_calls"] == 1


def test_aucun_tool_call_donne_message_par_defaut(db, root, llm):
    llm["queue"].append(_no_tool_message())
    reply = assistantv2_service.chat(db, root, "bla bla incomprehensible", None)
    assert reply.executed_tools == []
    assert "aide" in reply.text.lower()


def test_plafond_iterations_respecte(db, root, assurance, llm, monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANTV2_MAX_ITERATIONS", 2)
    for _ in range(5):
        llm["queue"].append(_tool_call_message([("get_balance", {"business": "assurance"})]))

    reply = assistantv2_service.chat(db, root, "boucle", None)

    assert llm["calls"]["tool_calls"] == 2
    assert reply.executed_tools.count("get_balance") == 2


def test_formulation_combine_plusieurs_etapes(db, root, assurance, poulets, llm, monkeypatch):
    _seed_poultry_purchase(db, root, poulets)
    captured = {}

    class _FakeFormulator:
        def formulate(self, operations, user_message=""):
            captured["operations"] = operations
            return "Reponse combinee formulee."

    monkeypatch.setattr("app.modules.assistantv2.orchestrator.get_formulator", lambda: _FakeFormulator())
    llm["queue"].append(_tool_call_message([("get_stock", {}), ("get_balance", {"business": "poulets"})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "stock et solde poulets", None)

    assert reply.text == "Reponse combinee formulee."
    assert [op for op, _ in captured["operations"]] == ["get_stock", "get_balance"]
