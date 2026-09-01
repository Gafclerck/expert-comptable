import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.core.deps import CurrentUser, RequireRoot, SessionDep, limiter
from app.modules.identity import service as identity_service
from app.modules.identity.schemas import (
    BusinessAccountCreate,
    BusinessAccountOut,
    BusinessCreate,
    BusinessOut,
    BusinessUpdate,
    ChangePasswordRequest,
    LoginResponse,
    MeOut,
    PersonCreate,
    PersonOut,
    PersonUpdate,
    RefreshRequest,
    RoleOut,
    UserCreate,
    UserOut,
    UserUpdate,
)

auth_router = APIRouter(prefix="/auth", tags=["identity"])
identity_router = APIRouter(prefix="/identity", tags=["identity"])


@auth_router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDep,
) -> LoginResponse:
    return identity_service.login_user(db, form_data)


@auth_router.post("/refresh", response_model=LoginResponse)
@limiter.limit("10/minute")
def refresh(
    request: Request,
    data: RefreshRequest,
    db: SessionDep,
) -> LoginResponse:
    return identity_service.refresh_access_token(db, data.refresh_token)


@auth_router.get("/me", response_model=MeOut)
def read_me(current_user: CurrentUser) -> MeOut:
    return MeOut.model_validate(identity_service.me(current_user))


@auth_router.post("/change-password")
def change_user_password(
    data: ChangePasswordRequest,
    db: SessionDep,
    current_user: CurrentUser,
) -> dict:
    identity_service.change_password(db, current_user, data.ancien_mot_de_passe, data.nouveau_mot_de_passe)
    return {"detail": "Mot de passe modifie avec succes"}


@identity_router.get("/roles", response_model=list[RoleOut])
def list_roles(db: SessionDep, current_user: CurrentUser) -> list[RoleOut]:
    return list(identity_service.list_roles(db))


@identity_router.post("/persons", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(
    data: PersonCreate,
    db: SessionDep,
    current_user: RequireRoot,
) -> PersonOut:
    person = identity_service.create_person(db, current_user, data.full_name, data.phone)
    return PersonOut.model_validate(person)


@identity_router.patch("/persons/{person_id}", response_model=PersonOut)
def patch_person(
    person_id: uuid.UUID,
    data: PersonUpdate,
    db: SessionDep,
    current_user: RequireRoot,
) -> PersonOut:
    person = identity_service.update_person(
        db, current_user, person_id, data.model_dump(exclude_unset=True)
    )
    return PersonOut.model_validate(person)


@identity_router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: SessionDep,
    current_user: RequireRoot,
) -> UserOut:
    user = identity_service.create_user(
        db,
        current_user,
        data.email,
        data.password,
        data.full_name,
        data.phone,
        data.is_root,
    )
    return UserOut.model_validate(identity_service._to_out(user))


@identity_router.get("/users", response_model=list[UserOut])
def list_users(
    db: SessionDep,
    current_user: RequireRoot,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[UserOut]:
    return [UserOut.model_validate(identity_service._to_out(u)) for u in identity_service.list_users(db, skip, limit)]


@identity_router.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: uuid.UUID, db: SessionDep, current_user: RequireRoot) -> UserOut:
    return UserOut.model_validate(identity_service._to_out(identity_service.get_user(db, user_id)))


@identity_router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: SessionDep,
    current_user: RequireRoot,
) -> UserOut:
    user = identity_service.update_user(db, current_user, user_id, data.model_dump(exclude_unset=True))
    return UserOut.model_validate(identity_service._to_out(user))


@identity_router.delete("/users/{user_id}", response_model=UserOut)
def deactivate_user(user_id: uuid.UUID, db: SessionDep, current_user: RequireRoot) -> UserOut:
    user = identity_service.deactivate_user(db, current_user, user_id)
    return UserOut.model_validate(identity_service._to_out(user))


@identity_router.get("/businesses", response_model=list[BusinessOut])
def list_businesses(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[BusinessOut]:
    return list(identity_service.list_businesses(db, skip, limit))


@identity_router.post("/businesses", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(data: BusinessCreate, db: SessionDep, current_user: RequireRoot) -> BusinessOut:
    business = identity_service.create_business(db, current_user, data.code, data.name)
    return BusinessOut.model_validate(business)


@identity_router.patch("/businesses/{business_id}", response_model=BusinessOut)
def patch_business(
    business_id: uuid.UUID,
    data: BusinessUpdate,
    db: SessionDep,
    current_user: RequireRoot,
) -> BusinessOut:
    business = identity_service.update_business(
        db, current_user, business_id, data.name, data.status
    )
    return BusinessOut.model_validate(business)


@identity_router.get("/businesses/{business_id}/accounts", response_model=list[BusinessAccountOut])
def list_business_accounts(
    business_id: uuid.UUID,
    db: SessionDep,
    current_user: CurrentUser,
) -> list[BusinessAccountOut]:
    return list(identity_service.list_business_accounts(db, business_id))


@identity_router.post(
    "/businesses/{business_id}/accounts",
    response_model=BusinessAccountOut,
    status_code=status.HTTP_201_CREATED,
)
def add_business_account(
    business_id: uuid.UUID,
    data: BusinessAccountCreate,
    db: SessionDep,
    current_user: RequireRoot,
) -> BusinessAccountOut:
    account = identity_service.create_business_account(
        db, current_user, business_id, data.person_id, data.role
    )
    person = identity_service.get_person(db, data.person_id)
    return BusinessAccountOut.model_validate(
        {
            "id": account.id,
            "business_id": account.business_id,
            "person_id": account.person_id,
            "role": account.role,
            "person_full_name": person.full_name,
        }
    )


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(identity_router)