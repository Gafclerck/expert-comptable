import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.audit.models import AuditAction


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: AuditAction
    entity_type: str
    entity_id: uuid.UUID | None
    old_values: dict | None
    new_values: dict | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}