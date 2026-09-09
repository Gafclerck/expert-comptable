import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.modules.shared.enums import sa_enum
from app.modules.shared.models import UUIDPkMixin


class AccountType(str, Enum):
    CASH = "cash"
    BANK = "bank"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class CategoryType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionType(str, Enum):
    REVENUE = "revenue"
    EXPENSE = "expense"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    POSTED = "posted"


class LineDirection(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class TransferStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"


class Account(UUIDPkMixin, Base):
    __tablename__ = "accounts"

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("businesses.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        sa_enum(AccountType, length=20), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(5), nullable=False, default="FCFA")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Category(UUIDPkMixin, Base):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[CategoryType] = mapped_column(
        sa_enum(CategoryType, length=20), nullable=False
    )


class Transaction(UUIDPkMixin, Base):
    __tablename__ = "transactions"

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("businesses.id"), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(
        sa_enum(TransactionType, length=20), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[TransactionStatus] = mapped_column(
        sa_enum(TransactionStatus, length=20), nullable=False, default=TransactionStatus.POSTED
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    lines: Mapped[list["TransactionLine"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    allocations: Mapped[list["TransactionAllocation"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )


class TransactionLine(UUIDPkMixin, Base):
    __tablename__ = "transaction_lines"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("categories.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    direction: Mapped[LineDirection] = mapped_column(
        sa_enum(LineDirection, length=20), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="lines")


class TransactionAllocation(UUIDPkMixin, Base):
    __tablename__ = "transaction_allocations"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("businesses.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)

    transaction: Mapped["Transaction"] = relationship(back_populates="allocations")


class Transfer(UUIDPkMixin, Base):
    __tablename__ = "transfers"

    source_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id"), nullable=False, index=True
    )
    destination_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[TransferStatus] = mapped_column(
        sa_enum(TransferStatus, length=20), nullable=False, default=TransferStatus.POSTED
    )
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
