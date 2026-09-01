import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.events import publish
from app.modules.identity.service import (
    add_business_customer,
    create_person,
    get_business_by_code,
    get_business_ids_for_user,
    get_person_summary,
)
from app.modules.insurance.models import (
    InsuranceClient,
    InsuranceClientStatus,
    InsuranceContract,
    InsuranceContractStatus,
    InsurancePayment,
    _date_to_datetime,
)
from app.modules.ledger.service import record_revenue

ASSURANCE_BUSINESS_CODE = "assurance"


def _assurance_business(db: Session):
    return get_business_by_code(db, ASSURANCE_BUSINESS_CODE)


def _ensure_insurance_access(db: Session, user, business) -> None:
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None and business.id not in allowed:
        raise HTTPException(status_code=403, detail="Acces refuse a l'activite assurance")


def create_client(
    db: Session,
    actor,
    *,
    full_name: str,
    phone: str | None,
    client_number: str | None,
) -> InsuranceClient:
    business = _assurance_business(db)
    _ensure_insurance_access(db, actor, business)
    if not client_number:
        count = db.query(func.count(InsuranceClient.id)).scalar() or 0
        client_number = f"CLI-{count + 1:05d}"
    if db.query(InsuranceClient).filter(InsuranceClient.client_number == client_number).first():
        raise HTTPException(status_code=400, detail="Ce numero de client existe deja")

    person = create_person(db, actor, full_name=full_name, phone=phone)
    add_business_customer(db, actor, business.id, person.id)

    client = InsuranceClient(person_id=person.id, client_number=client_number)
    db.add(client)
    db.commit()
    db.refresh(client)
    publish(
        "insurance.client.created",
        actor_id=str(actor.id),
        entity_id=str(client.id),
        new_values={"client_number": client.client_number, "person_id": str(client.person_id)},
    )
    return client


def get_client(db: Session, user, client_id: uuid.UUID) -> InsuranceClient:
    business = _assurance_business(db)
    _ensure_insurance_access(db, user, business)
    client = db.get(InsuranceClient, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return client


def list_clients(db: Session, user, skip: int = 0, limit: int = 100) -> list[InsuranceClient]:
    business = _assurance_business(db)
    _ensure_insurance_access(db, user, business)
    return (
        db.query(InsuranceClient)
        .order_by(InsuranceClient.created_at)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_contract(
    db: Session,
    actor,
    *,
    client_id: uuid.UUID,
    matricule: str,
    contract_type: str,
    premium: Decimal,
    start_date: date,
    end_date: date | None,
) -> InsuranceContract:
    client = get_client(db, actor, client_id)
    if client.status != InsuranceClientStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Client inactif")
    if end_date is not None and end_date < start_date:
        raise HTTPException(status_code=400, detail="La date de fin precede la date de debut")
    active = (
        db.query(InsuranceContract)
        .filter(
            InsuranceContract.matricule == matricule,
            InsuranceContract.status == InsuranceContractStatus.ACTIVE,
        )
        .first()
    )
    if active:
        raise HTTPException(status_code=400, detail="Cette matricule est deja active sur un autre contrat")

    contract = InsuranceContract(
        client_id=client.id,
        matricule=matricule,
        contract_type=contract_type,
        premium=premium,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    publish(
        "insurance.contract.created",
        actor_id=str(actor.id),
        entity_id=str(contract.id),
        new_values={
            "client_id": str(contract.client_id),
            "matricule": contract.matricule,
            "premium": str(contract.premium),
            "status": contract.status.value,
        },
    )
    return contract


def get_contract(db: Session, user, contract_id: uuid.UUID) -> InsuranceContract:
    business = _assurance_business(db)
    _ensure_insurance_access(db, user, business)
    contract = db.get(InsuranceContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    return contract


def list_contracts(
    db: Session,
    user,
    client_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[InsuranceContract]:
    business = _assurance_business(db)
    _ensure_insurance_access(db, user, business)
    query = db.query(InsuranceContract)
    if client_id is not None:
        query = query.filter(InsuranceContract.client_id == client_id)
    return query.order_by(InsuranceContract.created_at).offset(skip).limit(limit).all()


def _paid_total(db: Session, contract: InsuranceContract) -> Decimal:
    return (
        db.query(func.coalesce(func.sum(InsurancePayment.amount), Decimal("0")))
        .filter(InsurancePayment.contract_id == contract.id)
        .scalar()
        or Decimal("0")
    )


def remaining_amount(db: Session, contract: InsuranceContract) -> Decimal:
    return contract.premium - _paid_total(db, contract)


def create_payment(
    db: Session,
    actor,
    *,
    contract_id: uuid.UUID,
    amount: Decimal,
    paid_at: date | None,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
) -> InsurancePayment:
    contract = get_contract(db, actor, contract_id)
    if contract.status != InsuranceContractStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Contrat inactif")
    business = _assurance_business(db)
    remaining = remaining_amount(db, contract)
    if amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Le montant depasse le reste a payer ({remaining})",
        )

    transaction = record_revenue(
        db,
        actor,
        business_id=business.id,
        account_id=account_id,
        amount=amount,
        description=f"Prime assurance - contrat {contract.matricule}",
        occurred_at=_date_to_datetime(paid_at) if paid_at else None,
        category_id=category_id,
    )
    payment = InsurancePayment(
        contract_id=contract.id,
        amount=amount,
        paid_at=paid_at or date.today(),
        transaction_id=transaction.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    publish(
        "insurance.payment.created",
        actor_id=str(actor.id),
        entity_id=str(payment.id),
        new_values={
            "contract_id": str(payment.contract_id),
            "amount": str(payment.amount),
            "transaction_id": str(payment.transaction_id),
        },
    )
    return payment


def list_payments(db: Session, user, contract_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[InsurancePayment]:
    contract = get_contract(db, user, contract_id)
    return (
        db.query(InsurancePayment)
        .filter(InsurancePayment.contract_id == contract.id)
        .order_by(InsurancePayment.paid_at)
        .offset(skip)
        .limit(limit)
        .all()
    )


def to_client_out(db: Session, client: InsuranceClient) -> dict:
    person = get_person_summary(db, client.person_id)
    return {
        "id": client.id,
        "person_id": client.person_id,
        "client_number": client.client_number,
        "full_name": person.full_name,
        "phone": person.phone,
        "status": client.status,
        "created_at": client.created_at,
    }


def to_contract_out(db: Session, contract: InsuranceContract) -> dict:
    return {
        "id": contract.id,
        "client_id": contract.client_id,
        "matricule": contract.matricule,
        "contract_type": contract.contract_type,
        "premium": contract.premium,
        "start_date": contract.start_date,
        "end_date": contract.end_date,
        "status": contract.status,
        "remaining_amount": remaining_amount(db, contract),
        "created_at": contract.created_at,
    }


def to_payment_out(payment: InsurancePayment) -> dict:
    return {
        "id": payment.id,
        "contract_id": payment.contract_id,
        "amount": payment.amount,
        "paid_at": payment.paid_at,
        "transaction_id": payment.transaction_id,
        "created_at": payment.created_at,
    }