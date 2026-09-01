import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.shared.enums import sa_enum
from app.modules.shared.models import UUIDPkMixin


class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    DISPUTE = "DISPUTE"
    RESOLVE = "RESOLVE"
    REPAY = "REPAY"
    RETURN = "RETURN"
    TRANSFER = "TRANSFER"
    CORRECT = "CORRECT"


class AuditLog(UUIDPkMixin, Base):
    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        sa_enum(AuditAction, length=30), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())