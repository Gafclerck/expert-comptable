import re
import unicodedata
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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
    InsuranceDue,
    InsuranceDueStatus,
    InsurancePayment,
    _date_to_datetime,
)
from app.modules.ledger.service import record_revenue

ASSURANCE_BUSINESS_CODE = "assurance"


def _normalize(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(ch) != "Mn"
    ).strip()


def _assurance_business(db: Session):
    return get_business_by_code(db, ASSURANCE_BUSINESS_CODE)


def _ensure_insurance_access(db: Session, user, business) -> None:
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None and business.id not in allowed:
        raise HTTPException(status_code=403, detail="Acces refuse a l'activite assurance")


def expire_overdue_contracts(db: Session) -> None:
    today = date.today()
    db.query(InsuranceContract).filter(
        InsuranceContract.status == InsuranceContractStatus.ACTIVE,
        InsuranceContract.end_date.isnot(None),
        InsuranceContract.end_date < today,
    ).update(
        {InsuranceContract.status: InsuranceContractStatus.EXPIRED},
        synchronize_session="fetch",
    )
    db.flush()


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

    try:
        person = create_person(db, actor, full_name=full_name, phone=phone, commit=False)
        add_business_customer(db, actor, business.id, person.id, commit=False)
        client = InsuranceClient(person_id=person.id, client_number=client_number)
        db.add(client)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ce numero de client existe deja")
    except HTTPException:
        db.rollback()
        raise
    db.refresh(client)
    publish(
        "identity.person.created",
        actor_id=str(actor.id),
        entity_id=str(client.person_id),
        new_values={"full_name": full_name, "phone": phone},
    )
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
    expire_overdue_contracts(db)
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
    expire_overdue_contracts(db)
    db.commit()
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
    expire_overdue_contracts(db)
    db.commit()
    query = db.query(InsuranceContract)
    if client_id is not None:
        get_client(db, user, client_id)
        query = query.filter(InsuranceContract.client_id == client_id)
    return query.order_by(InsuranceContract.created_at).offset(skip).limit(limit).all()


def cancel_contract(db: Session, actor, contract_id: uuid.UUID) -> InsuranceContract:
    contract = get_contract(db, actor, contract_id)
    if contract.status == InsuranceContractStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Contrat deja annule")
    old_status = contract.status.value
    contract.status = InsuranceContractStatus.CANCELLED
    db.commit()
    db.refresh(contract)
    publish(
        "insurance.contract.cancelled",
        actor_id=str(actor.id),
        entity_id=str(contract.id),
        old_values={"status": old_status},
        new_values={"status": contract.status.value},
    )
    return contract


def _paid_total(db: Session, contract: InsuranceContract) -> Decimal:
    return (
        db.query(func.coalesce(func.sum(InsurancePayment.amount), Decimal("0")))
        .filter(InsurancePayment.contract_id == contract.id)
        .scalar()
        or Decimal("0")
    )


def remaining_amount(db: Session, contract: InsuranceContract) -> Decimal:
    """Montant restant du. Peut etre negatif : le client a alors une avance."""
    return contract.premium - _paid_total(db, contract)


def advance_amount(db: Session, contract: InsuranceContract) -> Decimal:
    """Avance (trop-percu) disponible sur le contrat, 0 FCFA si aucune."""
    remaining = remaining_amount(db, contract)
    return -remaining if remaining < 0 else Decimal("0")


def refresh_due_statuses(db: Session, contract: InsuranceContract) -> None:
    """Recalcule le statut de chaque echeance par cascade chronologique : le total
    deja paye sur le contrat (tous paiements confondus) couvre les echeances dans
    l'ordre de leur date, la plus ancienne d'abord. Jamais mis a jour a la main.
    """
    dues = (
        db.query(InsuranceDue)
        .filter(InsuranceDue.contract_id == contract.id)
        .order_by(InsuranceDue.due_date)
        .all()
    )
    total_paid = _paid_total(db, contract)
    today = date.today()
    cumulative = Decimal("0")
    for due in dues:
        cumulative += due.amount_due
        if total_paid >= cumulative:
            new_status = InsuranceDueStatus.PAID
        elif due.due_date < today:
            new_status = InsuranceDueStatus.OVERDUE
        else:
            new_status = InsuranceDueStatus.PENDING
        if due.status != new_status:
            due.status = new_status
    db.flush()


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
    # Un paiement superieur au reste a payer n'est plus refuse : le surplus est
    # credite comme avance sur le contrat (remaining_amount devient negatif,
    # voir advance_amount()). Le montant integral est toujours encaisse en
    # caisse puisque l'argent est reellement recu.

    paid_on = paid_at or date.today()
    try:
        transaction = record_revenue(
            db,
            actor,
            business_id=business.id,
            account_id=account_id,
            amount=amount,
            description=f"Prime assurance - contrat {contract.matricule}",
            occurred_at=_date_to_datetime(paid_on),
            category_id=category_id,
            commit=False,
        )
        payment = InsurancePayment(
            contract_id=contract.id,
            amount=amount,
            paid_at=paid_on,
            transaction_id=transaction.id,
        )
        db.add(payment)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Impossible d'enregistrer ce paiement")
    db.refresh(payment)
    publish(
        "ledger.transaction.posted",
        actor_id=str(actor.id),
        entity_id=str(payment.transaction_id),
        new_values={
            "business_id": str(business.id),
            "account_id": str(account_id),
            "type": "revenue",
            "amount": str(amount),
        },
    )
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


def create_due(
    db: Session,
    actor,
    *,
    contract_id: uuid.UUID,
    due_date: date,
    amount_due: Decimal,
) -> InsuranceDue:
    contract = get_contract(db, actor, contract_id)
    due = InsuranceDue(contract_id=contract.id, due_date=due_date, amount_due=amount_due)
    db.add(due)
    db.commit()
    db.refresh(due)
    refresh_due_statuses(db, contract)
    db.commit()
    db.refresh(due)
    publish(
        "insurance.due.created",
        actor_id=str(actor.id),
        entity_id=str(due.id),
        new_values={
            "contract_id": str(due.contract_id),
            "due_date": due.due_date.isoformat(),
            "amount_due": str(due.amount_due),
        },
    )
    return due


def list_dues(db: Session, user, contract_id: uuid.UUID) -> list[InsuranceDue]:
    contract = get_contract(db, user, contract_id)
    refresh_due_statuses(db, contract)
    db.commit()
    return (
        db.query(InsuranceDue)
        .filter(InsuranceDue.contract_id == contract.id)
        .order_by(InsuranceDue.due_date)
        .all()
    )


def find_client(db: Session, user, ref: str) -> InsuranceClient:
    """Resout un client par numero (CLI-xxxxx) ou par nom (insensible aux accents)."""
    business = _assurance_business(db)
    _ensure_insurance_access(db, user, business)
    clients = db.query(InsuranceClient).order_by(InsuranceClient.created_at).all()
    norm_ref = _normalize(ref)
    exact = [c for c in clients if _normalize(c.client_number) == norm_ref]
    if len(exact) == 1:
        return exact[0]
    names = {c: _normalize(get_person_summary(db, c.person_id).full_name) for c in clients}
    by_name = [c for c in clients if names[c] == norm_ref]
    if len(by_name) == 1:
        return by_name[0]
    partial = [c for c in clients if norm_ref in names[c] or names[c] in norm_ref]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise HTTPException(status_code=404, detail="Client introuvable")
    raise HTTPException(status_code=400, detail="Plusieurs clients correspondent a ce nom")


def get_active_contract_by_matricule(db: Session, user, matricule: str) -> InsuranceContract:
    business = _assurance_business(db)
    _ensure_insurance_access(db, user, business)
    expire_overdue_contracts(db)
    db.commit()
    norm = _normalize(re.sub(r"[\s_]", "-", matricule))
    rows = [
        c
        for c in db.query(InsuranceContract).all()
        if _normalize(re.sub(r"[\s_]", "-", c.matricule)) == norm
    ]
    if not rows:
        raise HTTPException(status_code=404, detail="Aucun contrat avec cette matricule")
    for contract in rows:
        if contract.status == InsuranceContractStatus.ACTIVE:
            return contract
    raise HTTPException(status_code=404, detail="Aucun contrat actif avec cette matricule")


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
    remaining = remaining_amount(db, contract)
    return {
        "id": contract.id,
        "client_id": contract.client_id,
        "matricule": contract.matricule,
        "contract_type": contract.contract_type,
        "premium": contract.premium,
        "start_date": contract.start_date,
        "end_date": contract.end_date,
        "status": contract.status,
        "remaining_amount": max(remaining, Decimal("0")),
        "advance_amount": -remaining if remaining < 0 else Decimal("0"),
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


def to_due_out(due: InsuranceDue) -> dict:
    return {
        "id": due.id,
        "contract_id": due.contract_id,
        "due_date": due.due_date,
        "amount_due": due.amount_due,
        "status": due.status,
        "created_at": due.created_at,
    }
