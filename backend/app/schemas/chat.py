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
    # Core response
    response: str
    session_id: uuid.UUID

    # Safety signals
    is_crisis: bool

    # Relevance / retrieval metadata
    is_relevant: bool
    relevance_score: float
    few_shot_count: int

    # Classifier enrichment (None when model not yet trained)
    predicted_category: str | None = None
    classifier_confidence: float = 0.0
    uncertainty: float = 0.0

    # Memory
    memory_used: bool = False


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    message_count: int
    crisis_flagged: bool
    started_at: datetime

    class Config:
        from_attributes = True
