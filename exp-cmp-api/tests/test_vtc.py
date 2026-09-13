from datetime import date, timedelta
from decimal import Decimal
import uuid

import pytest

from tests.conftest import auth_headers, link_person_to_business
from tests.helpers import create_account, create_category


def _vtc(db):
    from app.modules.identity.models import Business
    return db.query(Business).filter(Business.code == "vtc").first()


@pytest.fixture
def vtc_business(db):
    return _vtc(db)


def _create_chauffeur(client, actor, name, license_no=None):
    return client.post(
        "/api/vtc/chauffeurs",
        headers=auth_headers(actor),
        json={"full_name": name, "license_number": license_no},
    )


def _create_vehicule(client, actor, registration, make="Toyota", model="Corolla"):
    return client.post(
        "/api/vtc/vehicules",
        headers=auth_headers(actor),
        json={
            "make": make,
            "model": model,
            "year": 2020,
            "registration": registration,
            "acquisition_cost": "15000000.00",
        },
    )


def _create_affectation(client, actor, driver_id, vehicle_id, start, end=None, expected="100000.00"):
    return client.post(
        "/api/vtc/affectations",
        headers=auth_headers(actor),
        json={
            "driver_id": str(driver_id),
            "vehicle_id": str(vehicle_id),
            "start_date": start,
            "end_date": end,
            "expected_amount": expected,
            "terms": "Location journaliere",
        },
    )


def _versement(client, actor, driver_id, vehicle_id, amount, account_id, category_id, occurred_at=None):
    payload = {
        "driver_id": str(driver_id),
        "vehicle_id": str(vehicle_id),
        "amount": amount,
        "account_id": str(account_id),
        "category_id": str(category_id),
    }
    if occurred_at is not None:
        payload["occurred_at"] = occurred_at
    return client.post(
        "/api/vtc/versements",
        headers=auth_headers(actor),
        json=payload,
    )


def _depense(client, actor, vehicle_id, expense_type, amount, account_id, category_id):
    return client.post(
        "/api/vtc/depenses",
        headers=auth_headers(actor),
        json={
            "vehicle_id": str(vehicle_id),
            "expense_type": expense_type,
            "amount": amount,
            "account_id": str(account_id),
            "category_id": str(category_id),
        },
    )


def _chauffeur_vehicule_affectation(client, db, actor, vtc_business, reg="AB-123-CD"):
    link_person_to_business(db, actor.person, vtc_business)
    ch = _create_chauffeur(client, actor, "Boubacar").json()
    veh = _create_vehicule(client, actor, reg).json()
    af = _create_affectation(
        client, actor, ch["id"], veh["id"], date.today().isoformat()
    ).json()
    return ch, veh, af


def test_chauffeur_aussi_person_sans_compte(client, root, db):
    r = _create_chauffeur(client, root, "Mamadou", license_no="LIC-001")
    assert r.status_code == 201
    body = r.json()
    assert body["full_name"] == "Mamadou"
    assert body["license_number"] == "LIC-001"
    assert body["status"] == "active"
    assert body["person_id"]

    from app.modules.identity.models import Person
    person = db.get(Person, uuid.UUID(body["person_id"]))
    assert person is not None
    assert person.full_name == "Mamadou"


def test_creation_vehicule_et_liste(client, root):
    r = _create_vehicule(client, root, "XY-789-EF")
    assert r.status_code == 201
    body = r.json()
    assert body["make"] == "Toyota"
    assert body["registration"] == "XY-789-EF"
    assert Decimal(body["acquisition_cost"]) == Decimal("15000000.00")

    rows = client.get("/api/vtc/vehicules", headers=auth_headers(root)).json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["id"]


def test_creation_vehicule_sans_prix_refusee(client, root):
    r = client.post(
        "/api/vtc/vehicules",
        headers=auth_headers(root),
        json={"make": "Kia", "model": "Sportage", "year": 2013, "registration": "KO-000-ZZ"},
    )
    assert r.status_code == 422


def test_create_affectation_et_versements(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business)
    account = create_account(client, root, vtc_business, name="Caisse VTC")
    category = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")

    assert af["expected_amount"] == "100000.00"
    assert af["remaining_amount"] == "100000.00"

    v1 = _versement(client, co_owner, ch["id"], veh["id"], "60000.00", account["id"], category["id"])
    assert v1.status_code == 201

    v2 = _versement(client, co_owner, ch["id"], veh["id"], "40000.00", account["id"], category["id"])
    assert v2.status_code == 201

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("100000.00")

    af_after = client.get(f"/api/vtc/affectations/{af['id']}", headers=auth_headers(co_owner)).json()
    assert af_after["paid_amount"] == "100000.00"
    assert af_after["remaining_amount"] == "0.00"


def test_versement_hors_periode_affectation_refuse(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business)
    account = create_account(client, root, vtc_business, name="Caisse VTC Periode")
    category = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")

    before_assignment = (date.today() - timedelta(days=10)).isoformat()
    hors_periode = _versement(
        client,
        co_owner,
        ch["id"],
        veh["id"],
        "10000.00",
        account["id"],
        category["id"],
        occurred_at=f"{before_assignment}T12:00:00",
    )
    assert hors_periode.status_code == 400
    assert "affectation" in hors_periode.json()["detail"]


def test_affectation_chevauchement_refuse(client, db, vtc_business, co_owner):
    link_person_to_business(db, co_owner.person, vtc_business)
    ch = _create_chauffeur(client, co_owner, "Ali").json()
    veh = _create_vehicule(client, co_owner, "CD-123-EF").json()

    start = date.today().isoformat()
    assert _create_affectation(client, co_owner, ch["id"], veh["id"], start).status_code == 201
    dup = _create_affectation(client, co_owner, ch["id"], veh["id"], start)
    assert dup.status_code == 400
    assert "Chevauchement" in dup.json()["detail"]


def test_indisponibilite_bloque_affectation(client, db, vtc_business, co_owner):
    link_person_to_business(db, co_owner.person, vtc_business)
    ch = _create_chauffeur(client, co_owner, "Ousmane").json()
    veh = _create_vehicule(client, co_owner, "EF-456-GH").json()

    start = date.today().isoformat()

    indispo = client.post(
        "/api/vtc/indisponibilites",
        headers=auth_headers(co_owner),
        json={"vehicle_id": str(veh["id"]), "start_date": start, "reason": "Panne moteur"},
    )
    assert indispo.status_code == 201

    af = _create_affectation(client, co_owner, ch["id"], veh["id"], start)
    assert af.status_code == 400
    assert "indisponibilite" in af.json()["detail"].lower()


def test_indisponibilite_refusee_pendant_affectation_active(client, db, vtc_business, co_owner):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="GH-789-IJ")

    indispo = client.post(
        "/api/vtc/indisponibilites",
        headers=auth_headers(co_owner),
        json={"vehicle_id": str(veh["id"]), "start_date": date.today().isoformat()},
    )
    assert indispo.status_code == 400
    assert "affectation" in indispo.json()["detail"].lower()


def test_depense_debite_le_grand_livre(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="IJ-101-KL")
    account = create_account(client, root, vtc_business, name="Caisse VTC Depenses")
    cat_achat = create_category(client, root, code="vtc-carburant", name="Carburant", ctype="debit")

    e = _depense(client, co_owner, veh["id"], "fuel", "25000.00", account["id"], cat_achat["id"])
    assert e.status_code == 201
    assert e.json()["expense_type"] == "fuel"

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("-25000.00")


def test_cloture_affectation_versements_excedentaires_refusee(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="KL-202-MN")
    account = create_account(client, root, vtc_business, name="Caisse VTC Cloture")
    category = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")

    assert _versement(client, co_owner, ch["id"], veh["id"], "150000.00", account["id"], category["id"]).status_code == 201

    end = client.patch(
        f"/api/vtc/affectations/{af['id']}/end",
        headers=auth_headers(co_owner),
        json={"end_date": date.today().isoformat()},
    )
    assert end.status_code == 400
    assert "depassent" in end.json()["detail"]


def test_cloture_affectation_normale(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="MN-303-OP")
    account = create_account(client, root, vtc_business, name="Caisse VTC Cloture OK")
    category = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")

    assert _versement(client, co_owner, ch["id"], veh["id"], "100000.00", account["id"], category["id"]).status_code == 201

    end = client.patch(
        f"/api/vtc/affectations/{af['id']}/end",
        headers=auth_headers(co_owner),
        json={},
    )
    assert end.status_code == 200
    assert end.json()["status"] == "ended"


def test_statut_paiement_chauffeur(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="OP-404-QR")
    account = create_account(client, root, vtc_business, name="Caisse VTC Statut")
    category = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")

    assert _versement(client, co_owner, ch["id"], veh["id"], "60000.00", account["id"], category["id"]).status_code == 201

    statut = client.get(f"/api/vtc/paiements/{ch['id']}", headers=auth_headers(co_owner)).json()
    assert Decimal(statut["total_expected"]) == Decimal("100000.00")
    assert Decimal(statut["total_paid"]) == Decimal("60000.00")
    assert Decimal(statut["total_remaining"]) == Decimal("40000.00")


def test_statistiques_vehicule_et_resume_financier(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="QR-505-ST")
    account = create_account(client, root, vtc_business, name="Caisse VTC Stats")
    cat_vere = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")
    cat_fuel = create_category(client, root, code="vtc-carburant", name="Carburant", ctype="debit")

    assert _versement(client, co_owner, ch["id"], veh["id"], "100000.00", account["id"], cat_vere["id"]).status_code == 201
    assert _depense(client, co_owner, veh["id"], "fuel", "30000.00", account["id"], cat_fuel["id"]).status_code == 201

    stats = client.get(f"/api/vtc/vehicules/{veh['id']}/stats", headers=auth_headers(co_owner)).json()
    assert Decimal(stats["versements"]) == Decimal("100000.00")
    assert Decimal(stats["depenses"]) == Decimal("30000.00")
    assert Decimal(stats["rentabilite"]) == Decimal("70000.00")
    assert Decimal(stats["depenses_par_type"]["fuel"]) == Decimal("30000.00")

    resume = client.get("/api/vtc/resume-financier", headers=auth_headers(co_owner)).json()
    assert Decimal(resume["totals"]["versements"]) == Decimal("100000.00")
    assert Decimal(resume["totals"]["depenses"]) == Decimal("30000.00")
    assert Decimal(resume["totals"]["net"]) == Decimal("70000.00")
    assert len(resume["per_vehicle"]) == 1
    assert resume["counts"]["vehicules_actifs"] == 1
    assert resume["counts"]["chauffeurs_actifs"] == 1
    assert resume["counts"]["affectations_actives"] == 1


def test_soldes_caisses_vtc(client, db, vtc_business, co_owner, root):
    ch, veh, af = _chauffeur_vehicule_affectation(client, db, co_owner, vtc_business, reg="ST-606-UV")
    account = create_account(client, root, vtc_business, name="Caisse VTC Soldes")
    category = create_category(client, root, code="vtc-versements", name="Versements", ctype="credit")

    assert _versement(client, co_owner, ch["id"], veh["id"], "50000.00", account["id"], category["id"]).status_code == 201

    soldes = client.get("/api/vtc/soldes-caisses", headers=auth_headers(co_owner)).json()
    assert Decimal(soldes["total"]) == Decimal("50000.00")
    assert len(soldes["accounts"]) >= 1


def test_acces_refuse_hors_vtc(client, db, vtc_business, co_owner, assurance):
    link_person_to_business(db, co_owner.person, assurance)
    r = client.get("/api/vtc/vehicules", headers=auth_headers(co_owner))
    assert r.status_code == 403