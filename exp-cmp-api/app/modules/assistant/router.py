from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.modules.assistant import service as assistant_service
from app.modules.assistant.schemas import AssistantReply, ChatIn, IntentMeta

assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])


@assistant_router.get("/intents", response_model=list[IntentMeta])
def list_intents() -> list[dict]:
    return assistant_service.list_intents()


@assistant_router.post("/chat", response_model=AssistantReply)
def chat(data: ChatIn, db: SessionDep, current_user: CurrentUser) -> AssistantReply:
    return assistant_service.chat(db, current_user, data.message, data.session_id)


api_router = APIRouter()
api_router.include_router(assistant_router)