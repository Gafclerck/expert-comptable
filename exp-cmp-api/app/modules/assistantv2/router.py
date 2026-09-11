"""Router assistant v2, branche sur app.main : voir /api/assistantv2/chat et
/api/assistantv2/tools. Le module `assistant` (v1) reste actif en parallele
sur /api/assistant/*.
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
