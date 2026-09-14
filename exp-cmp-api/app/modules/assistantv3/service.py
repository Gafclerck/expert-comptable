from sqlalchemy.orm import Session

from app.modules.assistantv3 import orchestrator, registry
from app.modules.assistantv3.schemas import AssistantReplyV3

from app.modules.assistantv3 import tools as _tools  # noqa: F401


def chat(db: Session, actor, message: str, session_id: str | None) -> AssistantReplyV3:
    return orchestrator.handle_message(db, actor, message, session_id)


def list_tools() -> list[dict]:
    return [
        {
            "operation": spec.name,
            "label": spec.label,
            "example": spec.example,
            "business": spec.business,
            "is_critical": spec.is_critical,
        }
        for spec in registry.all_tools()
    ]
