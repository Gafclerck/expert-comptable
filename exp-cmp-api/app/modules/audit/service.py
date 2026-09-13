import uuid
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.db import session as session_factory
from app.core.events import subscribe
from app.modules.audit.models import AuditAction, AuditLog

_EVENT_ACTIONS = {
    "identity.person.created": ("persons", AuditAction.CREATE, None),
    "identity.person.updated": ("persons", AuditAction.UPDATE, None),
    "identity.role.created": ("roles", AuditAction.CREATE, None),
    "identity.user.created": ("users", AuditAction.CREATE, None),
    "identity.user.updated": ("users", AuditAction.UPDATE, None),
    "identity.business.created": ("businesses", AuditAction.CREATE, None),
    "identity.business.updated": ("businesses", AuditAction.UPDATE, None),
    "identity.business_account.created": ("business_accounts", AuditAction.CREATE, None),
    "ledger.account.created": ("accounts", AuditAction.CREATE, None),
    "ledger.category.created": ("categories", AuditAction.CREATE, None),
    "ledger.transaction.posted": ("transactions", AuditAction.CREATE, None),
    "ledger.transfer.posted": ("transfers", AuditAction.TRANSFER, None),
    "insurance.client.created": ("insurance_clients", AuditAction.CREATE, None),
    "insurance.contract.created": ("insurance_contracts", AuditAction.CREATE, None),
    "insurance.contract.cancelled": ("insurance_contracts", AuditAction.UPDATE, None),
    "insurance.payment.created": ("insurance_payments", AuditAction.CREATE, None),
    "insurance.due.created": ("insurance_dues", AuditAction.CREATE, None),
    "poultry.purchase.created": ("poultry_purchases", AuditAction.CREATE, None),
    "poultry.sale.created": ("poultry_sales", AuditAction.CREATE, None),
    "vtc.chauffeur.created": ("drivers", AuditAction.CREATE, None),
    "vtc.chauffeur.updated": ("drivers", AuditAction.UPDATE, None),
    "vtc.vehicule.created": ("vehicles", AuditAction.CREATE, None),
    "vtc.vehicule.updated": ("vehicles", AuditAction.UPDATE, None),
    "vtc.affectation.created": ("vehicle_assignments", AuditAction.CREATE, None),
    "vtc.affectation.ended": ("vehicle_assignments", AuditAction.UPDATE, None),
    "vtc.remittance.created": ("driver_remittances", AuditAction.CREATE, None),
    "vtc.expense.created": ("vehicle_expenses", AuditAction.CREATE, None),
    "vtc.downtime.created": ("vehicle_downtimes", AuditAction.CREATE, None),
    "vtc.downtime.closed": ("vehicle_downtimes", AuditAction.UPDATE, None),
    "assistant.command.executed": ("assistant_commands", AuditAction.CREATE, None),
    "telegram.binding.created": ("telegram_bindings", AuditAction.CREATE, None),
    "telegram.binding.removed": ("telegram_bindings", AuditAction.UPDATE, None),
}


def record(
    actor_id: str | None,
    action: AuditAction,
    entity_type: str,
    entity_id: uuid.UUID | None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    reason: str | None = None,
) -> None:
    db = session_factory()
    try:
        db.add(
            AuditLog(
                actor_id=uuid.UUID(actor_id) if actor_id else None,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_values=old_values,
                new_values=new_values,
                reason=reason,
            )
        )
        db.commit()
    finally:
        db.close()


def _handle(event_type: str, actor_id: str | None = None, entity_id: str | None = None,
            old_values: dict | None = None, new_values: dict | None = None, **_ignored: Any) -> None:
    entity_type, action, _ = _EVENT_ACTIONS[event_type]
    record(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=uuid.UUID(entity_id) if entity_id else None,
        old_values=old_values,
        new_values=new_values,
    )


_attached = False


def attach_listeners() -> None:
    global _attached
    if _attached:
        return
    for event_type in _EVENT_ACTIONS:
        subscribe(event_type, lambda _et=event_type, **kw: _handle(_et, **kw))
    _attached = True


def list_logs(
    db: Session,
    actor_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    entity_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditLog]:
    query = db.query(AuditLog)
    if actor_id is not None:
        query = query.filter(AuditLog.actor_id == actor_id)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    return query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()


def to_out(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "actor_id": log.actor_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "old_values": log.old_values,
        "new_values": log.new_values,
        "reason": log.reason,
        "created_at": log.created_at,
    }