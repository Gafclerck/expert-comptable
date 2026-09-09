import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.shared.enums import sa_enum
from app.modules.shared.models import UUIDPkMixin


class InsuranceClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class InsuranceContractStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InsuranceDueStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class InsuranceClient(UUIDPkMixin, Base):
    __tablename__ = "insurance_clients"

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("persons.id"), nullable=False, unique=True, index=True
    )
    client_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[InsuranceClientStatus] = mapped_column(
        sa_enum(InsuranceClientStatus, length=20), nullable=False, default=InsuranceClientStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InsuranceContract(UUIDPkMixin, Base):
    __tablename__ = "insurance_contracts"

    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("insurance_clients.id"), nullable=False, index=True
    )
    matricule: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    contract_type: Mapped[str] = mapped_column(String(100), nullable=False)
    premium: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[InsuranceContractStatus] = mapped_column(
        sa_enum(InsuranceContractStatus, length=20), nullable=False, default=InsuranceContractStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InsurancePayment(UUIDPkMixin, Base):
    __tablename__ = "insurance_payments"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("insurance_contracts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_at: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InsuranceDue(UUIDPkMixin, Base):
    """Echeance programmee pour un contrat. Statut derive (voir refresh_due_statuses),
    jamais mis a jour a la main : cascade chronologique sur le total deja paye du contrat.
    """

    __tablename__ = "insurance_dues"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("insurance_contracts.id"), nullable=False, index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[InsuranceDueStatus] = mapped_column(
        sa_enum(InsuranceDueStatus, length=20), nullable=False, default=InsuranceDueStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _date_to_datetime(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)