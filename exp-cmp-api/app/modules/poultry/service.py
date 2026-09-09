import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.events import publish
from app.modules.identity.service import get_business_by_code, get_business_ids_for_user
from app.modules.ledger.service import record_expense, record_revenue
from app.modules.poultry.models import Approvisionnement, Lot, Vente, VenteLot

POULETS_BUSINESS_CODE = "poulets"


def _poulets_business(db: Session):
    return get_business_by_code(db, POULETS_BUSINESS_CODE)


def _ensure_poultry_access(db: Session, user, business) -> None:
    allowed = get_business_ids_for_user(db, user)
    if allowed is not None and business.id not in allowed:
        raise HTTPException(status_code=403, detail="Acces refuse a l'activite poulets")


def create_approvisionnement(
    db: Session,
    actor,
    *,
    quantity: int,
    unit_price: Decimal,
    note: str | None,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    occurred_at: datetime | None = None,
) -> Approvisionnement:
    """Achete des poulets : cree un lot (stock disponible) et debite la caisse.
    1 achat = 1 lot, toujours (pas de fusion avec un lot existant)."""
    business = _poulets_business(db)
    _ensure_poultry_access(db, actor, business)
    amount = (unit_price * quantity).quantize(Decimal("0.01"))

    transaction = record_expense(
        db,
        actor,
        business_id=business.id,
        account_id=account_id,
        amount=amount,
        description=f"Achat de {quantity} poulets",
        occurred_at=occurred_at,
        category_id=category_id,
        commit=False,
    )
    lot = Lot(initial_quantity=quantity, remaining_quantity=quantity, unit_purchase_price=unit_price)
    db.add(lot)
    db.flush()
    appro = Approvisionnement(
        lot_id=lot.id,
        quantity=quantity,
        unit_price=unit_price,
        note=note,
        transaction_id=transaction.id,
    )
    db.add(appro)
    db.commit()
    db.refresh(appro)
    publish(
        "ledger.transaction.posted",
        actor_id=str(actor.id),
        entity_id=str(appro.transaction_id),
        new_values={"business_id": str(business.id), "account_id": str(account_id), "type": "expense", "amount": str(amount)},
    )
    publish(
        "poultry.purchase.created",
        actor_id=str(actor.id),
        entity_id=str(appro.id),
        new_values={"lot_id": str(lot.id), "quantity": quantity, "unit_price": str(unit_price)},
    )
    return appro


def list_approvisionnements(db: Session, user, skip: int = 0, limit: int = 100) -> list[Approvisionnement]:
    business = _poulets_business(db)
    _ensure_poultry_access(db, user, business)
    return db.query(Approvisionnement).order_by(Approvisionnement.created_at).offset(skip).limit(limit).all()


def get_stock_total(db: Session, user) -> int:
    """Stock total disponible, derive : somme du restant de tous les lots. Jamais stocke."""
    business = _poulets_business(db)
    _ensure_poultry_access(db, user, business)
    return db.query(func.coalesce(func.sum(Lot.remaining_quantity), 0)).scalar() or 0


def list_lots(db: Session, user, skip: int = 0, limit: int = 100) -> list[Lot]:
    business = _poulets_business(db)
    _ensure_poultry_access(db, user, business)
    return db.query(Lot).order_by(Lot.created_at).offset(skip).limit(limit).all()


def create_vente(
    db: Session,
    actor,
    *,
    quantity: int,
    unit_price: Decimal,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    occurred_at: datetime | None = None,
) -> Vente:
    """Vend des poulets : preleve en FIFO sur les lots les plus anciens ayant du
    stock, credite la caisse. Refuse si le stock total est insuffisant plutot
    que d'autoriser un stock negatif (l'IA doit alors demander une clarification)."""
    business = _poulets_business(db)
    _ensure_poultry_access(db, actor, business)

    lots = (
        db.query(Lot)
        .filter(Lot.remaining_quantity > 0)
        .order_by(Lot.created_at)
        .all()
    )
    available = sum(lot.remaining_quantity for lot in lots)
    if quantity > available:
        raise HTTPException(status_code=400, detail=f"Stock insuffisant : {available} poulet(s) disponible(s)")

    amount = (unit_price * quantity).quantize(Decimal("0.01"))
    transaction = record_revenue(
        db,
        actor,
        business_id=business.id,
        account_id=account_id,
        amount=amount,
        description=f"Vente de {quantity} poulets",
        occurred_at=occurred_at,
        category_id=category_id,
        commit=False,
    )
    sale = Vente(quantity=quantity, unit_price=unit_price, transaction_id=transaction.id)
    db.add(sale)
    db.flush()

    remaining_to_take = quantity
    for lot in lots:
        if remaining_to_take <= 0:
            break
        taken = min(lot.remaining_quantity, remaining_to_take)
        lot.remaining_quantity -= taken
        db.add(VenteLot(sale_id=sale.id, lot_id=lot.id, quantity_taken=taken))
        remaining_to_take -= taken

    db.commit()
    db.refresh(sale)
    publish(
        "ledger.transaction.posted",
        actor_id=str(actor.id),
        entity_id=str(sale.transaction_id),
        new_values={"business_id": str(business.id), "account_id": str(account_id), "type": "revenue", "amount": str(amount)},
    )
    publish(
        "poultry.sale.created",
        actor_id=str(actor.id),
        entity_id=str(sale.id),
        new_values={"quantity": quantity, "unit_price": str(unit_price)},
    )
    return sale


def list_ventes(db: Session, user, skip: int = 0, limit: int = 100) -> list[Vente]:
    business = _poulets_business(db)
    _ensure_poultry_access(db, user, business)
    return db.query(Vente).order_by(Vente.created_at).offset(skip).limit(limit).all()


def to_appro_out(appro: Approvisionnement) -> dict:
    return {
        "id": appro.id,
        "lot_id": appro.lot_id,
        "quantity": appro.quantity,
        "unit_price": appro.unit_price,
        "note": appro.note,
        "transaction_id": appro.transaction_id,
        "created_at": appro.created_at,
    }


def to_vente_out(sale: Vente) -> dict:
    return {
        "id": sale.id,
        "quantity": sale.quantity,
        "unit_price": sale.unit_price,
        "transaction_id": sale.transaction_id,
        "created_at": sale.created_at,
    }


def to_lot_out(lot: Lot) -> dict:
    return {
        "id": lot.id,
        "initial_quantity": lot.initial_quantity,
        "remaining_quantity": lot.remaining_quantity,
        "unit_purchase_price": lot.unit_purchase_price,
        "created_at": lot.created_at,
    }
