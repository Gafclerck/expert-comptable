from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, max_length=100)


class AssistantReplyV3(BaseModel):
    text: str
    session_id: str
    executed_tools: list[str] = []
    clarification: bool = False
    missing_field: str | None = None
    options: list[str] = []
    confirmation_required: bool = False
    pending_action: str | None = None


class ToolMeta(BaseModel):
    operation: str
    label: str
    example: str
    business: str | None = None
    is_critical: bool = False
