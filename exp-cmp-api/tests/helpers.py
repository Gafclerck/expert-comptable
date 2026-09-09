import uuid

from app.core.security import create_access_token, hash_password
from app.modules.identity.models import BusinessAccount, BusinessAccountRole, Person, Role, RoleCode, User, UserStatus


def make_user(db, email=None, is_root=False, person=None, active=True, **overrides) -> User:
    person = person or overrides.get("person")
    if person is None:
        person = Person(full_name=overrides.get("full_name", f"Personne {uuid.uuid4().hex[:6]}"))
        db.add(person)
        db.flush()
    if person.id is None:
        db.add(person)
        db.flush()
    user = User(
        email=email or f"{uuid.uuid4().hex[:10]}@example.com",
        password_hash=hash_password(overrides.get("password", "mot-de-passe-123")),
        person_id=person.id,
        status=UserStatus.ACTIVE if active else UserStatus.INACTIVE,
    )
    if is_root:
        root_role = db.query(Role).filter(Role.code == RoleCode.ROOT.value).one()
        user.roles = [root_role]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def link_person_to_business(db, person, business, role=BusinessAccountRole.OWNER) -> BusinessAccount:
    ba = BusinessAccount(business_id=business.id, person_id=person.id, role=role)
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return ba


def create_account(client, actor, business, name="Caisse principale", acct_type="cash") -> dict:
    response = client.post(
        "/api/ledger/accounts",
        headers=auth_headers(actor),
        json={"business_id": str(business.id), "name": name, "type": acct_type},
    )
    assert response.status_code == 201
    return response.json()


def create_category(client, actor, code="vente-primes", name="Vente de primes", ctype="credit") -> dict:
    response = client.post(
        "/api/ledger/categories",
        headers=auth_headers(actor),
        json={"code": code, "name": name, "type": ctype},
    )
    if response.status_code == 400 and "existe deja" in response.text:
        res = client.get("/api/ledger/categories", headers=auth_headers(actor))
        for c in res.json():
            if c["code"] == code:
                return c
    assert response.status_code == 201
    return response.json()