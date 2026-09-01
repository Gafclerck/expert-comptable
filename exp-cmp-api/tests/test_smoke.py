def test_app_boot_et_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_endpoint_protege_refuse_sans_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_token_invalide_refuse(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer token-fantome"})
    assert response.status_code == 401


def test_les_routes_modules_sont_montees(client):
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]
    for attendu in [
        "/api/auth/login",
        "/api/auth/me",
        "/api/auth/refresh",
        "/api/identity/users",
        "/api/identity/businesses",
        "/api/identity/roles",
        "/api/ledger/accounts",
        "/api/ledger/categories",
        "/api/ledger/transactions",
        "/api/ledger/transfers",
        "/api/audit/logs",
        "/api/insurance/clients",
        "/api/insurance/contracts/{contract_id}/payments",
    ]:
        assert attendu in paths, f"route manquante : {attendu}"