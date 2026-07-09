"""
MemoryService — Redis-backed Conversation Memory
=================================================
Stores the last N messages per chat session in Redis as a JSON list.
TTL is applied on every write so idle sessions are auto-expired.

Design decisions
----------------
* Key schema : "mb:memory:{session_id}"  (easy to namespace / flush)
* Storage    : JSON-encoded list of message dicts, newest at the END.
               We cap at MAX_HISTORY entries (user + assistant combined).
* TTL        : Reset on every write — 24 hours by default.
               Idle sessions are garbage-collected automatically.
* Graceful   : If Redis is unavailable the service returns empty history
               and logs a warning — the chat pipeline still works, just
               without memory until Redis recovers.

Message dict schema stored in Redis
--------------------------------------
{
    "role"       : "user" | "assistant",
    "content"    : str,
    "category"   : str | None,          # classifier output for user turns
    "confidence" : float | None,        # classifier confidence
    "is_crisis"  : bool,                # crisis flag from this turn
    "timestamp"  : float                # Unix epoch (for debugging / audit)
}
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
REDIS_KEY_PREFIX = "mb:memory:"
MAX_HISTORY      = 20       # max messages kept per session (10 turns)
HISTORY_FOR_LLM  = 12       # how many recent messages to inject (6 turns)
TTL_SECONDS      = 86_400   # 24 hours — reset on every write


class MemoryService:
    """
    Async Redis-backed conversation memory.

    Lifecycle
    ---------
    1. Call ``await initialize()`` once at FastAPI startup.
    2. Use ``get_history()`` / ``append_message()`` per request.
    3. Call ``close()`` at shutdown.
    """

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None
        self._available: bool = False

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create Redis client and verify connectivity."""
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            # Ping to verify the connection is live
            await self._client.ping()
            self._available = True
            logger.info(
                f"[MemoryService] Connected to Redis at {settings.REDIS_URL}"
            )
        except Exception as exc:
            self._available = False
            logger.warning(
                f"[MemoryService] Redis unavailable ({exc}). "
                "Chat memory disabled — system continues without it."
            )

    async def close(self) -> None:
        """Gracefully close the Redis connection."""
        if self._client:
            await self._client.aclose()
            logger.info("[MemoryService] Redis connection closed.")

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _build_key(session_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}{session_id}"

    async def _safe_get(self, key: str) -> list[dict]:
        """Fetch and deserialise history list; returns [] on any error."""
        try:
            raw = await self._client.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning(f"[MemoryService] Read error for {key}: {exc}")
        return []

    async def _safe_set(self, key: str, history: list[dict]) -> None:
        """Serialise and store history list with TTL; silently catches errors."""
        try:
            await self._client.setex(
                key,
                TTL_SECONDS,
                json.dumps(history, ensure_ascii=False),
            )
        except Exception as exc:
            logger.warning(f"[MemoryService] Write error for {key}: {exc}")

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """True when the Redis connection is live."""
        return self._available

    async def get_history(
        self,
        session_id: str,
        limit: int = HISTORY_FOR_LLM,
    ) -> list[dict]:
        """
        Return the last `limit` messages for this session.
        Each item has keys: role, content, category, confidence, is_crisis, timestamp.
        Returns [] when Redis is unavailable or the session has no history.
        """
        if not self._available:
            return []
        key = self._build_key(session_id)
        history = await self._safe_get(key)
        # Return the most recent `limit` messages
        return history[-limit:] if len(history) > limit else history

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        is_crisis: bool = False,
    ) -> None:
        """
        Append one message to the session history, capping at MAX_HISTORY.
        TTL is refreshed on every write.

        Parameters
        ----------
        session_id  : UUID string (from chat session)
        role        : "user" or "assistant"
        content     : The message text
        category    : Classifier-predicted category (user turns only)
        confidence  : Classifier confidence (user turns only)
        is_crisis   : Whether this turn triggered crisis protocol
        """
        if not self._available:
            return

        key = self._build_key(session_id)
        history = await self._safe_get(key)

        entry: dict = {
            "role"      : role,
            "content"   : content,
            "category"  : category,
            "confidence": confidence,
            "is_crisis" : is_crisis,
            "timestamp" : time.time(),
        }
        history.append(entry)

        # Enforce the rolling window — remove oldest messages first
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        await self._safe_set(key, history)

    async def clear_session(self, session_id: str) -> None:
        """Delete all memory for a session (e.g. user deletes conversation)."""
        if not self._available:
            return
        try:
            await self._client.delete(self._build_key(session_id))
        except Exception as exc:
            logger.warning(f"[MemoryService] Delete error for {session_id}: {exc}")

    async def ping(self) -> bool:
        """Health-check helper — used by /health endpoint."""
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False


# ── Singleton — initialised once at FastAPI startup (same pattern as embedder) ──
memory_service = MemoryService()
