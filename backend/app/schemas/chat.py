from pydantic import BaseModel
from datetime import datetime
import uuid


class SendMessageRequest(BaseModel):
    message: str
    session_id: uuid.UUID | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    relevance_score: float | None
    is_crisis: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    response: str
    is_crisis: bool
    is_relevant: bool
    relevance_score: float
    few_shot_count: int
    session_id: uuid.UUID


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    message_count: int
    crisis_flagged: bool
    started_at: datetime

    class Config:
        from_attributes = True
