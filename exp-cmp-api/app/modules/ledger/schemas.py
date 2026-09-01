import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.ledger.models import (
    AccountType,
    CategoryType,
    LineDirection,
    TransactionStatus,
    TransactionType,
    TransferStatus,
)


class AccountCreate(BaseModel):
    business_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType = AccountType.CASH
    currency: str = Field("FCFA", min_length=1, max_length=5)
    opening_balance: Decimal = Field(Decimal("0"), ge=0)


class AccountOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    type: AccountType
    currency: str
    opening_balance: Decimal
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountBalanceOut(BaseModel):
    account_id: uuid.UUID
    name: str
    currency: str
    opening_balance: Decimal
    inflows: Decimal
    outflows: Decimal
    balance: Decimal


class CategoryCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    type: CategoryType


class CategoryOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    type: CategoryType

    model_config = {"from_attributes": True}


class TransactionLineIn(BaseModel):
    category_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    direction: LineDirection
    description: str | None = Field(None, max_length=300)


class TransactionLineOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    amount: Decimal
    direction: LineDirection
    description: str | None

    model_config = {"from_attributes": True}


class TransactionAllocationIn(BaseModel):
    business_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)


class TransactionAllocationOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    amount: Decimal
    percentage: Decimal

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    business_id: uuid.UUID
    account_id: uuid.UUID
    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    description: str | None = Field(None, max_length=300)
    occurred_at: datetime | None = None
    lines: list[TransactionLineIn] = Field(..., min_length=1)
    allocations: list[TransactionAllocationIn] = Field(default_factory=list)


class TransactionOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    account_id: uuid.UUID
    type: TransactionType
    amount: Decimal
    description: str | None
    occurred_at: datetime
    status: TransactionStatus
    created_by: uuid.UUID | None
    immutable: bool
    created_at: datetime
    lines: list[TransactionLineOut] = Field(default_factory=list)
    allocations: list[TransactionAllocationOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TransferCreate(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    occurred_at: datetime | None = None
    reference: str | None = Field(None, max_length=200)


class TransferOut(BaseModel):
    id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal
    occurred_at: datetime
    status: TransferStatus
    reference: str | None
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}