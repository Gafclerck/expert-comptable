from decimal import Decimal

from tests.conftest import auth_headers, link_person_to_business, make_user
from tests.helpers import create_account, create_category
from app.modules.identity.models import BusinessAccountRole


def test_creation_compte_et_categorie(client, root, assurance):
    account = create_account(client, root, assurance)
    assert account["currency"] == "FCFA"

    category = create_category(client, root)
    assert category["code"] == "vente-primes"


def test_caisse_seedee_chaque_business_a_son_propre_nom(client, root, assurance, poulets, vtc):
    # init_db seede une caisse unique par activite avec un nom specifique
    # (jamais generique) : Assurance / Poulailler / VTC.
    accounts = client.get("/api/ledger/accounts", headers=auth_headers(root)).json()
    names_by_business = {a["business_id"]: a["name"] for a in accounts}
    assert names_by_business[str(assurance.id)] == "Caisse Assurance"
    assert names_by_business[str(poulets.id)] == "Caisse Poulailler"
    assert names_by_business[str(vtc.id)] == "Caisse VTC"


def test_creation_compte_refusee_aux_non_root(client, assurance, co_owner):
    response = client.post(
        "/api/ledger/accounts",
        headers=auth_headers(co_owner),
        json={"business_id": str(assurance.id), "name": "Caisse", "type": "cash"},
    )
    assert response.status_code == 403


def test_list_comptes_scope_par_business(client, root, db, assurance, poulets, co_owner):
    link_person_to_business(db, co_owner.person, assurance)

    response = client.get("/api/ledger/accounts", headers=auth_headers(co_owner))
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 1
    assert accounts[0]["business_id"] == str(assurance.id)
    assert accounts[0]["active"] is True


def test_encaisser_prime_alimente_le_solde(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    account = create_account(client, root, assurance, name="Caisse Assurance")
    category = create_category(client, root, code="primes", name="Primes", ctype="credit")

    response = client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": account["id"],
            "type": "revenue",
            "amount": "50000.00",
            "description": "Prime client X",
            "lines": [
                {"category_id": category["id"], "amount": "50000.00", "direction": "credit"}
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["immutable"] is True
    assert Decimal(body["amount"]) == Decimal("50000.00")

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("50000.00")


def test_depense_reduit_le_solde(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    account = create_account(client, root, assurance)
    credit_category = create_category(client, root, code="igp", name="IGP", ctype="credit")
    debit_category = create_category(client, root, code="achat-fournitures", name="Fournitures", ctype="debit")

    client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": account["id"],
            "type": "revenue",
            "amount": "100000.00",
            "lines": [{"category_id": credit_category["id"], "amount": "100000.00", "direction": "credit"}],
        },
    )
    depense = client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": account["id"],
            "type": "expense",
            "amount": "30000.00",
            "lines": [{"category_id": debit_category["id"], "amount": "30000.00", "direction": "debit"}],
        },
    )
    assert depense.status_code == 201

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("70000.00")


def test_transaction_avec_ventilation_sur_plusieurs_activites(client, root, db, assurance, poulets, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    account = create_account(client, root, assurance)
    debit_category = create_category(client, root, code="wifi", name="Wi-Fi", ctype="debit")

    response = client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": account["id"],
            "type": "expense",
            "amount": "100000.00",
            "description": "Facture Wi-Fi",
            "lines": [{"category_id": debit_category["id"], "amount": "100000.00", "direction": "debit"}],
            "allocations": [
                {"business_id": str(assurance.id), "amount": "50000.00"},
                {"business_id": str(poulets.id), "amount": "50000.00"},
            ],
        },
    )
    assert response.status_code == 201
    allocations = response.json()["allocations"]
    assert len(allocations) == 2
    assert Decimal(allocations[0]["amount"]) == Decimal("50000.00")
    assert Decimal(allocations[0]["percentage"]) == Decimal("50.0000")


def test_lignes_de_montant_incoherent_refuse(client, root, db, assurance, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    account = create_account(client, root, assurance)
    category = create_category(client, root, code="primes-v2", name="Primes", ctype="credit")

    response = client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": account["id"],
            "type": "revenue",
            "amount": "1000.00",
            "lines": [{"category_id": category["id"], "amount": "500.00", "direction": "credit"}],
        },
    )
    assert response.status_code == 400


def test_transfer_entre_caisses(client, root, db, assurance, poulets, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    link_person_to_business(db, co_owner.person, poulets)
    assurance_account = create_account(client, root, assurance, name="Caisse Assurance")
    poulets_account = create_account(client, root, poulets, name="Caisse Poulets")
    credit_category = create_category(client, root, code="primes-t", name="Primes T", ctype="credit")

    client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(assurance.id),
            "account_id": assurance_account["id"],
            "type": "revenue",
            "amount": "200000.00",
            "lines": [{"category_id": credit_category["id"], "amount": "200000.00", "direction": "credit"}],
        },
    )

    response = client.post(
        "/api/ledger/transfers",
        headers=auth_headers(co_owner),
        json={
            "source_account_id": assurance_account["id"],
            "destination_account_id": poulets_account["id"],
            "amount": "150000.00",
            "reference": "Financement poulets",
        },
    )
    assert response.status_code == 201

    assurance_balance = client.get(
        f"/api/ledger/accounts/{assurance_account['id']}/balance", headers=auth_headers(co_owner)
    ).json()
    poulets_balance = client.get(
        f"/api/ledger/accounts/{poulets_account['id']}/balance", headers=auth_headers(co_owner)
    ).json()
    assert Decimal(assurance_balance["balance"]) == Decimal("50000.00")
    assert Decimal(poulets_balance["balance"]) == Decimal("150000.00")


def test_transaction_non_autorisee_hors_activite(client, root, db, assurance, poulets, co_owner):
    link_person_to_business(db, co_owner.person, assurance)
    create_account(client, root, poulets, name="Caisse Poulets")

    response = client.post(
        "/api/ledger/transactions",
        headers=auth_headers(co_owner),
        json={
            "business_id": str(poulets.id),
            "account_id": "00000000-0000-0000-0000-000000000000",
            "type": "revenue",
            "amount": "1000.00",
            "lines": [{"category_id": "00000000-0000-0000-0000-000000000000", "amount": "1000.00", "direction": "credit"}],
        },
    )
    assert response.status_code == 403


def test_caisse_par_defaut_a_la_creation_business(client, root):
    # Creer une nouvelle activite via API
    res = client.post(
        "/api/identity/businesses",
        headers=auth_headers(root),
        json={"code": "boulangerie", "name": "Boulangerie Moderne"},
    )
    assert res.status_code == 201
    business_id = res.json()["id"]

    # Verifier qu'une caisse nommee (non generique) a ete automatiquement creee
    accounts = client.get(f"/api/ledger/accounts?business_id={business_id}", headers=auth_headers(root)).json()
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Caisse Boulangerie Moderne"
    assert accounts[0]["type"] == "cash"
    assert accounts[0]["currency"] == "FCFA"
    assert float(accounts[0]["opening_balance"]) == 0.0