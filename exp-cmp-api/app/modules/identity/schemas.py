import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.modules.identity.models import BusinessAccountRole, BusinessStatus, PersonStatus, UserStatus


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    ancien_mot_de_passe: str = Field(..., min_length=1, max_length=200)
    nouveau_mot_de_passe: str = Field(..., min_length=8, max_length=200)


class PersonCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)


class PersonUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)
    status: PersonStatus | None = None


class PersonOut(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None
    status: PersonStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=200)
    full_name: str = Field(..., min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)
    is_root: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=200)
    status: UserStatus | None = None
    is_root: bool | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    status: UserStatus
    person_id: uuid.UUID | None
    person_full_name: str | None
    roles: list[str]
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class BusinessCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)


class BusinessUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    status: BusinessStatus | None = None


class BusinessOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    status: BusinessStatus

    model_config = {"from_attributes": True}


class BusinessAccountCreate(BaseModel):
    person_id: uuid.UUID
    role: BusinessAccountRole


class BusinessAccountOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    person_id: uuid.UUID
    role: BusinessAccountRole
    person_full_name: str | None

    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    roles: list[str]

    model_config = {"from_attributes": True}