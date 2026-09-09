import uuid

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.modules.insurance import service as insurance_service
from app.modules.insurance.schemas import (
    InsuranceClientCreate,
    InsuranceClientOut,
    InsuranceContractCreate,
    InsuranceContractOut,
    InsuranceDueCreate,
    InsuranceDueOut,
    InsurancePaymentCreate,
    InsurancePaymentOut,
)

insurance_router = APIRouter(prefix="/insurance", tags=["assurance"])


@insurance_router.post("/clients", response_model=InsuranceClientOut, status_code=201)
def create_client(data: InsuranceClientCreate, db: SessionDep, current_user: CurrentUser) -> dict:
    client = insurance_service.create_client(
        db,
        current_user,
        full_name=data.full_name,
        phone=data.phone,
        client_number=data.client_number,
    )
    return insurance_service.to_client_out(db, client)


@insurance_router.get("/clients", response_model=list[InsuranceClientOut])
def list_clients(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    return [insurance_service.to_client_out(db, c) for c in insurance_service.list_clients(db, current_user, skip, limit)]


@insurance_router.get("/clients/{client_id}", response_model=InsuranceClientOut)
def read_client(client_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> dict:
    client = insurance_service.get_client(db, current_user, client_id)
    return insurance_service.to_client_out(db, client)


@insurance_router.post("/clients/{client_id}/contracts", response_model=InsuranceContractOut, status_code=201)
def create_contract(
    client_id: uuid.UUID,
    data: InsuranceContractCreate,
    db: SessionDep,
    current_user: CurrentUser,
) -> dict:
    contract = insurance_service.create_contract(
        db,
        current_user,
        client_id=client_id,
        matricule=data.matricule,
        contract_type=data.contract_type,
        premium=data.premium,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    return insurance_service.to_contract_out(db, contract)


@insurance_router.get("/clients/{client_id}/contracts", response_model=list[InsuranceContractOut])
def list_client_contracts(
    client_id: uuid.UUID,
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    contracts = insurance_service.list_contracts(db, current_user, client_id, skip, limit)
    return [insurance_service.to_contract_out(db, c) for c in contracts]


@insurance_router.get("/contracts", response_model=list[InsuranceContractOut])
def list_contracts(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    contracts = insurance_service.list_contracts(db, current_user, None, skip, limit)
    return [insurance_service.to_contract_out(db, c) for c in contracts]


@insurance_router.get("/contracts/{contract_id}", response_model=InsuranceContractOut)
def read_contract(contract_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> dict:
    contract = insurance_service.get_contract(db, current_user, contract_id)
    return insurance_service.to_contract_out(db, contract)


@insurance_router.post("/contracts/{contract_id}/cancel", response_model=InsuranceContractOut)
def cancel_contract(contract_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> dict:
    contract = insurance_service.cancel_contract(db, current_user, contract_id)
    return insurance_service.to_contract_out(db, contract)


@insurance_router.post("/contracts/{contract_id}/payments", response_model=InsurancePaymentOut, status_code=201)
def create_payment(
    contract_id: uuid.UUID,
    data: InsurancePaymentCreate,
    db: SessionDep,
    current_user: CurrentUser,
) -> dict:
    payment = insurance_service.create_payment(
        db,
        current_user,
        contract_id=contract_id,
        amount=data.amount,
        paid_at=data.paid_at,
        account_id=data.account_id,
        category_id=data.category_id,
    )
    return insurance_service.to_payment_out(payment)


@insurance_router.get("/contracts/{contract_id}/payments", response_model=list[InsurancePaymentOut])
def list_payments(
    contract_id: uuid.UUID,
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    payments = insurance_service.list_payments(db, current_user, contract_id, skip, limit)
    return [insurance_service.to_payment_out(p) for p in payments]


@insurance_router.post("/contracts/{contract_id}/dues", response_model=InsuranceDueOut, status_code=201)
def create_due(
    contract_id: uuid.UUID,
    data: InsuranceDueCreate,
    db: SessionDep,
    current_user: CurrentUser,
) -> dict:
    due = insurance_service.create_due(
        db,
        current_user,
        contract_id=contract_id,
        due_date=data.due_date,
        amount_due=data.amount_due,
    )
    return insurance_service.to_due_out(due)


@insurance_router.get("/contracts/{contract_id}/dues", response_model=list[InsuranceDueOut])
def list_dues(contract_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> list[dict]:
    dues = insurance_service.list_dues(db, current_user, contract_id)
    return [insurance_service.to_due_out(d) for d in dues]


api_router = APIRouter()
api_router.include_router(insurance_router)