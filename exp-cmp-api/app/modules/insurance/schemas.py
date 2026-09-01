import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.insurance.models import InsuranceClientStatus, InsuranceContractStatus


class InsuranceClientCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    phone: str | None = Field(None, max_length=30)
    client_number: str | None = Field(None, min_length=1, max_length=50)


class InsuranceClientOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    client_number: str
    full_name: str
    phone: str | None
    status: InsuranceClientStatus
    created_at: datetime


class InsuranceContractCreate(BaseModel):
    matricule: str = Field(..., min_length=1, max_length=50)
    contract_type: str = Field(..., min_length=1, max_length=100)
    premium: Decimal = Field(..., gt=0)
    start_date: date
    end_date: date | None = None


class InsuranceContractOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    matricule: str
    contract_type: str
    premium: Decimal
    start_date: date
    end_date: date | None
    status: InsuranceContractStatus
    remaining_amount: Decimal
    created_at: datetime


class InsurancePaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    paid_at: date | None = None
    account_id: uuid.UUID
    category_id: uuid.UUID


class InsurancePaymentOut(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    amount: Decimal
    paid_at: date
    transaction_id: uuid.UUID
    created_at: datetime