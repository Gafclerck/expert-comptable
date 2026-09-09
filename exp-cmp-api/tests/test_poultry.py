from decimal import Decimal

from tests.conftest import auth_headers, link_person_to_business
from tests.helpers import create_account, create_category


def _achat(client, user, quantity, total_amount, account_id, category_id):
    unit_price = (Decimal(total_amount) / quantity).quantize(Decimal("0.01"))
    return client.post(
        "/api/poultry/purchases",
        headers=auth_headers(user),
        json={
            "quantity": quantity,
            "unit_price": str(unit_price),
            "account_id": account_id,
            "category_id": category_id,
        },
    )


def _vente(client, user, quantity, total_amount, account_id, category_id):
    unit_price = (Decimal(total_amount) / quantity).quantize(Decimal("0.01"))
    return client.post(
        "/api/poultry/sales",
        headers=auth_headers(user),
        json={
            "quantity": quantity,
            "unit_price": str(unit_price),
            "account_id": account_id,
            "category_id": category_id,
        },
    )


def test_achat_cree_un_lot_et_debite_la_caisse(client, root, db, poulets, co_owner):
    link_person_to_business(db, co_owner.person, poulets)
    account = create_account(client, root, poulets, name="Caisse Poulailler")
    category = create_category(client, root, code="achat-poulets", name="Achat poulets", ctype="debit")

    response = _achat(client, co_owner, 24, "120000.00", account["id"], category["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["quantity"] == 24

    lots = client.get("/api/poultry/lots", headers=auth_headers(co_owner)).json()
    assert len(lots) == 1
    assert lots[0]["remaining_quantity"] == 24
    assert lots[0]["initial_quantity"] == 24

    stock = client.get("/api/poultry/stock", headers=auth_headers(co_owner)).json()
    assert stock["total_quantity"] == 24

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("-120000.00")


def test_vente_preleve_en_fifo_sur_plusieurs_lots(client, root, db, poulets, co_owner):
    link_person_to_business(db, co_owner.person, poulets)
    account = create_account(client, root, poulets, name="Caisse Poulailler FIFO")
    cat_achat = create_category(client, root, code="achat-fifo", name="Achat", ctype="debit")
    cat_vente = create_category(client, root, code="vente-fifo", name="Vente", ctype="credit")

    assert _achat(client, co_owner, 10, "50000.00", account["id"], cat_achat["id"]).status_code == 201
    assert _achat(client, co_owner, 10, "55000.00", account["id"], cat_achat["id"]).status_code == 201

    sale = _vente(client, co_owner, 15, "90000.00", account["id"], cat_vente["id"])
    assert sale.status_code == 201

    lots = sorted(
        client.get("/api/poultry/lots", headers=auth_headers(co_owner)).json(),
        key=lambda lot: lot["created_at"],
    )
    assert lots[0]["remaining_quantity"] == 0
    assert lots[1]["remaining_quantity"] == 5

    stock = client.get("/api/poultry/stock", headers=auth_headers(co_owner)).json()
    assert stock["total_quantity"] == 5

    balance = client.get(f"/api/ledger/accounts/{account['id']}/balance", headers=auth_headers(co_owner)).json()
    assert Decimal(balance["balance"]) == Decimal("-15000.00")


def test_vente_refuse_si_stock_insuffisant(client, root, db, poulets, co_owner):
    link_person_to_business(db, co_owner.person, poulets)
    account = create_account(client, root, poulets, name="Caisse Poulailler Stock")
    cat_achat = create_category(client, root, code="achat-stock", name="Achat", ctype="debit")
    cat_vente = create_category(client, root, code="vente-stock", name="Vente", ctype="credit")

    assert _achat(client, co_owner, 5, "25000.00", account["id"], cat_achat["id"]).status_code == 201

    over = _vente(client, co_owner, 10, "60000.00", account["id"], cat_vente["id"])
    assert over.status_code == 400

    stock = client.get("/api/poultry/stock", headers=auth_headers(co_owner)).json()
    assert stock["total_quantity"] == 5


def test_acces_refuse_hors_poulets(client, db, poulets, co_owner, assurance):
    link_person_to_business(db, co_owner.person, assurance)
    response = client.get("/api/poultry/lots", headers=auth_headers(co_owner))
    assert response.status_code == 403
