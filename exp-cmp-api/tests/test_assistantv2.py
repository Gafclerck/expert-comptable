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
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.config import settings
from app.modules.assistantv2 import service as assistantv2_service
from app.modules.assistantv2.tools import vtc_tools
from app.modules.insurance import service as insurance_service
from app.modules.insurance.models import InsuranceContractStatus
from app.modules.ledger import service as ledger_service
from app.modules.ledger.models import CategoryType
from app.modules.poultry import service as poultry_service
from app.modules.vtc import service as vtc_service
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
    assert "40000" in reply.text.replace(" ", "")  # le detail du montant est bien restitue avant de demander confirmation

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


def test_quantite_invalide_redemande_au_lieu_de_planter(db, root, poulets, llm):
    # Avant correctif : une quantite a zero fournie directement par le LLM
    # (donc jamais passee par la validation de _fill_field) atteignait le
    # calcul de prix unitaire dans add_purchase et provoquait une
    # ZeroDivisionError non geree. Doit maintenant redemander la quantite.
    llm["queue"].append(_tool_call_message([("add_purchase", {"quantity": 0, "amount": "120000"})]))

    reply = assistantv2_service.chat(db, root, "J'ai achete 0 poulets a 120000", None)

    assert reply.clarification is True
    assert reply.missing_field == "quantity"

    reply2 = assistantv2_service.chat(db, root, "24", reply.session_id)
    assert reply2.confirmation_required is True

    reply3 = assistantv2_service.chat(db, root, "oui", reply2.session_id)
    assert reply3.executed_tools == ["add_purchase"]
    assert "24" in reply3.text


def test_list_clients(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("list_clients", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Quels sont mes clients ?", None)

    assert reply.executed_tools == ["list_clients"]
    assert "Tagoun" in reply.text


def test_list_contracts_filtre_par_client(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("list_contracts", {"client": "Tagoun"})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Quels sont les contrats de Tagoun ?", None)

    assert reply.executed_tools == ["list_contracts"]
    assert "MAT-E2E" in reply.text


def test_cancel_contract_demande_confirmation_avec_avertissement(db, root, assurance, client, llm):
    _, contract = _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("cancel_contract", {"contract": "MAT-E2E"})]))

    reply = assistantv2_service.chat(db, root, "Annule le contrat MAT-E2E", None)
    assert reply.confirmation_required is True
    assert "remboursement" in reply.text.lower()

    reply2 = assistantv2_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["cancel_contract"]

    refreshed = insurance_service.get_contract(db, root, uuid.UUID(contract["id"]))
    assert refreshed.status == InsuranceContractStatus.CANCELLED


def test_list_transactions_transverse(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))
    reply = assistantv2_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assistantv2_service.chat(db, root, "oui", reply.session_id)

    llm["queue"].append(_tool_call_message([("list_transactions", {"business": "assurance"})]))
    llm["queue"].append(_no_tool_message())
    reply2 = assistantv2_service.chat(db, root, "Historique de la caisse assurance", None)

    assert reply2.executed_tools == ["list_transactions"]
    assert "40 000" in reply2.text


def test_get_balance_inclut_encaisse_et_depense(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))
    reply = assistantv2_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assistantv2_service.chat(db, root, "oui", reply.session_id)

    llm["queue"].append(_tool_call_message([("get_balance", {"business": "assurance"})]))
    llm["queue"].append(_no_tool_message())
    reply2 = assistantv2_service.chat(db, root, "Solde de la caisse assurance", None)

    assert "encaisse" in reply2.text.lower()
    assert "40 000" in reply2.text


def test_get_period_summary_ce_mois_par_defaut(db, root, assurance, client, llm):
    _create_client_and_contract(client, root)
    llm["queue"].append(_tool_call_message([("record_payment", {"contract": "MAT-E2E", "amount": "40000"})]))
    reply = assistantv2_service.chat(db, root, "Encaisser 40000 pour MAT-E2E", None)
    assistantv2_service.chat(db, root, "oui", reply.session_id)

    llm["queue"].append(_tool_call_message([("get_period_summary", {"business": "assurance"})]))
    llm["queue"].append(_no_tool_message())
    reply2 = assistantv2_service.chat(db, root, "Combien j'ai encaisse ce mois pour l'assurance ?", None)

    assert reply2.executed_tools == ["get_period_summary"]
    assert "40 000" in reply2.text
    assert "ce mois" in reply2.text.lower()


def test_get_period_summary_periode_sans_transaction(db, root, poulets, llm):
    llm["queue"].append(_tool_call_message([("get_period_summary", {"period": "hier", "business": "poulets"})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Depenses d'hier pour les poulets ?", None)

    assert reply.executed_tools == ["get_period_summary"]
    assert "hier" in reply.text.lower()
    assert "0 FCFA" in reply.text


def _seed_vtc_chauffeur_vehicule(db, root, name="Moussa Fall", registration="DK-1234-AB"):
    chauffeur = vtc_service.create_chauffeur(db, root, full_name=name, phone="771234567")
    vehicule = vtc_service.create_vehicule(
        db, root, make="Toyota", model="Corolla", year=2020,
        registration=registration, acquisition_cost=Decimal("1500000"),
    )
    return chauffeur, vehicule


def test_vtc_create_chauffeur_et_vehicule_via_llm(db, root, vtc, llm):
    llm["queue"].append(_tool_call_message([
        ("create_chauffeur", {"driver": "Moussa Fall", "phone": "771234567"}),
        ("create_vehicule", {"make": "Toyota", "model": "Corolla", "registration": "DK-1234-AB", "acquisition_cost": "1500000"}),
    ]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Nouveau chauffeur Moussa Fall et nouveau vehicule Toyota Corolla DK-1234-AB a 1 500 000", None)

    assert set(reply.executed_tools) == {"create_chauffeur", "create_vehicule"}
    assert "Moussa Fall" in reply.text
    assert "DK-1234-AB" in reply.text


def test_vtc_create_vehicule_sans_prix_demande_clarification(db, root, vtc, llm):
    llm["queue"].append(_tool_call_message([
        ("create_vehicule", {"make": "Toyota", "model": "Corolla", "registration": "DK-1234-AB"})
    ]))

    reply = assistantv2_service.chat(db, root, "nouvelle voiture Toyota Corolla immatriculation DK-1234-AB", None)
    assert reply.clarification is True
    assert reply.missing_field == "acquisition_cost"

    reply2 = assistantv2_service.chat(db, root, "1 500 000", reply.session_id)
    assert reply2.executed_tools == ["create_vehicule"]
    assert "1 500 000" in reply2.text


def test_vtc_nouvelle_voiture_declenche_clarification(db, root, vtc, llm):
    """Intention nue sans tool_call du LLM : le fallback deterministe injecte
    create_vehicule et l'orchestrateur clarifie champ par champ."""
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "nouvelle voiture", None)
    assert reply.clarification is True
    assert reply.missing_field == "make"

    reply2 = assistantv2_service.chat(db, root, "Toyota", reply.session_id)
    assert reply2.clarification is True
    assert reply2.missing_field == "model"

    reply3 = assistantv2_service.chat(db, root, "Corolla", reply2.session_id)
    assert reply3.clarification is True
    assert reply3.missing_field == "registration"

    reply4 = assistantv2_service.chat(db, root, "DK-1234-AB", reply3.session_id)
    assert reply4.clarification is True
    assert reply4.missing_field == "acquisition_cost"

    reply5 = assistantv2_service.chat(db, root, "1 500 000", reply4.session_id)
    assert reply5.executed_tools == ["create_vehicule"]
    assert "1 500 000" in reply5.text


def test_vtc_nouvelle_voiture_sans_declaration_reste_muet(db, root, vtc, llm):
    """Pas de signal de declaration (liste, pas de creation) : le fallback ne
    doit pas se declencher, retour au message par defaut."""
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "montre moi les nouvelles voitures du parc", None)
    assert reply.clarification is False
    assert reply.executed_tools == []


def test_vtc_list_chauffeurs_vide(db, root, vtc, llm):
    llm["queue"].append(_tool_call_message([("list_chauffeurs", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Quels sont mes chauffeurs ?", None)

    assert reply.executed_tools == ["list_chauffeurs"]
    assert "Aucun chauffeur" in reply.text


def test_vtc_creation_affectation_puis_versement_avec_confirmation(db, root, vtc, llm):
    _seed_vtc_chauffeur_vehicule(db, root)
    llm["queue"].append(_tool_call_message([
        ("create_affectation", {"driver": "Moussa Fall", "vehicle": "DK-1234-AB", "expected_amount": "50000"})
    ]))

    reply = assistantv2_service.chat(db, root, "Affecter Moussa Fall au vehicule DK-1234-AB pour 50 000", None)
    assert reply.confirmation_required is True
    assert reply.pending_action == "create_affectation"
    assert "50000" in reply.text  # le montant attendu est restitue avant de demander confirmation

    reply2 = assistantv2_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["create_affectation"]
    assert "Moussa Fall" in reply2.text

    llm["queue"].append(_tool_call_message([
        ("record_versement", {"driver": "Moussa Fall", "vehicle": "DK-1234-AB", "amount": "20000"})
    ]))
    reply3 = assistantv2_service.chat(db, root, "Moussa Fall a verse 20 000 pour DK-1234-AB", None)
    assert reply3.confirmation_required is True

    reply4 = assistantv2_service.chat(db, root, "oui", reply3.session_id)
    assert reply4.executed_tools == ["record_versement"]
    assert "20 000" in reply4.text
    assert "30 000" in reply4.text  # reste a payer
    assert "Caisse" in reply4.text  # caisse resolue par defaut


def test_vtc_clarification_chauffeur_inconnu(db, root, vtc, llm):
    chauffeur, _ = _seed_vtc_chauffeur_vehicule(db, root)
    llm["queue"].append(_tool_call_message([("get_chauffeur_sold", {"driver": "Personne Inconnue"})]))

    reply = assistantv2_service.chat(db, root, "Reste a payer de Personne Inconnue ?", None)
    assert reply.clarification is True
    assert reply.missing_field == "driver"
    assert "Aucun chauffeur" in reply.text

    reply2 = assistantv2_service.chat(db, root, "Moussa Fall", reply.session_id)
    assert reply2.executed_tools == ["get_chauffeur_sold"]
    assert "Moussa Fall" in reply2.text
    assert "0 FCFA" in reply2.text


def test_vtc_end_affectation_avec_confirmation(db, root, vtc, llm):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    vtc_service.create_affectation(
        db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id,
        start_date=date.today(), expected_amount=Decimal("50000"),
    )
    llm["queue"].append(_tool_call_message([
        ("end_affectation", {"driver": "Moussa Fall", "vehicle": "DK-1234-AB"})
    ]))

    reply = assistantv2_service.chat(db, root, "Cloturer l'affectation de Moussa Fall sur DK-1234-AB", None)
    assert reply.confirmation_required is True

    reply2 = assistantv2_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["end_affectation"]
    assert "terminee" in reply2.text.lower()


def test_vtc_declare_indisponibilite_puis_statistiques(db, root, vtc, llm):
    _seed_vtc_chauffeur_vehicule(db, root)
    llm["queue"].append(_tool_call_message([
        ("declare_indisponibilite", {"vehicle": "DK-1234-AB", "reason": "Panne moteur"})
    ]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "DK-1234-AB est en panne aujourd'hui", None)
    assert reply.executed_tools == ["declare_indisponibilite"]
    assert "DK-1234-AB" in reply.text


def test_vtc_resume_financier_direct(db, root, vtc):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    affectation = vtc_service.create_affectation(
        db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id,
        start_date=date.today(), expected_amount=Decimal("50000"),
    )
    account = ledger_service.list_accounts(db, root, vtc.id)[0]
    category = next(c for c in ledger_service.list_categories(db) if c.type == CategoryType.CREDIT)
    vtc_service.create_versement(
        db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id,
        amount=Decimal("20000"), account_id=account.id, category_id=category.id,
    )

    facts, target_id, text = vtc_tools.get_resume_financier(db, root, {})
    assert target_id is None
    assert "20 000" in text
    assert facts["kind"] == "get_resume_financier"
    assert facts["net"].endswith("FCFA")


def test_vtc_update_vehicule_status_avec_confirmation(db, root, vtc, llm):
    _seed_vtc_chauffeur_vehicule(db, root)
    llm["queue"].append(_tool_call_message([
        ("update_vehicule_status", {"vehicle": "DK-1234-AB", "status": "en panne"})
    ]))

    reply = assistantv2_service.chat(db, root, "Mettre le vehicule DK-1234-AB en panne", None)
    assert reply.confirmation_required is True
    assert reply.pending_action == "update_vehicule_status"

    reply2 = assistantv2_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["update_vehicule_status"]
    assert "out_of_service" in reply2.text


def test_vtc_update_chauffeur_status_avec_confirmation(db, root, vtc, llm):
    _seed_vtc_chauffeur_vehicule(db, root)
    llm["queue"].append(_tool_call_message([
        ("update_chauffeur_status", {"driver": "Moussa Fall", "status": "inactif"})
    ]))

    reply = assistantv2_service.chat(db, root, "Desactiver le chauffeur Moussa Fall", None)
    assert reply.confirmation_required is True

    reply2 = assistantv2_service.chat(db, root, "oui", reply.session_id)
    assert reply2.executed_tools == ["update_chauffeur_status"]
    assert "inactive" in reply2.text


def test_vtc_close_indisponibilite(db, root, vtc, llm):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    vtc_service.create_indisponibilite(db, root, vehicle_id=vehicule.id, start_date=date.today(), reason="Panne moteur")
    llm["queue"].append(_tool_call_message([
        ("close_indisponibilite", {"vehicle": "DK-1234-AB"})
    ]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "DK-1234-AB est reparable, fin de l'indisponibilite", None)
    assert reply.executed_tools == ["close_indisponibilite"]
    assert "cloturee" in reply.text.lower()


def test_vtc_list_versements_via_llm(db, root, vtc, llm):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    vtc_service.create_affectation(db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id, start_date=date.today(), expected_amount=Decimal("50000"))
    account = ledger_service.list_accounts(db, root, vtc.id)[0]
    category = next(c for c in ledger_service.list_categories(db) if c.type == CategoryType.CREDIT)
    vtc_service.create_versement(db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id, amount=Decimal("20000"), account_id=account.id, category_id=category.id)

    llm["queue"].append(_tool_call_message([("list_versements", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Lister les versements du parc", None)
    assert reply.executed_tools == ["list_versements"]
    assert "20 000" in reply.text


def test_vtc_get_vehicle_stats_avec_periode(db, root, vtc):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    vtc_service.create_affectation(db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id, start_date=date.today(), expected_amount=Decimal("50000"))
    account = ledger_service.list_accounts(db, root, vtc.id)[0]
    category = next(c for c in ledger_service.list_categories(db) if c.type == CategoryType.CREDIT)
    vtc_service.create_versement(db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id, amount=Decimal("20000"), account_id=account.id, category_id=category.id)

    params = {"vehicle_id": str(vehicule.id), "vehicle_label": "Toyota Corolla (DK-1234-AB)", "period": "ce mois"}
    facts, target_id, text = vtc_tools.get_vehicle_stats(db, root, params)
    assert facts["kind"] == "get_vehicle_stats"
    assert facts["period"] == "ce mois"
    assert "20 000" in text


def test_vtc_park_overview_direct(db, root, vtc):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    vtc_service.create_affectation(db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id, start_date=date.today(), expected_amount=Decimal("50000"))

    facts, target_id, text = vtc_tools.park_overview(db, root, {})
    assert target_id is None
    assert facts["kind"] == "park_overview"
    assert facts["chauffeurs_actifs"] == "1"
    assert "reste" in text.lower()


def test_vtc_active_affectations_via_llm(db, root, vtc, llm):
    chauffeur, vehicule = _seed_vtc_chauffeur_vehicule(db, root)
    vtc_service.create_affectation(db, root, driver_id=chauffeur.id, vehicle_id=vehicule.id, start_date=date.today(), expected_amount=Decimal("50000"))
    llm["queue"].append(_tool_call_message([("active_affectations", {})]))
    llm["queue"].append(_no_tool_message())

    reply = assistantv2_service.chat(db, root, "Quelles affectations sont actives aujourd'hui ?", None)
    assert reply.executed_tools == ["active_affectations"]
    assert "Moussa Fall" in reply.text
