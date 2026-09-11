import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums / litteraux
# ---------------------------------------------------------------------------

ChauffeurStatusLiteral = Literal["active", "inactive"]
VehiculeStatusLiteral = Literal["active", "out_of_service", "sold"]
AffectationStatusLiteral = Literal["active", "ended"]
TypeDepenseLiteral = Literal["fuel", "maintenance", "repair", "tires", "insurance", "registration", "misc"]


# ---------------------------------------------------------------------------
# Chauffeur
# ---------------------------------------------------------------------------


class ChauffeurCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=30)
    license_number: str | None = Field(None, max_length=50)


class ChauffeurOut(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID
    full_name: str
    phone: str | None
    license_number: str | None
    status: ChauffeurStatusLiteral
    created_at: datetime


class ChauffeurUpdateStatus(BaseModel):
    status: ChauffeurStatusLiteral


# ---------------------------------------------------------------------------
# Vehicule
# ---------------------------------------------------------------------------


class VehiculeCreate(BaseModel):
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int | None = None
    registration: str = Field(..., min_length=1, max_length=50)
    acquisition_cost: Decimal = Field(Decimal("0"), ge=0)


class VehiculeOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    make: str
    model: str
    year: int | None
    registration: str
    acquisition_cost: Decimal
    status: VehiculeStatusLiteral
    created_at: datetime


class VehiculeUpdate(BaseModel):
    make: str | None = Field(None, min_length=1, max_length=100)
    model: str | None = Field(None, min_length=1, max_length=100)
    year: int | None = None
    registration: str | None = Field(None, min_length=1, max_length=50)
    acquisition_cost: Decimal | None = None


class VehiculeUpdateStatus(BaseModel):
    status: VehiculeStatusLiteral


# ---------------------------------------------------------------------------
# Affectation
# ---------------------------------------------------------------------------


class AffectationCreate(BaseModel):
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    start_date: date
    end_date: date | None = None
    expected_amount: Decimal = Field(..., gt=0)
    terms: str | None = Field(None, max_length=300)


class AffectationOut(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    driver_name: str | None
    vehicle_registration: str | None
    start_date: date
    end_date: date | None
    expected_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    terms: str | None
    status: AffectationStatusLiteral
    created_at: datetime


class AffectationEnd(BaseModel):
    end_date: date | None = None


# ---------------------------------------------------------------------------
# Versement chauffeur
# ---------------------------------------------------------------------------


class VersementCreate(BaseModel):
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    account_id: uuid.UUID
    category_id: uuid.UUID
    occurred_at: datetime | None = None


class VersementOut(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    driver_id: uuid.UUID
    vehicle_id: uuid.UUID
    amount: Decimal
    paid_at: datetime
    transaction_id: uuid.UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Depense vehicule
# ---------------------------------------------------------------------------


class DepenseCreate(BaseModel):
    vehicle_id: uuid.UUID
    expense_type: TypeDepenseLiteral
    amount: Decimal = Field(..., gt=0)
    quantity: Decimal | None = None
    unit: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=300)
    account_id: uuid.UUID
    category_id: uuid.UUID
    occurred_at: datetime | None = None


class DepenseOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    expense_type: TypeDepenseLiteral
    amount: Decimal
    quantity: Decimal | None
    unit: str | None
    description: str | None
    occurred_at: datetime
    transaction_id: uuid.UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Indisponibilite vehicule
# ---------------------------------------------------------------------------


class IndisponibiliteCreate(BaseModel):
    vehicle_id: uuid.UUID
    start_date: date
    end_date: date | None = None
    reason: str | None = Field(None, max_length=300)


class IndisponibiliteOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    start_date: date
    end_date: date | None
    reason: str | None
    created_at: datetime


class IndisponibiliteEnd(BaseModel):
    end_date: date | None = None


# ---------------------------------------------------------------------------
# Indicateurs
# ---------------------------------------------------------------------------

class StatutPaiementOut(BaseModel):
    driver_id: uuid.UUID
    total_expected: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    assignments: list[dict]


class StatistiquesVehiculeOut(BaseModel):
    vehicle_id: uuid.UUID
    make: str
    model: str
    registration: str
    versements: Decimal
    depenses: Decimal
    rentabilite: Decimal
    depenses_par_type: dict[str, Decimal]
    cout_acquisition: Decimal


class TotalsOut(BaseModel):
    versements: Decimal
    depenses: Decimal
    net: Decimal


class PerVehicleOut(BaseModel):
    vehicle_id: uuid.UUID
    make: str
    model: str
    registration: str
    versements: Decimal
    depenses: Decimal
    net: Decimal


class CountsOut(BaseModel):
    vehicules_actifs: int
    chauffeurs_actifs: int
    affectations_actives: int


class ResumeFinancierOut(BaseModel):
    business_id: uuid.UUID
    totals: TotalsOut
    per_vehicle: list[PerVehicleOut]
    counts: CountsOut


class AccountBalanceOut(BaseModel):
    account_id: uuid.UUID
    name: str
    currency: str
    opening_balance: Decimal
    inflows: Decimal
    outflows: Decimal
    balance: Decimal


class SoldesCaissesOut(BaseModel):
    business_id: uuid.UUID
    accounts: list[AccountBalanceOut]
    total: Decimal
