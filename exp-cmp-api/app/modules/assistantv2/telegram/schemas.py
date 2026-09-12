"""Contrats des endpoints REST Telegram (liaison du compte applicatif au
chat Telegram par token jetable deep-link)."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class BindingTokenOut(BaseModel):
    token: str
    expires_at: datetime
    instruction: str


class BindingMeOut(BaseModel):
    linked: bool
    chat_id: int | None = None
    user_id: uuid.UUID | None = None
    tg_username: str | None = None
    active: bool | None = None
    linked_at: datetime | None = None
    last_seen_at: datetime | None = None


class BindingAdminOut(BaseModel):
    id: uuid.UUID
    chat_id: int
    user_id: uuid.UUID
    tg_username: str | None = None
    active: bool
    linked_at: datetime
    last_seen_at: datetime | None = None