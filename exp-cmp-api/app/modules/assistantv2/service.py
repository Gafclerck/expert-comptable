from sqlalchemy.orm import Session

from app.modules.assistantv2 import orchestrator, registry
from app.modules.assistantv2.schemas import AssistantReplyV2, ToolMeta

# S'assure que tous les outils sont enregistres des l'import de ce module
# (deja declenche par orchestrator, mais explicite ici aussi : service.py est
# le point d'entree naturel du module, autant qu'il soit auto-suffisant).
from app.modules.assistantv2 import tools as _tools  # noqa: F401


def chat(db: Session, actor, message: str, session_id: str | None) -> AssistantReplyV2:
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
