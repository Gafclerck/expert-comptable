from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, max_length=100)


class IntentCommand(BaseModel):
    operation: str
    business: str = "assurance"
    params: dict = {}
    confidence: str = "low"


class AssistantReply(BaseModel):
    text: str
    session_id: str
    intent: str | None = None
    executed: bool = False
    clarification: bool = False
    missing_field: str | None = None
    options: list[str] = []


class IntentMeta(BaseModel):
    operation: str
    label: str
    example: str