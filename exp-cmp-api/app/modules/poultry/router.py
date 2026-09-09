from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.modules.poultry import service as poultry_service
from app.modules.poultry.schemas import (
    ApprovisionnementCreate,
    ApprovisionnementOut,
    LotOut,
    StockOut,
    VenteCreate,
    VenteOut,
)

poultry_router = APIRouter(prefix="/poultry", tags=["poulailler"])


@poultry_router.post("/purchases", response_model=ApprovisionnementOut, status_code=201)
def create_purchase(data: ApprovisionnementCreate, db: SessionDep, current_user: CurrentUser) -> dict:
    appro = poultry_service.create_approvisionnement(
        db,
        current_user,
        quantity=data.quantity,
        unit_price=data.unit_price,
        note=data.note,
        account_id=data.account_id,
        category_id=data.category_id,
        occurred_at=data.occurred_at,
    )
    return poultry_service.to_appro_out(appro)


@poultry_router.get("/purchases", response_model=list[ApprovisionnementOut])
def list_purchases(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    rows = poultry_service.list_approvisionnements(db, current_user, skip, limit)
    return [poultry_service.to_appro_out(a) for a in rows]


@poultry_router.post("/sales", response_model=VenteOut, status_code=201)
def create_sale(data: VenteCreate, db: SessionDep, current_user: CurrentUser) -> dict:
    sale = poultry_service.create_vente(
        db,
        current_user,
        quantity=data.quantity,
        unit_price=data.unit_price,
        account_id=data.account_id,
        category_id=data.category_id,
        occurred_at=data.occurred_at,
    )
    return poultry_service.to_vente_out(sale)


@poultry_router.get("/sales", response_model=list[VenteOut])
def list_sales(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    rows = poultry_service.list_ventes(db, current_user, skip, limit)
    return [poultry_service.to_vente_out(v) for v in rows]


@poultry_router.get("/lots", response_model=list[LotOut])
def list_lots(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    rows = poultry_service.list_lots(db, current_user, skip, limit)
    return [poultry_service.to_lot_out(lot) for lot in rows]


@poultry_router.get("/stock", response_model=StockOut)
def read_stock(db: SessionDep, current_user: CurrentUser) -> dict:
    return {"total_quantity": poultry_service.get_stock_total(db, current_user)}


api_router = APIRouter()
api_router.include_router(poultry_router)
