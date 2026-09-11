import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.shared.enums import sa_enum
from app.modules.shared.models import UUIDPkMixin


class ChauffeurStatut(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class VehiculeStatut(str, Enum):
    ACTIVE = "active"
    OUT_OF_SERVICE = "out_of_service"
    SOLD = "sold"


class AffectationStatut(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"


class TypeDepenseVehicule(str, Enum):
    FUEL = "fuel"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    TIRES = "tires"
    INSURANCE = "insurance"
    REGISTRATION = "registration"
    MISC = "misc"


class Chauffeur(UUIDPkMixin, Base):
    """Conducteur rattache a une Person (sans compte)."""

    __tablename__ = "drivers"

    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("persons.id"), nullable=False, unique=True, index=True
    )
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[ChauffeurStatut] = mapped_column(
        sa_enum(ChauffeurStatut, length=20), nullable=False, default=ChauffeurStatut.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Vehicule(UUIDPkMixin, Base):
    """Vehicule du parc VTC."""

    __tablename__ = "vehicles"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id"), nullable=False, index=True
    )
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    acquisition_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    acquisition_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=True
    )
    status: Mapped[VehiculeStatut] = mapped_column(
        sa_enum(VehiculeStatut, length=20), nullable=False, default=VehiculeStatut.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Affectation(UUIDPkMixin, Base):
    """Association historisee chauffeur <-> vehicule, portant le montant attendu
    et les conditions de location.
    """

    __tablename__ = "vehicle_assignments"

    driver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("drivers.id"), nullable=False, index=True
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    terms: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[AffectationStatut] = mapped_column(
        sa_enum(AffectationStatut, length=20), nullable=False, default=AffectationStatut.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VersementChauffeur(UUIDPkMixin, Base):
    """Versement / redevance d'un chauffeur rattache a une affectation.
    driver_id et vehicle_id sont des copies figees pour robustesse historique.
    """

    __tablename__ = "driver_remittances"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicle_assignments.id"), nullable=False, index=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("drivers.id"), nullable=False, index=True
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=False, unique=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DepenseVehicule(UUIDPkMixin, Base):
    """Depense liee a un vehicule, unifiee (carburant, entretien, reparations, etc.)."""

    __tablename__ = "vehicle_expenses"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    expense_type: Mapped[TypeDepenseVehicule] = mapped_column(
        sa_enum(TypeDepenseVehicule, length=20), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=False, unique=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IndisponibiliteVehicule(UUIDPkMixin, Base):
    """Periode d'indisponibilite (panne, immobilisation) d'un vehicule.
    Aucun versement ne doit etre enregistre pendant cette periode.
    """

    __tablename__ = "vehicle_downtimes"

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
