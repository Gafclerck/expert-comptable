"""Router assistant v3. VOLONTAIREMENT NON branche sur app.main tant que les
tests ne sont pas concluants (meme methode que v2)."""
from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.modules.assistantv3 import service as assistantv3_service
from app.modules.assistantv3.schemas import AssistantReplyV3, ChatIn, ToolMeta

assistantv3_router = APIRouter(prefix="/assistantv3", tags=["assistantv3"])


@assistantv3_router.get("/tools", response_model=list[ToolMeta])
def list_tools() -> list[dict]:
    return assistantv3_service.list_tools()


@assistantv3_router.post("/chat", response_model=AssistantReplyV3)
def chat(data: ChatIn, db: SessionDep, current_user: CurrentUser) -> AssistantReplyV3:
    return assistantv3_service.chat(db, current_user, data.message, data.session_id)


api_router = APIRouter()
api_router.include_router(assistantv3_router)
