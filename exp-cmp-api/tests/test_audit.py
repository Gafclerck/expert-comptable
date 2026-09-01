from tests.conftest import auth_headers, link_person_to_business, make_user
from app.modules.audit.models import AuditLog


def test_journalisation_dune_transaction(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)

    account = client.post(
        "/api/ledger/accounts",
        headers=auth_headers(root),
        json={"business_id": str(assurance.id), "name": "Caisse", "type": "cash"},
    ).json()
    category = client.post(
        "/api/ledger/categories",
        headers=auth_headers(root),
        json={"code": "primes-audit", "name": "Primes", "type": "credit"},
    ).json()

    client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": account["id"],
            "type": "revenue",
            "amount": "25000.00",
            "lines": [{"category_id": category["id"], "amount": "25000.00", "direction": "credit"}],
        },
    )

    logs = db.query(AuditLog).all()
    actions = {(log.entity_type, log.action.value) for log in logs}
    assert ("accounts", "CREATE") in actions
    assert ("categories", "CREATE") in actions
    assert ("transactions", "CREATE") in actions


def test_journalisation_transfer(client, root, db, assurance, poulets, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    link_person_to_business(db, co_owner.person, poulets)

    src = client.post(
        "/api/ledger/accounts",
        headers=auth_headers(root),
        json={"business_id": str(assurance.id), "name": "Src", "type": "cash"},
    ).json()
    dst = client.post(
        "/api/ledger/accounts",
        headers=auth_headers(root),
        json={"business_id": str(poulets.id), "name": "Dst", "type": "cash"},
    ).json()

    client.post(
        "/api/ledger/transfers",
        headers=auth_headers(co_owner),
        json={
            "source_account_id": src["id"],
            "destination_account_id": dst["id"],
            "amount": "50000.00",
        },
    )

    logs = db.query(AuditLog).all()
    assert any(log.entity_type == "transfers" and log.action.value == "TRANSFER" for log in logs)


def test_historique_reserve_root(client, root, co_owner):
    assert client.get("/api/audit/logs", headers=auth_headers(co_owner)).status_code == 403
    response = client.get("/api/audit/logs", headers=auth_headers(root))
    assert response.status_code == 200


def test_creation_user_journalise(client, root, db):
    client.post(
        "/api/identity/users",
        headers=auth_headers(root),
        json={
            "email": "owner.journalise@example.com",
            "password": "mot-de-passe-owner",
            "full_name": "Owner Journalise",
            "is_root": False,
        },
    )
    logs = db.query(AuditLog).all()
    assert any(log.entity_type == "users" and log.action.value == "CREATE" for log in logs)


def test_filtre_par_action(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    client.post(
        "/api/ledger/accounts",
        headers=auth_headers(root),
        json={"business_id": str(assurance.id), "name": "Caisse", "type": "bank"},
    )
    response = client.get(
        "/api/audit/logs",
        headers=auth_headers(root),
        params={"entity_type": "accounts"},
    )
    assert response.status_code == 200
    assert all(log["entity_type"] == "accounts" for log in response.json())