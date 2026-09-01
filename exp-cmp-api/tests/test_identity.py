import uuid

from tests.conftest import auth_headers, link_person_to_business, make_user


def test_login_root(client, root):
    response = client.post(
        "/api/auth/login",
        data={"username": "root@example.com", "password": "mot-de-passe-root"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_echec(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "inexistant@example.com", "password": "mauvais-mot-de-passe"},
    )
    assert response.status_code == 401


def test_refresh_token(client, root):
    login = client.post(
        "/api/auth/login",
        data={"username": "root@example.com", "password": "mot-de-passe-root"},
    ).json()
    response = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_me(client, root):
    response = client.get("/api/auth/me", headers=auth_headers(root))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "root@example.com"
    assert "root" in body["roles"]


def test_me_reserve_aux_authentifies(client, co_owner):
    response = client.get("/api/auth/me", headers=auth_headers(co_owner))
    assert response.status_code == 200


def test_creation_coowner_par_root_sans_role(client, root):
    response = client.post(
        "/api/identity/users",
        headers=auth_headers(root),
        json={
            "email": "owner.alpha@example.com",
            "password": "mot-de-passe-owner",
            "full_name": "Owner Alpha",
            "is_root": False,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "owner.alpha@example.com"
    assert body["roles"] == []


def test_creation_root_par_root(client, root):
    response = client.post(
        "/api/identity/users",
        headers=auth_headers(root),
        json={
            "email": "autre-root@example.com",
            "password": "mot-de-passe-root2",
            "full_name": "Autre Root",
            "is_root": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["roles"] == ["root"]


def test_creation_user_refusee_aux_non_root(client, co_owner):
    response = client.post(
        "/api/identity/users",
        headers=auth_headers(co_owner),
        json={
            "email": "owner.beta@example.com",
            "password": "mot-de-passe-owner",
            "full_name": "Owner Beta",
            "is_root": False,
        },
    )
    assert response.status_code == 403


def test_creation_user_email_duplique(client, root, co_owner):
    response = client.post(
        "/api/identity/users",
        headers=auth_headers(root),
        json={
            "email": co_owner.email,
            "password": "mot-de-passe-owner",
            "full_name": "Doublon",
            "is_root": False,
        },
    )
    assert response.status_code == 400


def test_roles_visibles_par_tous(client, co_owner):
    response = client.get("/api/identity/roles", headers=auth_headers(co_owner))
    assert response.status_code == 200
    codes = [r["code"] for r in response.json()]
    assert codes == ["root"]


def test_patch_user_passe_en_root(client, root, co_owner):
    response = client.patch(
        f"/api/identity/users/{co_owner.id}",
        headers=auth_headers(root),
        json={"is_root": True},
    )
    assert response.status_code == 200
    assert response.json()["roles"] == ["root"]


def test_change_password(client, db, co_owner):
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(co_owner),
        json={
            "ancien_mot_de_passe": "mot-de-passe-123",
            "nouveau_mot_de_passe": "nouveau-mot-de-passe",
        },
    )
    assert response.status_code == 200
    login = client.post(
        "/api/auth/login",
        data={"username": co_owner.email, "password": "nouveau-mot-de-passe"},
    )
    assert login.status_code == 200


def test_list_users_reserve_root(client, root, co_owner):
    assert client.get("/api/identity/users", headers=auth_headers(co_owner)).status_code == 403
    assert client.get("/api/identity/users", headers=auth_headers(root)).status_code == 200


def test_businesses_et_business_accounts(client, db, root, assurance, co_owner):
    response = client.get("/api/identity/businesses", headers=auth_headers(co_owner))
    assert response.status_code == 200
    codes = [b["code"] for b in response.json()]
    assert "assurance" in codes

    response = client.post(
        f"/api/identity/businesses/{assurance.id}/accounts",
        headers=auth_headers(root),
        json={"person_id": str(co_owner.person_id), "role": "customer"},
    )
    assert response.status_code == 201
    assert response.json()["person_full_name"] is not None


def test_business_accounts_visibles(client, db, assurance, co_owner):
    person = co_owner.person
    link_person_to_business(db, person, assurance)
    response = client.get(
        f"/api/identity/businesses/{assurance.id}/accounts",
        headers=auth_headers(co_owner),
    )
    assert response.status_code == 200
    ids = [ba["person_id"] for ba in response.json()]
    assert str(co_owner.person_id) in ids