import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.shared.models import UUIDPkMixin


class Lot(UUIDPkMixin, Base):
    """Un lot de poulets achetes ensemble. Poulet = poulet : pas de distinction
    vivant/abattu/congele, pas d'etape de transformation (decision explicite MVP).
    remaining_quantity est stocke (mis a jour a chaque vente) pour permettre le
    FIFO sans recalcul couteux, mais reste toujours reconstructible depuis
    poultry_sale_lots (source de verite), comme Caisse.solde pour le ledger.
    """

    __tablename__ = "poultry_lots"

    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Approvisionnement(UUIDPkMixin, Base):
    """L'achat qui cree un lot (1 achat = 1 lot). Mouvement financier : sortie
    d'argent. Pas de champ fournisseur : on ne gere pas cette tracabilite.
    """

    __tablename__ = "poultry_purchases"

    lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("poultry_lots.id"), nullable=False, unique=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Vente(UUIDPkMixin, Base):
    """Une vente de poulets. Mouvement financier : entree d'argent. Preleve sur
    un ou plusieurs lots via VenteLot (FIFO, voir poultry.service.create_vente).
    """

    __tablename__ = "poultry_sales"

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class VenteLot(UUIDPkMixin, Base):
    """Ventilation d'une vente sur un lot (une vente peut piocher dans plusieurs
    lots si le plus ancien n'a pas assez de stock restant).
    """

    __tablename__ = "poultry_sale_lots"

    sale_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("poultry_sales.id"), nullable=False, index=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("poultry_lots.id"), nullable=False, index=True)
    quantity_taken: Mapped[int] = mapped_column(Integer, nullable=False)
