"""Tests specifiques au business assurance : record_payment, cancel_contract,
list_clients, le raccourci "reste" (PaymentAmountFieldType), get_period_summary.
"""
import uuid

from app.modules.assistantv3 import service as assistantv3_service
from app.modules.insurance import service as insurance_service
from app.modules.insurance.models import InsuranceContractStatus
from tests.assistantv3.conftest import _no_tool_message, _tool_call_message, create_client_and_contract
from tests.helpers import auth_headers


def test_paiement_simple_demande_confirmation_puis_execute(db, root, assurance, client, llm):
    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))

    reply = assistantv3_service.chat(db, root, "Encaisser 40 000 de Tagoun pour le contrat MAT-E2E", None)
    assert reply.confirmation_required is True
    assert reply.pending_action == "record_payment"
    assert "40000" in reply.text.replace(" ", "")

    reply2 = assistantv3_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["record_payment"]
    assert "40 000" in reply2.text
    assert "60 000" in reply2.text


def test_confirmation_refusee_annule_sans_effet(db, root, assurance, client, llm):
    _, contract = create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))

    reply = assistantv3_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assert reply.confirmation_required is True

    reply2 = assistantv3_service.chat(db, root, "non", reply.session_id)
    assert reply2.text == "Action annulee."

    remaining = client.get(f"/api/insurance/contracts/{contract['id']}", headers=auth_headers(root)).json()
    assert float(remaining["remaining_amount"]) == 100000


def test_clarification_puis_confirmation_sans_rappeler_le_llm(db, root, assurance, client, llm):
    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E"})]))

    reply = assistantv3_service.chat(db, root, "Encaisser pour le contrat MAT-E2E", None)
    assert reply.clarification is True
    assert reply.missing_field == "amount"

    reply2 = assistantv3_service.chat(db, root, "40000", reply.session_id)
    assert reply2.confirmation_required is True
    assert reply2.pending_action == "record_payment"

    reply3 = assistantv3_service.chat(db, root, "oui", reply2.session_id)
    assert reply3.clarification is False
    assert "40 000" in reply3.text
    assert "60 000" in reply3.text
    assert llm["calls"]["tool_calls"] == 1


def test_paiement_reste_shortcut(db, root, assurance, client, llm):
    """Specifique au port FieldType : PaymentAmountFieldType (composition de
    AmountFieldType + raccourci "reste") fonctionne apres une clarification."""
    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E"})]))

    reply = assistantv3_service.chat(db, root, "Encaisser pour le contrat MAT-E2E", None)
    assert reply.missing_field == "amount"

    reply2 = assistantv3_service.chat(db, root, "le reste", reply.session_id)
    assert reply2.confirmation_required is True

    reply3 = assistantv3_service.chat(db, root, "oui", reply2.session_id)
    assert "100 000" in reply3.text


def test_list_clients(db, root, assurance, client, llm):
    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("list_clients", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv3_service.chat(db, root, "Quels sont mes clients ?", None)

    assert reply.executed_tools == ["list_clients"]
    assert "Tagoun" in reply.text


def test_cancel_contract_demande_confirmation_avec_avertissement(db, root, assurance, client, llm):
    _, contract = create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("cancel_contract", {"contract": "MAT-E2E"})]))

    reply = assistantv3_service.chat(db, root, "Annule le contrat MAT-E2E", None)
    assert reply.confirmation_required is True
    assert "remboursement" in reply.text.lower()

    reply2 = assistantv3_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["cancel_contract"]

    refreshed = insurance_service.get_contract(db, root, uuid.UUID(contract["id"]))
    assert refreshed.status == InsuranceContractStatus.CANCELLED


def test_get_period_summary_ce_mois_par_defaut(db, root, assurance, client, llm):
    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))
    reply = assistantv3_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assistantv3_service.chat(db, root, "oui", reply.session_id)

    llm["queue"].append(_tool_call_message([("get_period_summary", {"business": "assurance"})]))
    llm["queue"].append(_no_tool_message())
    reply2 = assistantv3_service.chat(db, root, "Combien j'ai encaisse ce mois pour l'assurance ?", None)

    assert reply2.executed_tools == ["get_period_summary"]
    assert "40 000" in reply2.text
    assert "ce mois" in reply2.text.lower()
