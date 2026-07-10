# MindBridge AI v1.1 — API Changes

**Status:** Design (pre-implementation)  
**Date:** 2026-07-10

---

## Table of Contents

1. [Change Policy](#1-change-policy)
2. [Existing Endpoints — Unchanged](#2-existing-endpoints--unchanged)
3. [Modified Endpoints](#3-modified-endpoints)
4. [New Endpoints](#4-new-endpoints)
5. [WebSocket Changes](#5-websocket-changes)
6. [Schema Definitions (Pydantic)](#6-schema-definitions-pydantic)
7. [Backward Compatibility Matrix](#7-backward-compatibility-matrix)
8. [Error Codes](#8-error-codes)

---

## 1. Change Policy

v1.1 follows an **additive-only** policy for all REST API changes:

- No endpoints are removed.
- No request fields are removed or made required that were previously optional.
- No response fields are removed.
- New response fields are added as optional (with defaults) so that v1.0 clients safely ignore them.
- New endpoints use new paths that v1.0 clients never call.

**Version header:** v1.1 does not introduce an `/api/v2` prefix. All changes are within `/api/v1`.

---

## 2. Existing Endpoints — Unchanged

The following endpoints have **no changes** to their request or response contracts:

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/v1/auth/register` | POST | Unchanged |
| `/api/v1/auth/login` | POST | Unchanged |
| `/api/v1/auth/refresh` | POST | Unchanged |
| `/api/v1/auth/logout` | POST | Unchanged |
| `/api/v1/chat/sessions` (listing) | GET | Modified — see §3.2 |
| `/api/v1/chat/sessions/{id}/messages` | GET | Modified — see §3.3 |
| `/api/v1/chat/sessions/{id}` | DELETE | Unchanged |
| `/api/v1/mood/log` | POST | Unchanged |
| `/api/v1/mood/history` | GET | Unchanged |
| `/api/v1/mood/stats` | GET | Unchanged |
| `/ws/chat/{session_id}` | WebSocket | Modified — see §5 |

---

## 3. Modified Endpoints

### 3.1 `POST /api/v1/chat/message` 🔒

**Change type:** Additive — new fields added to response.

**Request:** No change.

```json
{
  "message": "I've been feeling really anxious lately.",
  "session_id": "uuid-or-null"
}
```

**Response `200` — v1.0:**
```json
{
  "response": "I hear you...",
  "session_id": "uuid",
  "is_crisis": false,
  "is_relevant": true,
  "relevance_score": 0.68,
  "few_shot_count": 3,
  "predicted_category": "anxiety",
  "classifier_confidence": 0.84,
  "uncertainty": 0.012,
  "memory_used": true
}
```

**Response `200` — v1.1 (new fields highlighted):**
```json
{
  "response": "I hear you — anxiety can feel so exhausting...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_crisis": false,
  "is_relevant": true,
  "relevance_score": 0.68,
  "few_shot_count": 3,
  "predicted_category": "anxiety",
  "classifier_confidence": 0.84,
  "uncertainty": 0.012,
  "memory_used": true,
  "emotion_tag": "fear"
}
```

**New response fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `emotion_tag` | `string \| null` | `null` | Detected user emotion from Ekman 7-class taxonomy. One of: `joy`, `sadness`, `fear`, `anger`, `disgust`, `surprise`, `neutral`. `null` when confidence below threshold or tagger unavailable. |

**Crisis response example (v1.1):**
When `is_crisis=true`, the `predicted_category` may also be `"existential"` for messages that previously triggered false-positive crisis but are now correctly reclassified:

```json
{
  "response": "I hear you, and I'm really glad you reached out...",
  "session_id": "uuid",
  "is_crisis": true,
  "predicted_category": "crisis",
  "emotion_tag": "fear",
  ...
}
```

**Existential response example (new in v1.1):**
```json
{
  "response": "It sounds like you're grappling with some deep questions...",
  "session_id": "uuid",
  "is_crisis": false,
  "predicted_category": "existential",
  "emotion_tag": "sadness",
  "relevance_score": 0.72,
  ...
}
```

---

### 3.2 `GET /api/v1/chat/sessions` 🔒

**Change type:** Additive — new fields added to each session object in the response array.

**Request:** No change.

**Response `200` — v1.0 session object:**
```json
{
  "id": "uuid",
  "title": "I've been feeling really anxious...",
  "message_count": 6,
  "crisis_flagged": false,
  "started_at": "2026-07-10T12:00:00Z"
}
```

**Response `200` — v1.1 session object:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Navigating anxiety at work",
  "title_generated": true,
  "message_count": 24,
  "crisis_flagged": false,
  "session_summary": "The user has been discussing workplace anxiety and feeling overwhelmed by deadlines. They mentioned struggling with sleep and explored some breathing techniques in the later part of the conversation. Progress was noted in identifying specific triggers.",
  "summary_updated_at": "2026-07-10T14:30:00Z",
  "started_at": "2026-07-10T12:00:00Z"
}
```

**New response fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `title_generated` | `bool` | `false` | `true` if the title was AI-generated, `false` if it's the truncated first message fallback |
| `session_summary` | `string \| null` | `null` | AI-generated rolling summary of the conversation. `null` until the session has >= 20 messages and the first summary has been generated. |
| `summary_updated_at` | `datetime \| null` | `null` | ISO 8601 UTC timestamp of the last summary generation. |

---

### 3.3 `GET /api/v1/chat/sessions/{session_id}/messages` 🔒

**Change type:** Additive — new fields added to each message object in the response array.

**Request:** No change.

**Response `200` — v1.0 message object:**
```json
{
  "id": "uuid",
  "role": "user",
  "content": "I feel anxious.",
  "relevance_score": 0.65,
  "is_crisis": false,
  "created_at": "2026-07-10T12:00:00Z"
}
```

**Response `200` — v1.1 message object:**
```json
{
  "id": "uuid",
  "role": "user",
  "content": "I feel so anxious and scared about the exam.",
  "relevance_score": 0.71,
  "is_crisis": false,
  "emotion_tag": "fear",
  "importance_score": 0.75,
  "created_at": "2026-07-10T12:00:00Z"
}
```

**New response fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `emotion_tag` | `string \| null` | `null` | Emotion detected for user messages. Always `null` for assistant messages. |
| `importance_score` | `float` | `0.5` | Heuristic importance score (0.0–1.0). Useful for client-side filtering or highlighting. |

---

### 3.4 `GET /api/v1/users/me` 🔒

**Change type:** Additive — new field added to response.

**Response `200` — v1.1:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "created_at": "2026-07-01T00:00:00Z",
  "memory_ttl_preference": "24h"
}
```

**New response fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `memory_ttl_preference` | `string` | `"24h"` | User's preferred Redis conversation memory TTL. |

---

## 4. New Endpoints

### 4.1 `PATCH /api/v1/users/me` 🔒

**Description:** Update the current user's profile settings. Currently supports `memory_ttl_preference`. Additional fields may be added in future versions without breaking this contract.

**Request:**
```json
{
  "memory_ttl_preference": "72h"
}
```

**Request fields:**

| Field | Type | Required | Allowed Values |
|-------|------|----------|----------------|
| `memory_ttl_preference` | `string` | No | `"24h"`, `"72h"`, `"7d"`, `"session"` |

> All fields are optional. Send only the fields you wish to update. Unknown fields are ignored.

**Response `200`:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "created_at": "2026-07-01T00:00:00Z",
  "memory_ttl_preference": "72h"
}
```

**Errors:**

| Code | Condition |
|------|-----------|
| `422` | `memory_ttl_preference` is not one of the allowed values |
| `401` | Missing or invalid token |

**Example — set 7-day memory TTL:**
```bash
curl -X PATCH https://api.mindbridge.ai/api/v1/users/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"memory_ttl_preference": "7d"}'
```

**Example — set session-only memory (no persistence between sessions):**
```bash
curl -X PATCH https://api.mindbridge.ai/api/v1/users/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"memory_ttl_preference": "session"}'
```

> **Note on `"session"` TTL:** When set to `"session"`, the Redis key still uses a 24h TTL as a safety floor (to handle page refresh / reconnect scenarios). The distinction is semantic: no warm-load from PostgreSQL is performed, so the memory truly starts fresh when the user opens a new session after disconnection.

---

## 5. WebSocket Changes

### `WS /ws/chat/{session_id}`

**Change type:** Additive — new field added to outbound message events.

**Inbound message (client → server):** No change.

**Outbound `message` event — v1.0:**
```json
{
  "type": "message",
  "response": "...",
  "is_crisis": false,
  "is_relevant": true,
  "relevance_score": 0.68,
  "few_shot_count": 3,
  "predicted_category": "anxiety",
  "classifier_confidence": 0.84,
  "memory_used": true
}
```

**Outbound `message` event — v1.1:**
```json
{
  "type": "message",
  "response": "...",
  "is_crisis": false,
  "is_relevant": true,
  "relevance_score": 0.68,
  "few_shot_count": 3,
  "predicted_category": "anxiety",
  "classifier_confidence": 0.84,
  "memory_used": true,
  "emotion_tag": "sadness"
}
```

**New outbound field:**

| Field | Type | Description |
|-------|------|-------------|
| `emotion_tag` | `string \| null` | Detected emotion for this message turn. `null` when unavailable. |

**Other WebSocket event types** (`connected`, `typing`, `error`) are unchanged.

**Internal change:** `chat_ws.py` now calls `memory_service.warm_load()` before the AI pipeline when Redis returns empty history. This is transparent to the WebSocket client.

---

## 6. Schema Definitions (Pydantic)

The following Pydantic schemas require updates. All changes are additive.

### 6.1 `ChatResponse` (chat.py schemas)

```python
class ChatResponse(BaseModel):
    # Core response (unchanged)
    response: str
    session_id: uuid.UUID

    # Safety signals (unchanged)
    is_crisis: bool

    # Relevance / retrieval metadata (unchanged)
    is_relevant: bool
    relevance_score: float
    few_shot_count: int

    # Classifier enrichment (unchanged)
    predicted_category: str | None = None
    classifier_confidence: float = 0.0
    uncertainty: float = 0.0

    # Memory (unchanged)
    memory_used: bool = False

    # NEW in v1.1
    emotion_tag: str | None = None
```

### 6.2 `SessionResponse` (chat.py schemas)

```python
class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    message_count: int
    crisis_flagged: bool
    started_at: datetime

    # NEW in v1.1
    title_generated: bool = False
    session_summary: str | None = None
    summary_updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
```

### 6.3 `MessageResponse` (chat.py schemas)

```python
class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    relevance_score: float | None
    is_crisis: bool
    created_at: datetime

    # NEW in v1.1
    emotion_tag: str | None = None
    importance_score: float = 0.5

    model_config = ConfigDict(from_attributes=True)
```

### 6.4 `UserResponse` (auth.py schemas)

```python
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    created_at: datetime

    # NEW in v1.1
    memory_ttl_preference: str | None = "24h"

    model_config = ConfigDict(from_attributes=True)
```

### 6.5 `UpdateUserRequest` (users.py schemas — NEW)

```python
class UpdateUserRequest(BaseModel):
    memory_ttl_preference: Literal["24h", "72h", "7d", "session"] | None = None

    @field_validator("memory_ttl_preference")
    @classmethod
    def validate_ttl(cls, v: str | None) -> str | None:
        if v is not None and v not in ("24h", "72h", "7d", "session"):
            raise ValueError("memory_ttl_preference must be one of: 24h, 72h, 7d, session")
        return v
```

---

## 7. Backward Compatibility Matrix

| API Consumer | Impact | Action Required |
|-------------|--------|-----------------|
| v1.0 frontend (Next.js) | None — new fields are ignored by React state | None |
| v1.0 API client (any language) | None — additive fields parsed as JSON ignore extras | None |
| e2e_test.py test suite | Minor — `test_enriched_response_fields` list must include `emotion_tag` | Update test to add `"emotion_tag"` to required fields list |
| Existing session list renders | `session_summary` and `title_generated` appear as new fields — UI will simply not render them until frontend is updated | None (ignored) |
| WebSocket clients | New `emotion_tag` field in message events — clients that JSON-parse and access by key will ignore unknown keys | None |

---

## 8. Error Codes

No new error codes are introduced. All existing error codes and their meanings remain unchanged.

**Existing error format:**
```json
{
  "detail": "Human-readable error message"
}
```

**Additional `422` validation cases in v1.1:**

| Endpoint | Field | Condition | Error detail |
|----------|-------|-----------|--------------|
| `PATCH /api/v1/users/me` | `memory_ttl_preference` | Value not in allowlist | `"memory_ttl_preference must be one of: 24h, 72h, 7d, session"` |

---

## Appendix: Full v1.1 Endpoint Catalog

| Endpoint | Method | Auth | Changed | Notes |
|----------|--------|------|---------|-------|
| `/api/v1/auth/register` | POST | No | No | |
| `/api/v1/auth/login` | POST | No | No | |
| `/api/v1/auth/refresh` | POST | No | No | |
| `/api/v1/auth/logout` | POST | No | No | |
| `/api/v1/users/me` | GET | Yes | Yes | +`memory_ttl_preference` |
| `/api/v1/users/me` | PATCH | Yes | **NEW** | Update user settings |
| `/api/v1/chat/message` | POST | Yes | Yes | +`emotion_tag` |
| `/api/v1/chat/sessions` | GET | Yes | Yes | +`title_generated`, `session_summary`, `summary_updated_at` |
| `/api/v1/chat/sessions/{id}/messages` | GET | Yes | Yes | +`emotion_tag`, `importance_score` per message |
| `/api/v1/chat/sessions/{id}` | DELETE | Yes | No | |
| `/api/v1/mood/log` | POST | Yes | No | |
| `/api/v1/mood/history` | GET | Yes | No | |
| `/api/v1/mood/stats` | GET | Yes | No | |
| `/ws/chat/{session_id}` | WebSocket | Yes (token) | Yes | +`emotion_tag` in message events |
| `/health` | GET | No | Yes | +`emotion_tagger_loaded`, `existential_anchors_loaded`, `memory_warm_load_enabled` |
