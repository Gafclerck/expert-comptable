from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.modules.vtc import service as vtc_service
from app.modules.vtc.schemas import (
    AffectationCreate,
    AffectationEnd,
    AffectationOut,
    ChauffeurCreate,
    ChauffeurOut,
    ChauffeurUpdateStatus,
    DepenseCreate,
    DepenseOut,
    IndisponibiliteCreate,
    IndisponibiliteEnd,
    IndisponibiliteOut,
    ResumeFinancierOut,
    SoldesCaissesOut,
    StatistiquesVehiculeOut,
    StatutPaiementOut,
    VehiculeCreate,
    VehiculeOut,
    VehiculeUpdate,
    VehiculeUpdateStatus,
    VersementCreate,
    VersementOut,
)
from app.modules.vtc.models import (
    AffectationStatut,
    ChauffeurStatut,
    TypeDepenseVehicule,
    VehiculeStatut,
)

vtc_router = APIRouter(prefix="/vtc", tags=["vtc"])


# ---------------------------------------------------------------------------
# Chauffeur
# ---------------------------------------------------------------------------


@vtc_router.post("/chauffeurs", response_model=ChauffeurOut, status_code=201)
def create_chauffeur(data: ChauffeurCreate, db: SessionDep, current_user: CurrentUser) -> dict:
    ch = vtc_service.create_chauffeur(
        db,
        current_user,
        full_name=data.full_name,
        phone=data.phone,
        license_number=data.license_number,
    )
    return vtc_service.get_chauffeur(db, current_user, ch.id)


@vtc_router.get("/chauffeurs", response_model=list[ChauffeurOut])
def list_chauffeurs(
    db: SessionDep,
    current_user: CurrentUser,
    status: ChauffeurStatut | None = None,
) -> list[dict]:
    return vtc_service.list_chauffeurs(db, current_user, status=status)


@vtc_router.get("/chauffeurs/{chauffeur_id}", response_model=ChauffeurOut)
def get_chauffeur(chauffeur_id: str, db: SessionDep, current_user: CurrentUser) -> dict:
    import uuid
    return vtc_service.get_chauffeur(db, current_user, uuid.UUID(chauffeur_id))


@vtc_router.patch("/chauffeurs/{chauffeur_id}/status", response_model=ChauffeurOut)
def update_chauffeur_status(chauffeur_id: str, data: ChauffeurUpdateStatus, db: SessionDep, current_user: CurrentUser) -> dict:
    import uuid
    from app.modules.vtc.models import ChauffeurStatut
    vtc_service.update_chauffeur_status(
        db, current_user, uuid.UUID(chauffeur_id), status=ChauffeurStatut(data.status)
    )
    return vtc_service.get_chauffeur(db, current_user, uuid.UUID(chauffeur_id))


# ---------------------------------------------------------------------------
# Vehicule
# ---------------------------------------------------------------------------


@vtc_router.post("/vehicules", response_model=VehiculeOut, status_code=201)
def create_vehicule(data: VehiculeCreate, db: SessionDep, current_user: CurrentUser) -> VehiculeOut:
    v = vtc_service.create_vehicule(
        db,
        current_user,
        make=data.make,
        model=data.model,
        year=data.year,
        registration=data.registration,
        acquisition_cost=data.acquisition_cost,
    )
    return v


@vtc_router.get("/vehicules", response_model=list[VehiculeOut])
def list_vehicules(
    db: SessionDep,
    current_user: CurrentUser,
    status: VehiculeStatut | None = None,
) -> list[VehiculeOut]:
    return vtc_service.list_vehicules(db, current_user, status=status)


@vtc_router.get("/vehicules/{vehicule_id}", response_model=VehiculeOut)
def get_vehicule(vehicule_id: str, db: SessionDep, current_user: CurrentUser) -> VehiculeOut:
    import uuid
    return vtc_service.get_vehicule(db, current_user, uuid.UUID(vehicule_id))


@vtc_router.patch("/vehicules/{vehicule_id}", response_model=VehiculeOut)
def update_vehicule(vehicule_id: str, data: VehiculeUpdate, db: SessionDep, current_user: CurrentUser) -> VehiculeOut:
    import uuid
    return vtc_service.update_vehicule(
        db,
        current_user,
        uuid.UUID(vehicule_id),
        make=data.make,
        model=data.model,
        year=data.year,
        registration=data.registration,
        acquisition_cost=data.acquisition_cost,
    )


@vtc_router.patch("/vehicules/{vehicule_id}/status", response_model=VehiculeOut)
def update_vehicule_status(vehicule_id: str, data: VehiculeUpdateStatus, db: SessionDep, current_user: CurrentUser) -> VehiculeOut:
    import uuid
    from app.modules.vtc.models import VehiculeStatut
    vtc_service.update_vehicule_status(
        db, current_user, uuid.UUID(vehicule_id), status=VehiculeStatut(data.status)
    )
    return vtc_service.get_vehicule(db, current_user, uuid.UUID(vehicule_id))


# ---------------------------------------------------------------------------
# Affectation
# ---------------------------------------------------------------------------


@vtc_router.post("/affectations", response_model=AffectationOut, status_code=201)
def create_affectation(data: AffectationCreate, db: SessionDep, current_user: CurrentUser) -> dict:
    af = vtc_service.create_affectation(
        db,
        current_user,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        start_date=data.start_date,
        end_date=data.end_date,
        expected_amount=data.expected_amount,
        terms=data.terms,
    )
    return vtc_service.to_affectation_out(db, af)


@vtc_router.get("/affectations", response_model=list[AffectationOut])
def list_affectations(
    db: SessionDep,
    current_user: CurrentUser,
    driver_id: str | None = None,
    vehicle_id: str | None = None,
    status: AffectationStatut | None = None,
) -> list[dict]:
    import uuid
    return vtc_service.list_affectations(
        db,
        current_user,
        driver_id=uuid.UUID(driver_id) if driver_id else None,
        vehicle_id=uuid.UUID(vehicle_id) if vehicle_id else None,
        status=status,
    )


@vtc_router.get("/affectations/{affectation_id}", response_model=AffectationOut)
def get_affectation(affectation_id: str, db: SessionDep, current_user: CurrentUser) -> dict:
    import uuid
    return vtc_service.get_affectation(db, current_user, uuid.UUID(affectation_id))


@vtc_router.patch("/affectations/{affectation_id}/end", response_model=AffectationOut)
def end_affectation(affectation_id: str, data: AffectationEnd, db: SessionDep, current_user: CurrentUser) -> dict:
    import uuid
    vtc_service.end_affectation(db, current_user, uuid.UUID(affectation_id), end_date=data.end_date)
    return vtc_service.get_affectation(db, current_user, uuid.UUID(affectation_id))


# ---------------------------------------------------------------------------
# Versement chauffeur
# ---------------------------------------------------------------------------


@vtc_router.post("/versements", response_model=VersementOut, status_code=201)
def create_versement(data: VersementCreate, db: SessionDep, current_user: CurrentUser) -> VersementOut:
    return vtc_service.create_versement(
        db,
        current_user,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
        amount=data.amount,
        account_id=data.account_id,
        category_id=data.category_id,
        occurred_at=data.occurred_at,
    )


@vtc_router.get("/versements", response_model=list[VersementOut])
def list_versements(
    db: SessionDep,
    current_user: CurrentUser,
    driver_id: str | None = None,
    vehicle_id: str | None = None,
) -> list[VersementOut]:
    import uuid
    return vtc_service.list_versements(
        db,
        current_user,
        driver_id=uuid.UUID(driver_id) if driver_id else None,
        vehicle_id=uuid.UUID(vehicle_id) if vehicle_id else None,
    )


# ---------------------------------------------------------------------------
# Depense vehicule
# ---------------------------------------------------------------------------


@vtc_router.post("/depenses", response_model=DepenseOut, status_code=201)
def create_depense(data: DepenseCreate, db: SessionDep, current_user: CurrentUser) -> DepenseOut:
    return vtc_service.create_depense(
        db,
        current_user,
        vehicle_id=data.vehicle_id,
        expense_type=TypeDepenseVehicule(data.expense_type),
        amount=data.amount,
        quantity=data.quantity,
        unit=data.unit,
        description=data.description,
        account_id=data.account_id,
        category_id=data.category_id,
        occurred_at=data.occurred_at,
    )


@vtc_router.get("/depenses", response_model=list[DepenseOut])
def list_depenses(
    db: SessionDep,
    current_user: CurrentUser,
    vehicle_id: str | None = None,
    expense_type: TypeDepenseVehicule | None = None,
) -> list[DepenseOut]:
    import uuid
    return vtc_service.list_depenses(
        db,
        current_user,
        vehicle_id=uuid.UUID(vehicle_id) if vehicle_id else None,
        expense_type=expense_type,
    )


# ---------------------------------------------------------------------------
# Indisponibilite vehicule
# ---------------------------------------------------------------------------


@vtc_router.post("/indisponibilites", response_model=IndisponibiliteOut, status_code=201)
def create_indisponibilite(data: IndisponibiliteCreate, db: SessionDep, current_user: CurrentUser) -> IndisponibiliteOut:
    return vtc_service.create_indisponibilite(
        db,
        current_user,
        vehicle_id=data.vehicle_id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
    )


@vtc_router.get("/indisponibilites", response_model=list[IndisponibiliteOut])
def list_indisponibilites(
    db: SessionDep,
    current_user: CurrentUser,
    vehicle_id: str | None = None,
) -> list[IndisponibiliteOut]:
    import uuid
    return vtc_service.list_indisponibilites(
        db,
        current_user,
        vehicle_id=uuid.UUID(vehicle_id) if vehicle_id else None,
    )


@vtc_router.patch("/indisponibilites/{indispo_id}/close", response_model=IndisponibiliteOut)
def close_indisponibilite(indispo_id: str, data: IndisponibiliteEnd, db: SessionDep, current_user: CurrentUser) -> IndisponibiliteOut:
    import uuid
    return vtc_service.close_indisponibilite(
        db, current_user, uuid.UUID(indispo_id), end_date=data.end_date
    )


# ---------------------------------------------------------------------------
# Indicateurs financiers
# ---------------------------------------------------------------------------


@vtc_router.get("/paiements/{driver_id}", response_model=StatutPaiementOut)
def statut_paiement_chauffeur(driver_id: str, db: SessionDep, current_user: CurrentUser) -> dict:
    import uuid
    return vtc_service.statut_paiement_chauffeur(db, current_user, uuid.UUID(driver_id))


@vtc_router.get("/vehicules/{vehicule_id}/stats", response_model=StatistiquesVehiculeOut)
def statistiques_vehicule(vehicule_id: str, db: SessionDep, current_user: CurrentUser) -> dict:
    import uuid
    return vtc_service.statistiques_vehicule(db, current_user, uuid.UUID(vehicule_id))


@vtc_router.get("/resume-financier", response_model=ResumeFinancierOut)
def resume_financier(
    db: SessionDep,
    current_user: CurrentUser,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    from datetime import date as _date
    start_d = _date.fromisoformat(start) if start else None
    end_d = _date.fromisoformat(end) if end else None
    return vtc_service.resume_financier(db, current_user, start=start_d, end=end_d)


@vtc_router.get("/soldes-caisses", response_model=SoldesCaissesOut)
def soldes_caisses(db: SessionDep, current_user: CurrentUser) -> dict:
    return vtc_service.soldes_caisses(db, current_user)


# ---------------------------------------------------------------------------
# api_router (monte dans main.py)
# ---------------------------------------------------------------------------

api_router = APIRouter()
api_router.include_router(vtc_router)
