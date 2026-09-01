import uuid

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, RequireRoot, SessionDep
from app.modules.identity.models import User
from app.modules.ledger import service as ledger_service
from app.modules.ledger.schemas import (
    AccountBalanceOut,
    AccountCreate,
    AccountOut,
    CategoryCreate,
    CategoryOut,
    TransactionAllocationOut,
    TransactionCreate,
    TransactionLineOut,
    TransactionOut,
    TransferCreate,
    TransferOut,
)

ledger_router = APIRouter(prefix="/ledger", tags=["ledger"])

# Peuplements Pydantic pour les listes imbriquees des transactions.
LineSidecar = TransactionLineOut
AllocationSidecar = TransactionAllocationOut


def _txn_to_out(txn) -> dict:
    return {
        "id": txn.id,
        "business_id": txn.business_id,
        "account_id": txn.account_id,
        "type": txn.type,
        "amount": txn.amount,
        "description": txn.description,
        "occurred_at": txn.occurred_at,
        "status": txn.status,
        "created_by": txn.created_by,
        "immutable": txn.immutable,
        "created_at": txn.created_at,
        "lines": [TransactionLineOut.model_validate(l) for l in txn.lines],
        "allocations": [TransactionAllocationOut.model_validate(a) for a in txn.allocations],
    }


@ledger_router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    db: SessionDep,
    current_user: CurrentUser,
    business_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[AccountOut]:
    return list(ledger_service.list_accounts(db, current_user, business_id, skip, limit))


@ledger_router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(data: AccountCreate, db: SessionDep, current_user: RequireRoot) -> AccountOut:
    account = ledger_service.create_account(
        db,
        current_user,
        data.business_id,
        data.name,
        data.type,
        data.currency,
        data.opening_balance,
    )
    return AccountOut.model_validate(account)


@ledger_router.get("/accounts/{account_id}", response_model=AccountOut)
def read_account(account_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> AccountOut:
    return AccountOut.model_validate(ledger_service.get_account(db, account_id, current_user))


@ledger_router.get("/accounts/{account_id}/balance", response_model=AccountBalanceOut)
def account_balance(account_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> AccountBalanceOut:
    account = ledger_service.get_account(db, account_id, current_user)
    return AccountBalanceOut.model_validate(ledger_service.compute_balance(db, account))


@ledger_router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: SessionDep, current_user: CurrentUser) -> list[CategoryOut]:
    return list(ledger_service.list_categories(db))


@ledger_router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: SessionDep, current_user: RequireRoot) -> CategoryOut:
    category = ledger_service.create_category(db, current_user, data.code, data.name, data.type)
    return CategoryOut.model_validate(category)


@ledger_router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(data: TransactionCreate, db: SessionDep, current_user: CurrentUser) -> dict:
    txn = ledger_service.create_transaction(
        db,
        current_user,
        business_id=data.business_id,
        account_id=data.account_id,
        txn_type=data.type,
        amount=data.amount,
        description=data.description,
        occurred_at=data.occurred_at,
        lines=[l.model_dump() for l in data.lines],
        allocations=[a.model_dump() for a in data.allocations],
    )
    return _txn_to_out(txn)


@ledger_router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    db: SessionDep,
    current_user: CurrentUser,
    business_id: uuid.UUID | None = Query(None),
    account_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    return [_txn_to_out(t) for t in ledger_service.list_transactions(db, current_user, business_id, account_id, skip, limit)]


@ledger_router.get("/transactions/{transaction_id}", response_model=TransactionOut)
def read_transaction(transaction_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> dict:
    return _txn_to_out(ledger_service.get_transaction(db, transaction_id, current_user))


@ledger_router.post("/transfers", response_model=TransferOut, status_code=201)
def create_transfer(data: TransferCreate, db: SessionDep, current_user: CurrentUser) -> TransferOut:
    transfer = ledger_service.create_transfer(
        db,
        current_user,
        source_account_id=data.source_account_id,
        destination_account_id=data.destination_account_id,
        amount=data.amount,
        occurred_at=data.occurred_at,
        reference=data.reference,
    )
    return TransferOut.model_validate(transfer)


@ledger_router.get("/transfers", response_model=list[TransferOut])
def list_transfers(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[TransferOut]:
    return list(ledger_service.list_transfers(db, current_user, skip, limit))


@ledger_router.get("/transfers/{transfer_id}", response_model=TransferOut)
def read_transfer(transfer_id: uuid.UUID, db: SessionDep, current_user: CurrentUser) -> TransferOut:
    return TransferOut.model_validate(ledger_service.get_transfer(db, transfer_id, current_user))


api_router = APIRouter()
api_router.include_router(ledger_router)