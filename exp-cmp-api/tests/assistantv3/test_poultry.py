"""Tests specifiques au business poulets : add_purchase, la validation de
quantite (QuantityFieldType), get_period_summary sans transaction.
"""
from app.modules.assistantv3 import service as assistantv3_service
from tests.assistantv3.conftest import _no_tool_message, _tool_call_message


def test_quantite_invalide_redemande_au_lieu_de_planter(db, root, poulets, llm):
    # Avant correctif (v2) : une quantite a zero fournie directement par le
    # LLM atteignait le calcul de prix unitaire dans add_purchase et
    # provoquait une ZeroDivisionError non geree.
    llm["queue"].append(_tool_call_message([("add_purchase", {"quantity": 0, "amount": "120000"})]))

    reply = assistantv3_service.chat(db, root, "J'ai achete 0 poulets a 120000", None)
    assert reply.clarification is True
    assert reply.missing_field == "quantity"

    reply2 = assistantv3_service.chat(db, root, "24", reply.session_id)
    assert reply2.confirmation_required is True

    reply3 = assistantv3_service.chat(db, root, "oui", reply2.session_id)
    assert reply3.executed_tools == ["add_purchase"]
    assert "24" in reply3.text


def test_quantite_non_entiere_rejetee(db, root, poulets, llm):
    """QuantityFieldType.validate rejette 24.7 plutot que de le tronquer
    silencieusement en 24 (correction post-introspection)."""
    llm["queue"].append(_tool_call_message([("add_purchase", {"quantity": 24.7, "amount": "120000"})]))

    reply = assistantv3_service.chat(db, root, "J'ai achete 24.7 poulets a 120000", None)

    assert reply.clarification is True
    assert reply.missing_field == "quantity"


def test_get_period_summary_periode_sans_transaction(db, root, poulets, llm):
    llm["queue"].append(_tool_call_message([("get_period_summary", {"period": "hier", "business": "poulets"})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv3_service.chat(db, root, "Depenses d'hier pour les poulets ?", None)

    assert reply.executed_tools == ["get_period_summary"]
    assert "hier" in reply.text.lower()
    assert "0 FCFA" in reply.text
