import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ApprovisionnementCreate(BaseModel):
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    note: str | None = Field(None, max_length=300)
    account_id: uuid.UUID
    category_id: uuid.UUID
    occurred_at: datetime | None = None


class ApprovisionnementOut(BaseModel):
    id: uuid.UUID
    lot_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    note: str | None
    transaction_id: uuid.UUID
    created_at: datetime


class VenteCreate(BaseModel):
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    account_id: uuid.UUID
    category_id: uuid.UUID
    occurred_at: datetime | None = None


class VenteOut(BaseModel):
    id: uuid.UUID
    quantity: int
    unit_price: Decimal
    transaction_id: uuid.UUID
    created_at: datetime


class LotOut(BaseModel):
    id: uuid.UUID
    initial_quantity: int
    remaining_quantity: int
    unit_purchase_price: Decimal
    created_at: datetime


class StockOut(BaseModel):
    total_quantity: int
