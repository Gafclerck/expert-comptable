import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.events import publish
from app.modules.identity.service import business_exists, get_business_ids_for_user
from app.modules.ledger.models import (
    Account,
    AccountType,
    Category,
    CategoryType,
    LineDirection,
    Transaction,
    TransactionAllocation,
    TransactionLine,
    TransactionStatus,
    TransactionType,
    Transfer,
    TransferStatus,
)

CREDIT_TYPES = {TransactionType.REVENUE}
DEBIT_TYPES = {TransactionType.EXPENSE}


def _ensure_business_access(db: Session, user, business_id: uuid.UUID) -> None:
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None and business_id not in allowed:
        raise HTTPException(status_code=403, detail="Acces refuse a cette activite")


def get_account(db: Session, account_id: uuid.UUID, user) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    _ensure_business_access(db, user, account.business_id)
    return account


def list_accounts(db: Session, user, business_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100) -> list[Account]:
    query = db.query(Account)
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None:
        query = query.filter(Account.business_id.in_(allowed))
    if business_id is not None:
        query = query.filter(Account.business_id == business_id)
    return query.order_by(Account.created_at).offset(skip).limit(limit).all()


DEFAULT_ACCOUNT_NAME = "Caisse Principale"


def create_default_business_account(
    db: Session, business_id: uuid.UUID, actor_id: str | None = None
) -> Account | None:
    """Cree une caisse par defaut pour une activite si elle n'en possede pas encore."""
    existing = db.query(Account).filter(Account.business_id == business_id).first()
    if existing:
        return existing
    account = Account(
        business_id=business_id,
        name=DEFAULT_ACCOUNT_NAME,
        type=AccountType.CASH,
        currency="FCFA",
        opening_balance=Decimal("0"),
        active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    publish(
        "ledger.account.created",
        actor_id=actor_id,
        entity_id=str(account.id),
        new_values={"business_id": str(account.business_id), "name": account.name, "type": account.type.value},
    )
    return account


def _handle_business_created(
    entity_id: str | None = None,
    actor_id: str | None = None,
    **_ignored,
) -> None:
    if not entity_id:
        return
    from app.core.db import session as session_factory
    db = session_factory()
    try:
        create_default_business_account(db, uuid.UUID(entity_id), actor_id=actor_id)
    finally:
        db.close()


_listeners_attached = False


def attach_listeners() -> None:
    global _listeners_attached
    if _listeners_attached:
        return
    from app.core.events import subscribe
    subscribe("identity.business.created", _handle_business_created)
    _listeners_attached = True


def create_account(
    db: Session, actor, business_id: uuid.UUID, name: str, acct_type: AccountType,
    currency: str, opening_balance: Decimal,
) -> Account:
    if not business_exists(db, business_id):
        raise HTTPException(status_code=404, detail="Activite introuvable")
    # One-to-one : une activite ne possede qu'une seule caisse.
    if db.query(Account).filter(Account.business_id == business_id).first():
        raise HTTPException(status_code=409, detail="Cette activite dispose deja d'un compte")
    account = Account(
        business_id=business_id,
        name=name,
        type=acct_type,
        currency=currency,
        opening_balance=opening_balance,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    actor_id = str(actor.id) if hasattr(actor, "id") and actor.id else (str(actor) if actor else None)
    publish(
        "ledger.account.created",
        actor_id=actor_id,
        entity_id=str(account.id),
        new_values={"business_id": str(account.business_id), "name": account.name, "type": account.type.value},
    )
    return account


def get_category(db: Session, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categorie introuvable")
    return category


def list_categories(db: Session) -> list[Category]:
    return db.query(Category).order_by(Category.code).all()


def create_category(db: Session, actor, code: str, name: str, ctype: CategoryType) -> Category:
    if db.query(Category).filter(Category.code == code).first():
        raise HTTPException(status_code=400, detail="Ce code de categorie existe deja")
    category = Category(code=code, name=name, type=ctype)
    db.add(category)
    db.commit()
    db.refresh(category)
    publish(
        "ledger.category.created",
        actor_id=str(actor.id),
        entity_id=str(category.id),
        new_values={"code": category.code, "name": category.name, "type": category.type.value},
    )
    return category


def _expected_direction(txn_type: TransactionType) -> LineDirection:
    if txn_type in CREDIT_TYPES:
        return LineDirection.CREDIT
    return LineDirection.DEBIT


def record_revenue(
    db: Session,
    actor,
    *,
    business_id: uuid.UUID,
    account_id: uuid.UUID,
    amount: Decimal,
    description: str | None,
    occurred_at: datetime | None,
    category_id: uuid.UUID,
    commit: bool = True,
) -> Transaction:
    """Facade metier : encaisse un revenu sur une seule ligne (ex. prime d'assurance)."""
    return create_transaction(
        db,
        actor,
        business_id=business_id,
        account_id=account_id,
        txn_type=TransactionType.REVENUE,
        amount=amount,
        description=description,
        occurred_at=occurred_at,
        lines=[{"category_id": category_id, "amount": amount, "direction": LineDirection.CREDIT}],
        allocations=[],
        commit=commit,
    )


def record_expense(
    db: Session,
    actor,
    *,
    business_id: uuid.UUID,
    account_id: uuid.UUID,
    amount: Decimal,
    description: str | None,
    occurred_at: datetime | None,
    category_id: uuid.UUID,
    commit: bool = True,
) -> Transaction:
    """Facade metier : debite une depense sur une seule ligne (ex. achat de poulets)."""
    return create_transaction(
        db,
        actor,
        business_id=business_id,
        account_id=account_id,
        txn_type=TransactionType.EXPENSE,
        amount=amount,
        description=description,
        occurred_at=occurred_at,
        lines=[{"category_id": category_id, "amount": amount, "direction": LineDirection.DEBIT}],
        allocations=[],
        commit=commit,
    )


def create_transaction(
    db: Session,
    actor,
    *,
    business_id: uuid.UUID,
    account_id: uuid.UUID,
    txn_type: TransactionType,
    amount: Decimal,
    description: str | None,
    occurred_at: datetime | None,
    lines: list[dict],
    allocations: list[dict],
    commit: bool = True,
) -> Transaction:
    if not business_exists(db, business_id):
        raise HTTPException(status_code=404, detail="Activite introuvable")
    _ensure_business_access(db, actor, business_id)
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if account.business_id != business_id:
        raise HTTPException(status_code=400, detail="Le compte n'appartient pas a cette activite")
    if not account.active:
        raise HTTPException(status_code=400, detail="Compte inactif")

    expected = _expected_direction(txn_type)
    total_lines = Decimal("0")
    for line in lines:
        category = get_category(db, line["category_id"])
        if line["direction"] != expected:
            raise HTTPException(status_code=400, detail="La direction des lignes ne correspond pas au type de transaction")
        if category.type != (CategoryType.CREDIT if expected == LineDirection.CREDIT else CategoryType.DEBIT):
            raise HTTPException(status_code=400, detail=f"La categorie {category.code} est de type {category.type.value}")
        total_lines += line["amount"]
    if total_lines != amount:
        raise HTTPException(status_code=400, detail="La somme des lignes doit etre egale au montant de la transaction")

    alloc_sum = sum((a["amount"] for a in allocations), start=Decimal("0"))
    if alloc_sum > amount:
        raise HTTPException(status_code=400, detail="La somme des ventilations depasse le montant")
    for alloc in allocations:
        if not business_exists(db, alloc["business_id"]):
            raise HTTPException(status_code=404, detail="Activite de ventilation introuvable")

    txn = Transaction(
        business_id=business_id,
        account_id=account_id,
        type=txn_type,
        amount=amount,
        description=description,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        status=TransactionStatus.POSTED,
        created_by=actor.id,
        immutable=True,
    )
    db.add(txn)
    db.flush()
    db.add_all(
        TransactionLine(
            transaction_id=txn.id,
            category_id=line["category_id"],
            amount=line["amount"],
            direction=line["direction"],
            description=line.get("description"),
        )
        for line in lines
    )
    if allocations:
        pct_scale = Decimal("100") / amount
        db.add_all(
            TransactionAllocation(
                transaction_id=txn.id,
                business_id=alloc["business_id"],
                amount=alloc["amount"],
                percentage=(alloc["amount"] * pct_scale),
            )
            for alloc in allocations
        )
    if commit:
        db.commit()
        db.refresh(txn)
        publish(
            "ledger.transaction.posted",
            actor_id=str(actor.id),
            entity_id=str(txn.id),
            new_values={
                "business_id": str(txn.business_id),
                "account_id": str(txn.account_id),
                "type": txn.type.value,
                "amount": str(txn.amount),
            },
        )
    else:
        db.flush()
        db.refresh(txn)
    return txn


def create_transfer(
    db: Session,
    actor,
    *,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount: Decimal,
    occurred_at: datetime | None,
    reference: str | None,
) -> Transfer:
    source = db.get(Account, source_account_id)
    destination = db.get(Account, destination_account_id)
    if not source or not destination:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if source.id == destination.id:
        raise HTTPException(status_code=400, detail="Le compte source et le compte destination doivent differer")
    if not source.active or not destination.active:
        raise HTTPException(status_code=400, detail="Compte inactif")
    _ensure_business_access(db, actor, source.business_id)
    _ensure_business_access(db, actor, destination.business_id)

    transfer = Transfer(
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=amount,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        status=TransferStatus.POSTED,
        reference=reference,
        created_by=actor.id,
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    publish(
        "ledger.transfer.posted",
        actor_id=str(actor.id),
        entity_id=str(transfer.id),
        new_values={
            "source_account_id": str(transfer.source_account_id),
            "destination_account_id": str(transfer.destination_account_id),
            "amount": str(transfer.amount),
        },
    )
    return transfer


def compute_balance(db: Session, account: Account) -> dict:
    txn_rows = (
        db.query(Transaction.type, func.coalesce(func.sum(Transaction.amount), Decimal("0")))
        .filter(Transaction.account_id == account.id, Transaction.status == TransactionStatus.POSTED)
        .group_by(Transaction.type)
        .all()
    )
    inflows = Decimal("0")
    outflows = Decimal("0")
    for ttype, total in txn_rows:
        ttype = TransactionType(ttype)
        if ttype in CREDIT_TYPES:
            inflows += total
        elif ttype in DEBIT_TYPES:
            outflows += total

    src_sum = (
        db.query(func.coalesce(func.sum(Transfer.amount), Decimal("0")))
        .filter(Transfer.source_account_id == account.id, Transfer.status == TransferStatus.POSTED)
        .scalar()
        or Decimal("0")
    )
    dst_sum = (
        db.query(func.coalesce(func.sum(Transfer.amount), Decimal("0")))
        .filter(Transfer.destination_account_id == account.id, Transfer.status == TransferStatus.POSTED)
        .scalar()
        or Decimal("0")
    )
    outflows += src_sum
    inflows += dst_sum
    balance = account.opening_balance + inflows - outflows
    return {
        "account_id": account.id,
        "name": account.name,
        "currency": account.currency,
        "opening_balance": account.opening_balance,
        "inflows": inflows,
        "outflows": outflows,
        "balance": balance,
    }


def compute_period_totals(db: Session, user, business_id: uuid.UUID, start: date, end: date) -> dict:
    """Encaissements/depenses sur une periode donnee (bornes incluses), pour une
    activite entiere (toutes ses caisses confondues). Contrairement a
    compute_balance, qui est cumulatif depuis l'ouverture du compte, ceci
    repond a des questions comme "combien j'ai encaisse ce mois". Les
    virements entre caisses ne sont pas comptes : ce n'est ni un encaissement
    ni une depense au sens de l'activite, juste un mouvement de tresorerie
    interne.
    """
    _ensure_business_access(db, user, business_id)
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)
    rows = (
        db.query(Transaction.type, func.coalesce(func.sum(Transaction.amount), Decimal("0")))
        .filter(
            Transaction.business_id == business_id,
            Transaction.status == TransactionStatus.POSTED,
            Transaction.occurred_at >= start_dt,
            Transaction.occurred_at <= end_dt,
        )
        .group_by(Transaction.type)
        .all()
    )
    inflows = Decimal("0")
    outflows = Decimal("0")
    for ttype, total in rows:
        ttype = TransactionType(ttype)
        if ttype in CREDIT_TYPES:
            inflows += total
        elif ttype in DEBIT_TYPES:
            outflows += total
    return {
        "business_id": business_id,
        "start": start,
        "end": end,
        "inflows": inflows,
        "outflows": outflows,
        "net": inflows - outflows,
    }


def get_transaction(db: Session, transaction_id: uuid.UUID, user) -> Transaction:
    txn = (
        db.query(Transaction)
        .options(selectinload(Transaction.lines), selectinload(Transaction.allocations))
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    _ensure_business_access(db, user, txn.business_id)
    return txn


def list_transactions(
    db: Session,
    user,
    business_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Transaction]:
    query = db.query(Transaction).options(selectinload(Transaction.lines), selectinload(Transaction.allocations))
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None:
        query = query.filter(Transaction.business_id.in_(allowed))
    if business_id is not None:
        query = query.filter(Transaction.business_id == business_id)
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    return query.order_by(Transaction.occurred_at.desc()).offset(skip).limit(limit).all()


def get_transfer(db: Session, transfer_id: uuid.UUID, user) -> Transfer:
    transfer = db.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Virement introuvable")
    source = db.get(Account, transfer.source_account_id)
    destination = db.get(Account, transfer.destination_account_id)
    for account in (source, destination):
        if account:
            _ensure_business_access(db, user, account.business_id)
    return transfer


def list_transfers(db: Session, user, skip: int = 0, limit: int = 100) -> list[Transfer]:
    rows = db.query(Transfer).order_by(Transfer.occurred_at.desc()).offset(skip).limit(limit).all()
    allowed = get_business_ids_for_user(db, user)
    if allowed is None:
        return rows
    accounts = db.query(Account).all()
    by_id = {a.id: a.business_id for a in accounts}
    return [t for t in rows if by_id.get(t.source_account_id) in allowed or by_id.get(t.destination_account_id) in allowed]