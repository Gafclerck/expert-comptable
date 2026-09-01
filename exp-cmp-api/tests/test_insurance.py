from datetime import date
from decimal import Decimal

from tests.conftest import auth_headers, link_person_to_business, make_user
from tests.helpers import create_account, create_category


def _create_client(client, actor, name="Tagoun", phone=None, client_number=None):
    response = client.post(
        "/api/insurance/clients",
        headers=auth_headers(actor),
        json={"full_name": name, "phone": phone, "client_number": client_number},
    )
    return response


def _create_contract(client, actor, client_id, matricule="MAT-001", premium="100000.00"):
    response = client.post(
        f"/api/insurance/clients/{client_id}/contracts",
        headers=auth_headers(actor),
        json={
            "matricule": matricule,
            "contract_type": "assurance-auto",
            "premium": premium,
            "start_date": "2026-09-01",
            "end_date": "2027-08-31",
        },
    )
    return response


def _encaisse(client, actor, contract_id, amount, account_id, category_id):
    return client.post(
        f"/api/insurance/contracts/{contract_id}/payments",
        headers=auth_headers(actor),
        json={"amount": amount, "account_id": str(account_id), "category_id": str(category_id)},
    )


def test_creation_client_avec_numero_auto(client, root):
    r = _create_client(client, root, name="Moussa")
    assert r.status_code == 201
    body = r.json()
    assert body["client_number"] == "CLI-00001"
    assert body["full_name"] == "Moussa"
    assert body["phone"] is None
    assert body["status"] == "active"


def test_numero_client_duplique_refuse(client, root):
    assert _create_client(client, root, client_number="CLI-X").status_code == 201
    assert _create_client(client, root, client_number="CLI-X").status_code == 400


def test_creation_contrat_et_matricule_unique_parmi_actifs(client, root):
    client_id = _create_client(client, root).json()["id"]
    first = _create_contract(client, root, client_id, matricule="MAT-100")
    assert first.status_code == 201
    assert Decimal(first.json()["premium"]) == Decimal("100000.00")

    dup = _create_contract(client, root, client_id, matricule="MAT-100")
    assert dup.status_code == 400


def test_encaisser_prime_credite_le_solde_et_audit(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    account = create_account(client, root, assurance, name="Caisse Assurance")
    category = create_category(client, root, code="primes-enca", name="Primes", ctype="credit")

    client_id = _create_client(client, co_owner).json()["id"]
    contract = _create_contract(client, co_owner, client_id, matricule="MAT-200", premium="100000.00").json()

    payment = _encaisse(client, co_owner, contract["id"], "40000.00", account["id"], category["id"])
    assert payment.status_code == 201
    assert payment.json()["transaction_id"]

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("40000.00")

    contract_after = client.get(f"/api/insurance/contracts/{contract['id']}", headers=auth_headers(co_owner)).json()
    assert Decimal(contract_after["remaining_amount"]) == Decimal("60000.00")

    from app.modules.audit.models import AuditLog
    types = {log.entity_type for log in db.query(AuditLog).all()}
    assert {"insurance_clients", "insurance_contracts", "insurance_payments", "transactions"} <= types


def test_paiement_complet_et_depassement_refuse(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    account = create_account(client, root, assurance, name="Caisse Assurance")
    category = create_category(client, root, code="primes-full", name="Primes", ctype="credit")

    client_id = _create_client(client, co_owner).json()["id"]
    contract = _create_contract(client, co_owner, client_id, matricule="MAT-300", premium="50000.00").json()

    first = _encaisse(client, co_owner, contract["id"], "50000.00", account["id"], category["id"])
    assert first.status_code == 201

    over = _encaisse(client, co_owner, contract["id"], "1.00", account["id"], category["id"])
    assert over.status_code == 400


def test_acces_refuse_hors_assurance(client, db, assurance, co_owner, poulets):
    link_person_to_business(db, co_owner.person, poulets)
    response = _create_client(client, co_owner)
    assert response.status_code == 403


def test_liste_clients_et_contrats(client, root):
    client_id = _create_client(client, root, name="Awa").json()["id"]
    _create_contract(client, root, client_id, matricule="MAT-400")

    clients = client.get("/api/insurance/clients", headers=auth_headers(root)).json()
    assert any(c["full_name"] == "Awa" for c in clients)

    contracts = client.get(f"/api/insurance/clients/{client_id}/contracts", headers=auth_headers(root)).json()
    assert [c["matricule"] for c in contracts] == ["MAT-400"]


def test_date_fin_anterieure_refusee(client, root):
    client_id = _create_client(client, root).json()["id"]
    response = client.post(
        f"/api/insurance/clients/{client_id}/contracts",
        headers=auth_headers(root),
        json={
            "matricule": "MAT-X",
            "contract_type": "assurance-auto",
            "premium": "10000.00",
            "start_date": "2026-09-01",
            "end_date": "2026-01-01",
        },
    )
    assert response.status_code == 400