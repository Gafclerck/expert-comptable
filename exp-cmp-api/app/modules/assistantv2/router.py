"""Router assistant v2. VOLONTAIREMENT NON branche sur app.main : voir
app/modules/assistantv2/__init__.py. A inclure dans app/main.py uniquement
une fois la phase de test manuelle/automatisee concluante :

    from app.modules.assistantv2.router import api_router as assistantv2_router
    ...
    app.include_router(assistantv2_router, prefix=settings.API_STR)
"""
from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.modules.assistantv2 import service as assistantv2_service
from app.modules.assistantv2.schemas import AssistantReplyV2, ChatIn, ToolMeta

assistantv2_router = APIRouter(prefix="/assistantv2", tags=["assistantv2"])


@assistantv2_router.get("/tools", response_model=list[ToolMeta])
def list_tools() -> list[dict]:
    return assistantv2_service.list_tools()


@assistantv2_router.post("/chat", response_model=AssistantReplyV2)
def chat(data: ChatIn, db: SessionDep, current_user: CurrentUser) -> AssistantReplyV2:
    return assistantv2_service.chat(db, current_user, data.message, data.session_id)


api_router = APIRouter()
api_router.include_router(assistantv2_router)
