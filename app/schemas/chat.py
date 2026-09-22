from pydantic import BaseModel, Field


class RagRequest(BaseModel):
    query: str = Field(..., min_length=1)
    conversation_id: str
    account_id: int | None = None
    inbox_id: int
    user_id: int | None = None
    channel: str | None = None


class RagResponse(BaseModel):
    answer: str
    intent_detected: str
    sources_used: int
    conversation_id: str