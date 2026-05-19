from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import uuid

from app.database import get_db
from app.models.user import User
from app.models.session import ChatSession
from app.models.message import Message
from app.schemas.chat import SendMessageRequest, ChatResponse, SessionResponse, MessageResponse
from app.services.ai_service import process_message
from app.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get or create session
    session = None
    if data.session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == data.session_id,
                ChatSession.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

    if not session:
        session = ChatSession(user_id=current_user.id)
        db.add(session)
        await db.flush()
        await db.refresh(session)

    # Get session history for context
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
        .limit(20)
    )
    history = history_result.scalars().all()
    session_history = [{"role": m.role, "content": m.content} for m in history]

    # Run AI pipeline
    ai_result = await process_message(data.message, session_history)

    # Save user message
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=data.message,
        relevance_score=ai_result["relevance_score"],
        is_crisis=False,
    )
    db.add(user_msg)

    # Save AI response
    ai_msg = Message(
        session_id=session.id,
        role="assistant",
        content=ai_result["response"],
        relevance_score=ai_result["relevance_score"],
        is_crisis=ai_result["is_crisis"],
    )
    db.add(ai_msg)

    # Update session
    session.message_count += 2
    if ai_result["is_crisis"]:
        session.crisis_flagged = True
    if session.message_count == 2:
        # Set title from first message
        title = data.message[:50] + ("..." if len(data.message) > 50 else "")
        session.title = title

    await db.flush()

    return ChatResponse(
        response=ai_result["response"],
        is_crisis=ai_result["is_crisis"],
        is_relevant=ai_result["is_relevant"],
        relevance_score=ai_result["relevance_score"],
        few_shot_count=ai_result["few_shot_count"],
        session_id=session.id,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.started_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    if not session_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    return {"message": "Session deleted"}
