"""Tests du noyau assistantv3 : la boucle, le plafond d'iterations, la
formulation combinee, les outils transverses (get_balance, list_transactions)
et le filtrage par acces utilisateur. Rien ici n'est specifique a un
business : ces tests utiliseraient les memes assertions si assurance/poulets
etaient remplaces par d'autres business.
"""
from app.modules.assistantv3 import service as assistantv3_service
from tests.assistantv3.conftest import _no_tool_message, _tool_call_message, seed_poultry_purchase


def test_aucun_tool_call_donne_message_par_defaut(db, root, llm):
    llm["queue"].append(_no_tool_message())
    reply = assistantv3_service.chat(db, root, "bla bla incomprehensible", None)
    assert reply.executed_tools == []
    assert "aide" in reply.text.lower()


def test_plafond_iterations_respecte(db, root, assurance, llm, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ASSISTANTV2_MAX_ITERATIONS", 2)
    for _ in range(5):
        llm["queue"].append(_tool_call_message([("get_balance", {"business": "assurance"})]))

    reply = assistantv3_service.chat(db, root, "boucle", None)

    assert llm["calls"]["tool_calls"] == 2
    assert reply.executed_tools.count("get_balance") == 2


def test_plusieurs_tool_calls_dans_le_meme_message(db, root, assurance, poulets, client, llm):
    seed_poultry_purchase(db, root, poulets)
    llm["queue"].append(_tool_call_message([
        ("get_stock", {}),
        ("get_balance", {"business": "assurance"}),
    ]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv3_service.chat(
        db, root, "Combien de poulets me reste-t-il, et quel est le solde de la caisse assurance ?", None
    )

    assert set(reply.executed_tools) == {"get_stock", "get_balance"}
    assert "poulet" in reply.text.lower()
    assert "FCFA" in reply.text
    assert llm["calls"]["tool_calls"] == 2


def test_solde_toutes_les_caisses_sans_precision(db, root, assurance, poulets, llm):
    llm["queue"].append(_tool_call_message([("get_balance", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv3_service.chat(db, root, "Quels sont les soldes de mes caisses ?", None)

    assert reply.executed_tools == ["get_balance"]
    assert "Assurance" in reply.text
    assert "Poulets" in reply.text


def test_get_balance_inclut_encaisse_et_depense(db, root, assurance, client, llm):
    from tests.assistantv3.conftest import create_client_and_contract

    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))
    reply = assistantv3_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assistantv3_service.chat(db, root, "oui", reply.session_id)

    llm["queue"].append(_tool_call_message([("get_balance", {"business": "assurance"})]))
    llm["queue"].append(_no_tool_message())
    reply2 = assistantv3_service.chat(db, root, "Solde de la caisse assurance", None)

    assert "encaisse" in reply2.text.lower()
    assert "40 000" in reply2.text


def test_list_transactions_transverse(db, root, assurance, client, llm):
    from tests.assistantv3.conftest import create_client_and_contract

    create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))
    reply = assistantv3_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assistantv3_service.chat(db, root, "oui", reply.session_id)

    llm["queue"].append(_tool_call_message([("list_transactions", {"business": "assurance"})]))
    llm["queue"].append(_no_tool_message())
    reply2 = assistantv3_service.chat(db, root, "Historique de la caisse assurance", None)

    assert reply2.executed_tools == ["list_transactions"]
    assert "40 000" in reply2.text


def test_formulation_combine_plusieurs_etapes(db, root, assurance, poulets, llm, monkeypatch):
    seed_poultry_purchase(db, root, poulets)
    captured = {}

    class _FakeFormulator:
        def formulate(self, operations, user_message=""):
            captured["operations"] = operations
            return "Reponse combinee formulee."

    monkeypatch.setattr("app.modules.assistantv3.orchestrator.get_formulator", lambda: _FakeFormulator())
    llm["queue"].append(_tool_call_message([("get_stock", {}), ("get_balance", {"business": "poulets"})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv3_service.chat(db, root, "stock et solde poulets", None)

    assert reply.text == "Reponse combinee formulee."
    assert [op for op, _ in captured["operations"]] == ["get_stock", "get_balance"]


def test_outils_filtres_selon_acces_utilisateur(db, root, poulets, monkeypatch, llm):
    """Le point le plus rentable identifie a l'introspection : un utilisateur
    limite a une seule activite ne doit pas se voir proposer les outils des
    autres au LLM."""
    import app.modules.assistantv3.orchestrator as orchestrator_module

    monkeypatch.setattr(
        "app.modules.assistantv3.resolvers.accessible_business_codes",
        lambda db, actor: {"poulets"},
    )

    captured_tool_names = {}
    real_build = orchestrator_module.registry.build_llm_tool_definitions

    def spy_build(accessible_codes=None):
        defs = real_build(accessible_codes)
        captured_tool_names["names"] = {d["function"]["name"] for d in defs}
        return defs

    monkeypatch.setattr(orchestrator_module.registry, "build_llm_tool_definitions", spy_build)

    llm["queue"].append(_no_tool_message())
    assistantv3_service.chat(db, root, "aide", None)

    assert "get_stock" in captured_tool_names["names"]
    assert "create_contract" not in captured_tool_names["names"]
    assert "help" in captured_tool_names["names"]


def test_acces_refuse_donne_message_clair_pas_je_n_ai_pas_compris(db, root, poulets, monkeypatch, llm):
    """Correction post-introspection : avant, un tool call refuse par le
    filtrage d'acces ne laissait aucune trace dans le plan, et l'utilisateur
    recevait le message par defaut plutot qu'une explication."""
    monkeypatch.setattr(
        "app.modules.assistantv3.resolvers.accessible_business_codes",
        lambda db, actor: {"poulets"},
    )
    llm["queue"].append(_tool_call_message([("create_contract", {"client": "Tagoun", "matricule": "MAT-1", "premium": "1000"})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv3_service.chat(db, root, "Cree un contrat pour Tagoun", None)

    assert "acces refuse" in reply.text.lower() or "accès refusé" in reply.text.lower()
