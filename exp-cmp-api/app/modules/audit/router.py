import uuid

from fastapi import APIRouter, Query

from app.core.deps import RequireRoot, SessionDep
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditAction
from app.modules.audit.schemas import AuditLogOut

audit_router = APIRouter(prefix="/audit", tags=["audit"])


@audit_router.get("/logs", response_model=list[AuditLogOut])
def list_logs(
    db: SessionDep,
    current_user: RequireRoot,
    actor_id: uuid.UUID | None = Query(None),
    action: AuditAction | None = Query(None),
    entity_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict]:
    logs = audit_service.list_logs(db, actor_id, action, entity_type, skip, limit)
    return [audit_service.to_out(log) for log in logs]


api_router = APIRouter()
api_router.include_router(audit_router)