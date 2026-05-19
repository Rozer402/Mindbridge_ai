"""
WebSocket endpoint for real-time streaming chat.
ws://localhost:8000/ws/chat/{session_id}?token=<jwt>
"""

import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.session import ChatSession
from app.models.message import Message
from app.services.auth_service import decode_token
from app.services.ai_service import process_message
from jose import JWTError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    await websocket.accept()

    # Validate token
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.send_json({"error": "Invalid token type"})
            await websocket.close(code=4001)
            return
        user_id = payload.get("sub")
    except JWTError:
        await websocket.send_json({"error": "Invalid or expired token"})
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        # Verify user
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            await websocket.send_json({"error": "User not found"})
            await websocket.close(code=4003)
            return

        # Get or create session
        try:
            sid = uuid.UUID(session_id)
        except ValueError:
            await websocket.send_json({"error": "Invalid session_id"})
            await websocket.close(code=4000)
            return

        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == sid,
                ChatSession.user_id == user.id
            )
        )
        session = session_result.scalar_one_or_none()

        if not session:
            session = ChatSession(id=sid, user_id=user.id)
            db.add(session)
            await db.flush()

        await websocket.send_json({"type": "connected", "session_id": str(session.id)})

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                    user_message = data.get("message", "").strip()
                except json.JSONDecodeError:
                    user_message = raw.strip()

                if not user_message:
                    continue

                # Send typing indicator
                await websocket.send_json({"type": "typing"})

                # Get history
                history_result = await db.execute(
                    select(Message)
                    .where(Message.session_id == session.id)
                    .order_by(Message.created_at)
                    .limit(20)
                )
                history = [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]

                # Run AI pipeline
                ai_result = await process_message(user_message, history)

                # Save messages
                user_msg = Message(session_id=session.id, role="user", content=user_message,
                                   relevance_score=ai_result["relevance_score"])
                ai_msg = Message(session_id=session.id, role="assistant", content=ai_result["response"],
                                 relevance_score=ai_result["relevance_score"], is_crisis=ai_result["is_crisis"])
                db.add(user_msg)
                db.add(ai_msg)
                session.message_count += 2
                if ai_result["is_crisis"]:
                    session.crisis_flagged = True
                await db.flush()

                # Send response
                await websocket.send_json({
                    "type": "message",
                    "response": ai_result["response"],
                    "is_crisis": ai_result["is_crisis"],
                    "is_relevant": ai_result["is_relevant"],
                    "relevance_score": ai_result["relevance_score"],
                    "few_shot_count": ai_result["few_shot_count"],
                })

        except WebSocketDisconnect:
            logger.info(f"[WS] Client disconnected: {user.email} / session {session_id}")
        except Exception as e:
            logger.error(f"[WS] Error: {e}")
            try:
                await websocket.send_json({"type": "error", "message": "An error occurred"})
            except Exception:
                pass
