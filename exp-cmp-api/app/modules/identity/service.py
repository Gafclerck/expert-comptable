import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.events import publish
from app.core.security import (
    DUMPMY_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.identity.models import (
    Business,
    BusinessAccount,
    BusinessAccountRole,
    BusinessStatus,
    Person,
    Role,
    RoleCode,
    User,
    UserStatus,
)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token invalide ou expire",
    headers={"WWW-Authenticate": "Bearer"},
)


def _to_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "status": user.status,
        "person_id": user.person_id,
        "person_full_name": user.person.full_name if user.person else None,
        "roles": [r.code for r in user.roles],
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


def is_root(user: User) -> bool:
    return any(r.code == RoleCode.ROOT.value for r in user.roles)


def get_user_from_token(db: Session, token: str) -> User | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            return None
        email = payload.get("sub")
        if email is None:
            return None
    except (InvalidTokenError, jwt.ExpiredSignatureError):
        return None
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        verify_password(password, DUMPMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def login_user(db: Session, form_data: OAuth2PasswordRequestForm) -> dict:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte inactif",
        )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            data={"sub": user.email}, expires_delta=expires_delta
        ),
        "refresh_token": create_refresh_token(data={"sub": user.email}),
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except (InvalidTokenError, jwt.ExpiredSignatureError):
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None or user.status != UserStatus.ACTIVE:
        raise credentials_exception
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            data={"sub": user.email}, expires_delta=expires_delta
        ),
        "refresh_token": create_refresh_token(data={"sub": user.email}),
        "token_type": "bearer",
    }


def change_password(db: Session, user: User, ancien: str, nouveau: str) -> None:
    if not verify_password(ancien, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'ancien mot de passe est incorrect",
        )
    user.password_hash = hash_password(nouveau)
    db.commit()


def get_person(db: Session, person_id: uuid.UUID) -> Person:
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Personne introuvable")
    return person


def create_person(
    db: Session, actor: User, full_name: str, phone: str | None = None, *, commit: bool = True
) -> Person:
    person = Person(full_name=full_name, phone=phone)
    db.add(person)
    if commit:
        db.commit()
        db.refresh(person)
        publish(
            "identity.person.created",
            actor_id=str(actor.id),
            entity_id=str(person.id),
            new_values={"full_name": person.full_name, "phone": person.phone},
        )
    else:
        db.flush()
        db.refresh(person)
    return person


def update_person(db: Session, actor: User, person_id: uuid.UUID, data: dict) -> Person:
    person = get_person(db, person_id)
    updates = {k: v for k, v in data.items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ a modifier")
    old = {"full_name": person.full_name, "phone": person.phone}
    for field, value in updates.items():
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    publish(
        "identity.person.updated",
        actor_id=str(actor.id),
        entity_id=str(person.id),
        old_values=old,
        new_values={"full_name": person.full_name, "phone": person.phone},
    )
    return person


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.code).all()


def create_user(
    db: Session,
    actor: User,
    email: EmailStr,
    password: str,
    full_name: str,
    phone: str | None,
    is_root: bool,
) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Cet email est deja utilise")
    roles = [db.query(Role).filter(Role.code == RoleCode.ROOT.value).one()] if is_root else []
    person = create_person(db, actor, full_name=full_name, phone=phone)
    user = User(
        email=email,
        password_hash=hash_password(password),
        person_id=person.id,
        status=UserStatus.ACTIVE,
    )
    user.roles = roles
    db.add(user)
    db.commit()
    db.refresh(user)
    publish(
        "identity.user.created",
        actor_id=str(actor.id),
        entity_id=str(user.id),
        new_values={"email": user.email, "is_root": is_root},
    )
    return user


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    return (
        db.query(User)
        .filter(User.status == UserStatus.ACTIVE)
        .order_by(User.created_at)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_user(db: Session, actor: User, user_id: uuid.UUID, data: dict) -> User:
    user = get_user(db, user_id)
    old = {"email": user.email, "status": user.status, "is_root": is_root(user)}
    if "email" in data and data["email"] and data["email"] != user.email:
        existing = db.query(User).filter(User.email == data["email"], User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Cet email est deja utilise")
        user.email = data["email"]
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data["password"])
    if "status" in data and data["status"]:
        user.status = data["status"]
    if "is_root" in data and data["is_root"] is not None:
        root_role = db.query(Role).filter(Role.code == RoleCode.ROOT.value).one()
        current = set(user.roles)
        if data["is_root"]:
            current.add(root_role)
        else:
            current.discard(root_role)
        user.roles = list(current)
    db.commit()
    db.refresh(user)
    publish(
        "identity.user.updated",
        actor_id=str(actor.id),
        entity_id=str(user.id),
        old_values=old,
        new_values={"email": user.email, "status": user.status, "is_root": is_root(user)},
    )
    return user


def deactivate_user(db: Session, actor: User, user_id: uuid.UUID) -> User:
    user = get_user(db, user_id)
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="Impossible de desactiver son propre compte")
    user.status = UserStatus.INACTIVE
    db.commit()
    db.refresh(user)
    publish(
        "identity.user.updated",
        actor_id=str(actor.id),
        entity_id=str(user.id),
        old_values={"status": UserStatus.ACTIVE},
        new_values={"status": UserStatus.INACTIVE},
    )
    return user


def list_businesses(db: Session, skip: int = 0, limit: int = 100) -> list[Business]:
    return (
        db.query(Business)
        .filter(Business.status == BusinessStatus.ACTIVE)
        .order_by(Business.code)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_business(db: Session, business_id: uuid.UUID) -> Business:
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Activite introuvable")
    return business


def get_business_by_code(db: Session, code: str) -> Business:
    business = db.query(Business).filter(Business.code == code).first()
    if not business:
        raise HTTPException(status_code=404, detail=f"Activite {code} introuvable")
    return business


def create_business(db: Session, actor: User, code: str, name: str) -> Business:
    if db.query(Business).filter(Business.code == code).first():
        raise HTTPException(status_code=400, detail="Ce code d'activite existe deja")
    business = Business(code=code, name=name, status=BusinessStatus.ACTIVE)
    db.add(business)
    db.commit()
    db.refresh(business)
    publish(
        "identity.business.created",
        actor_id=str(actor.id),
        entity_id=str(business.id),
        new_values={"code": business.code, "name": business.name},
    )
    return business


def update_business(db: Session, actor: User, business_id: uuid.UUID, name: str | None, new_status) -> Business:
    business = get_business(db, business_id)
    if name:
        business.name = name
    if new_status:
        business.status = new_status
    db.commit()
    db.refresh(business)
    publish(
        "identity.business.updated",
        actor_id=str(actor.id),
        entity_id=str(business.id),
        old_values={"name": business.name, "status": business.status},
        new_values={"name": business.name, "status": business.status},
    )
    return business


def create_business_account(
    db: Session,
    actor: User,
    business_id: uuid.UUID,
    person_id: uuid.UUID,
    role: BusinessAccountRole,
    *,
    commit: bool = True,
) -> BusinessAccount:
    business = get_business(db, business_id)
    person = get_person(db, person_id)
    existing = (
        db.query(BusinessAccount)
        .filter(BusinessAccount.business_id == business.id, BusinessAccount.person_id == person.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Cette personne est deja rattachee a cette activite")
    account = BusinessAccount(business_id=business.id, person_id=person.id, role=role)
    db.add(account)
    if commit:
        db.commit()
        db.refresh(account)
        publish(
            "identity.business_account.created",
            actor_id=str(actor.id),
            entity_id=str(account.id),
            new_values={
                "business_id": str(account.business_id),
                "person_id": str(account.person_id),
                "role": account.role.value,
            },
        )
    else:
        db.flush()
        db.refresh(account)
    return account


def list_business_accounts(db: Session, business_id: uuid.UUID) -> list[dict]:
    business = get_business(db, business_id)
    rows = (
        db.query(BusinessAccount, Person)
        .join(Person, Person.id == BusinessAccount.person_id)
        .filter(BusinessAccount.business_id == business.id)
        .all()
    )
    return [
        {
            "id": ba.id,
            "business_id": ba.business_id,
            "person_id": ba.person_id,
            "role": ba.role,
            "person_full_name": person.full_name,
        }
        for ba, person in rows
    ]


def me(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.person.full_name if user.person else None,
        "roles": [r.code for r in user.roles],
    }


def get_person_summary(db: Session, person_id: uuid.UUID) -> Person:
    return get_person(db, person_id)


def add_business_customer(
    db: Session, actor: User, business_id: uuid.UUID, person_id: uuid.UUID, *, commit: bool = True
) -> BusinessAccount:
    return create_business_account(
        db, actor, business_id, person_id, BusinessAccountRole.CUSTOMER, commit=commit
    )


def business_exists(db: Session, business_id: uuid.UUID) -> bool:
    return db.get(Business, business_id) is not None


def get_business_ids_for_user(db: Session, user: User) -> set[uuid.UUID] | None:
    if is_root(user):
        return None
    if user.person_id is None:
        return set()
    rows = (
        db.query(BusinessAccount.business_id)
        .filter(
            BusinessAccount.person_id == user.person_id,
            BusinessAccount.role == BusinessAccountRole.OWNER,
        )
        .all()
    )
    return {row[0] for row in rows}