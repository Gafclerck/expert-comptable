"""Modeles du canal Telegram :
- `TelegramBinding`   : liaison chat_id (compte Telegram) -> user (compte app) ;
- `TelegramLinkToken` : token jetable du deep-link `/start <TOKEN>` ;
- `TelegramMessage`   : journal d'idempotence (exactly-once) des updates
  Telegram deja traites (sur `update_id`, unique par le reseau Telegram).

Imports pour que `Base.metadata.create_all` des tests les cree : le module
est importe via le router monte dans app.main.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.modules.shared.models import UUIDPkMixin


class TelegramBinding(UUIDPkMixin, Base):
    __tablename__ = "telegram_bindings"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tg_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TelegramLinkToken(UUIDPkMixin, Base):
    __tablename__ = "telegram_link_tokens"

    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TelegramMessage(UUIDPkMixin, Base):
    __tablename__ = "telegram_messages"

    update_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # "in" | "out"
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )