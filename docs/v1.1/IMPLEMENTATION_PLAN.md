# MindBridge AI v1.1 — Implementation Plan

**Status:** Design (pre-implementation)  
**Date:** 2026-07-10  
**Estimated duration:** 5 milestones, ~6–8 weeks

---

## Overview

v1.1 is decomposed into **5 milestones**. Each milestone is independently testable, deployable to staging, and can be released separately if needed. Later milestones depend on earlier ones only as noted.

The milestones are ordered to deliver safety-critical changes (M1: existential guard, M2: memory) before quality improvements (M3: emotion, M4: summaries/titles) and infrastructure (M5: testing).

| Milestone | Theme | Features | Dependencies |
|-----------|-------|----------|-------------|
| M1 | Crisis Safety | FR-05 Existential vs. Crisis | None |
| M2 | Memory Foundation | FR-07 Memory Persistence | None |
| M3 | Emotional Intelligence | FR-01 Emotion Tagging, FR-02 Importance Scoring, FR-03 Emotion-Aware Retrieval | M2 (Redis schema) |
| M4 | Session Intelligence | FR-04 Rolling Summaries, FR-06 AI Titles | M3 (DB migration) |
| M5 | Test Infrastructure | FR-08 Better Testing | M1–M4 (all features complete) |

---

## Milestone 1 — Crisis Safety (FR-05)

**Goal:** Reduce false-positive crisis triggers for existential/philosophical statements. **Safety-critical. Must be completed and validated before any other milestone ships to production.**

**Duration:** 1 week

### Tasks

#### 1.1 Existential Anchor Preparation
- [ ] Define the 10 existential anchor phrases (see FR-05 spec)
- [ ] Add anchor list as a constant in `crisis_service.py`
- [ ] Write a standalone script `scripts/validate_existential_anchors.py` that:
  - Embeds each anchor phrase
  - Computes cosine similarity against the crisis corpus embeddings
  - Prints the similarity matrix — expected: anchors should score 0.55–0.75 (near but below the 0.70 crisis threshold)
  - Run this script and review output before proceeding

#### 1.2 `embedder.py` — Existential Embedding Support
- [ ] Add `existential_embeddings: np.ndarray | None` attribute
- [ ] Add `EXISTENTIAL_PHRASES` constant list (10 phrases)
- [ ] In `load_corpus()`: pre-compute and store `existential_embeddings` from `EXISTENTIAL_PHRASES` (same pattern as `crisis_embeddings`)
- [ ] Modify `check_crisis_embedding()` to return `tuple[bool, bool]` instead of `bool`
  - Signature: `check_crisis_embedding(query_vec) -> (is_crisis: bool, is_existential: bool)`
  - Add `EXISTENTIAL_MARGIN = 0.08` constant
  - Implement the disambiguation algorithm (see ARCHITECTURE.md §9)

#### 1.3 `ai_service.py` — Pipeline Update
- [ ] Update Step 4 to unpack the new tuple return value:
  ```python
  embedding_crisis, is_existential = embedder.check_crisis_embedding(query_vec)
  ```
- [ ] If `not final_is_crisis and is_existential`: set `predicted_category = "existential"`
- [ ] Add `EXISTENTIAL_RESPONSE_HINT` constant string
- [ ] In Step 6 (Build Prompt): inject `EXISTENTIAL_RESPONSE_HINT` when `is_existential=True` (not when `is_crisis=True`)

#### 1.4 `config.py` — New Constants
- [ ] Add `EXISTENTIAL_MARGIN: float = 0.08`

#### 1.5 `main.py` — Health Endpoint
- [ ] Add `existential_anchors_loaded` to the `/health` response (check `embedder.existential_embeddings is not None`)

#### 1.6 Validation Script (manual, pre-merge)
- [ ] Run: 10 existential phrases → all must return `is_crisis=False`
- [ ] Run: 10 known crisis phrases → all must return `is_crisis=True`
- [ ] Confirm keyword layer still catches "I want to die" regardless of existential similarity

**Definition of Done:**
- All above tasks complete
- Existential phrases return `is_crisis=False`, `predicted_category="existential"`
- Genuine crisis phrases return `is_crisis=True` (keyword and embedding layers unaffected)
- `/health` reports `existential_anchors_loaded: true`
- Reviewed in code review and approved

---

## Milestone 2 — Memory Foundation (FR-07)

**Goal:** Extend the Redis memory schema, add warm-load capability, and expose user-configurable TTL. This is the foundation for M3.

**Duration:** 1 week

### Tasks

#### 2.1 Database Migration
- [ ] Create `backend/migrations/versions/002_v1_1_emotional_memory.py`
  - Add `messages.emotion_tag` (VARCHAR 20, nullable)
  - Add `messages.importance_score` (FLOAT, NOT NULL DEFAULT 0.5)
  - Add `chat_sessions.title_generated` (BOOLEAN, NOT NULL DEFAULT false)
  - Add `chat_sessions.session_summary` (TEXT, nullable)
  - Add `chat_sessions.summary_updated_at` (TIMESTAMPTZ, nullable)
  - Add `users.memory_ttl_preference` (VARCHAR 20, nullable, default '24h')
  - Add all check constraints (see DATABASE_CHANGES.md §3)
- [ ] Run migration on local dev database: `alembic upgrade 002`
- [ ] Verify migration is reversible: `alembic downgrade 001`, then `alembic upgrade 002`

#### 2.2 SQLAlchemy Models
- [ ] `models/message.py`: Add `emotion_tag`, `importance_score` columns
- [ ] `models/session.py`: Add `title_generated`, `session_summary`, `summary_updated_at` columns
- [ ] `models/user.py`: Add `memory_ttl_preference` column

#### 2.3 `memory_service.py` — Extended Redis Schema
- [ ] Update `append_message()` and `append_turn()` to accept and store `emotion_tag` and `importance_score`
- [ ] Update `get_history()` to return `emotion_tag` and `importance_score` with graceful defaults for old entries (use `.get()` with defaults)

#### 2.4 `memory_service.py` — `warm_load()` Method
- [ ] Implement `warm_load(session_id: str, messages: list[dict]) -> None`
  - Accept list of `{"role", "content"}` dicts (from PostgreSQL `session_history`)
  - Build Redis entries with `emotion_tag=null`, `importance_score=0.5`, `is_crisis=False`
  - Cap at `MAX_HISTORY` most recent messages
  - Write as a single Redis pipeline: RPUSH × n + LTRIM + EXPIRE
  - No-op if `messages` is empty or Redis unavailable

#### 2.5 `chat.py` — Call `warm_load()`
- [ ] After fetching Redis history: if result is empty AND `session_history` is non-empty → call `warm_load()`

#### 2.6 `chat_ws.py` — Call `warm_load()`
- [ ] Same warm-load logic as `chat.py` (after fallback history load)

#### 2.7 User Memory TTL Endpoint
- [ ] `schemas/user.py` — add `UpdateUserRequest` schema (see API_CHANGES.md §6.5)
- [ ] `api/v1/users.py` — add `PATCH /api/v1/users/me` endpoint
  - Validate `memory_ttl_preference` against allowlist
  - UPDATE user record
  - Return updated `UserResponse`
- [ ] Update `UserResponse` schema to include `memory_ttl_preference`
- [ ] Update `memory_service.append_turn()` to accept `ttl_seconds: int` parameter
- [ ] In `chat.py`: fetch user's `memory_ttl_preference` and convert to seconds before calling `append_turn()`
- [ ] TTL conversion table: `{"24h": 86400, "72h": 259200, "7d": 604800, "session": 86400}`
  - Note: `"session"` uses 24h as safety floor

#### 2.8 Health Endpoint
- [ ] Add `memory_warm_load_enabled: true` to `/health` response

**Definition of Done:**
- Migration 002 applied, reversible
- `warm_load()` tested manually: simulate Redis TTL expiry, verify warm-load works
- `PATCH /api/v1/users/me` returns 200 with valid TTL, 422 with invalid TTL
- Redis entries include `emotion_tag` (null) and `importance_score` (0.5 default)
- All v1.0 read paths unaffected (new fields have defaults)

---

## Milestone 3 — Emotional Intelligence (FR-01, FR-02, FR-03)

**Goal:** Add emotion tagging to the pipeline, compute importance scores, and enable emotion-aware retrieval. Depends on M2 (Redis and DB schema ready).

**Duration:** 1.5 weeks

### Tasks

#### 3.1 `emotion_tagger.py` — New Service
- [ ] Create `backend/app/services/emotion_tagger.py`
- [ ] Define `EMOTION_ANCHORS: dict[str, str]` — 7 emotion → anchor phrase
- [ ] Implement `EmotionTagger` class:
  - `anchor_embeddings: dict[str, np.ndarray] | None`
  - `THRESHOLD: float = 0.30`
  - `initialize(model: SentenceTransformer) -> None` — encode all 7 anchors
  - `tag(query_vec: np.ndarray) -> tuple[str | None, float]`
- [ ] Create module-level singleton: `emotion_tagger = EmotionTagger()`

#### 3.2 `main.py` — Initialize EmotionTagger
- [ ] Import `emotion_tagger` singleton
- [ ] In lifespan: `emotion_tagger.initialize(embedder.model)` after `embedder.initialize()`
- [ ] Wrap in try/except (non-fatal)
- [ ] Add `emotion_tagger_loaded` to `/health` response

#### 3.3 `importance_scorer.py` — New Utility
- [ ] Create `backend/app/services/importance_scorer.py`
- [ ] Implement `compute_importance_score(content, is_crisis, classifier_confidence, relevance_score) -> float`
- [ ] Implement `is_filler(content) -> bool` — checks word count <= 2
- [ ] No state, no imports beyond stdlib — pure functions

#### 3.4 `ai_service.py` — Pipeline Integration
- [ ] Import `emotion_tagger` and `compute_importance_score`
- [ ] Add Step 3.6 (Emotion Tag):
  ```python
  emotion_tag, emotion_confidence = emotion_tagger.tag(query_vec)
  ```
- [ ] In Step 6 (Build Prompt): inject emotion hint when `emotion_tag is not None and not final_is_crisis`
- [ ] In Step 8 (Persist to Redis):
  - Compute `importance_score = compute_importance_score(user_message, final_is_crisis, classifier_confidence, relevance_score)`
  - Pass `emotion_tag` and `importance_score` to `memory_service.append_turn()`
- [ ] Update Step 9 (Return): add `emotion_tag` to returned dict

#### 3.5 `chat.py` — Persist emotion_tag + importance_score to PostgreSQL
- [ ] Pass `emotion_tag=ai_result.get("emotion_tag")` when creating the user `Message` ORM object
- [ ] Pass `importance_score=ai_result.get("importance_score", 0.5)` when creating both user and AI `Message` ORM objects

#### 3.6 `chat_ws.py` — WebSocket emotion_tag
- [ ] Pass `emotion_tag` from `ai_result` to WebSocket outbound message event

#### 3.7 Pydantic Schema Updates
- [ ] `ChatResponse`: add `emotion_tag: str | None = None`
- [ ] `MessageResponse`: add `emotion_tag: str | None = None`, `importance_score: float = 0.5`

#### 3.8 `memory_service.py` — Importance-Aware Trim (FR-02)
- [ ] Implement `trim_by_importance(session_id: str) -> None`
  - LRANGE the full list
  - If any entry outside the `HISTORY_FOR_LLM` window has `importance_score < IMPORTANCE_EVICT_THRESHOLD (0.20)`:
    - Find lowest-scoring evict candidate
    - Remove it using LREM + rebuild (or use a sorted set approach if implementation is complex)
  - Never evict entries with `importance_score >= IMPORTANCE_PIN_THRESHOLD (0.80)`
- [ ] Call `trim_by_importance()` after every `append_turn()` when `_available=True`

#### 3.9 `embedder.py` — Emotion-Aware Retrieval (FR-03)
- [ ] Add `EMOTION_BONUS = 0.15` and `VALENCE_BONUS = 0.05` constants
- [ ] Add `EMOTION_VALENCE: dict[str, str]` mapping (e.g., `{"joy": "positive", "sadness": "negative", ...}`)
- [ ] Implement `get_few_shot_examples_by_category_and_emotion(query_vec, category, emotion_tag) -> list[dict]`
  - Call existing method with `top_k = TOP_K * 2` for larger candidate pool
  - Re-rank by emotion alignment (see ARCHITECTURE.md §8)
  - Return top `TOP_K`
- [ ] Update `ai_service.py` Step 5 to call new method when `emotion_tag is not None`

**Definition of Done:**
- `POST /api/v1/chat/message` returns `emotion_tag` field in response
- Messages with "I feel so scared" return `emotion_tag = "fear"` (or similar)
- Messages with "okay" return `emotion_tag = null`
- `messages.emotion_tag` and `messages.importance_score` are populated in PostgreSQL
- Redis entries include `emotion_tag` and `importance_score`
- `/health` reports `emotion_tagger_loaded: true`

---

## Milestone 4 — Session Intelligence (FR-04, FR-06)

**Goal:** Add rolling conversation summaries and AI-generated session titles. These are background tasks — zero user-facing latency impact. Depends on M2 (DB migration).

**Duration:** 1 week

### Tasks

#### 4.1 `summary_service.py` — New Service
- [ ] Create `backend/app/services/summary_service.py`
- [ ] Define `SUMMARY_PROMPT` constant (see FR-04 spec)
- [ ] Define `SUMMARY_TRIGGER_EVERY = 20` (read from config)
- [ ] Implement `maybe_generate_summary(session_id, message_count, db_session_factory) -> None`:
  - Early return if `message_count % SUMMARY_TRIGGER_EVERY != 0`
  - Open fresh DB session (use `AsyncSessionLocal`)
  - SELECT last 40 messages ordered by `created_at` for this session
  - Build message transcript string for prompt
  - Call Gemini with `_gemini_model.generate_content(summary_messages)`
  - UPDATE `chat_sessions` SET `session_summary=...`, `summary_updated_at=now()`
  - All exceptions caught and logged at WARNING level

#### 4.2 `title_service.py` — New Service
- [ ] Create `backend/app/services/title_service.py`
- [ ] Define `TITLE_PROMPT` constant (see FR-06 spec)
- [ ] Implement `maybe_generate_title(session_id, first_user_msg, first_ai_resp, is_crisis, db_session_factory) -> None`:
  - If `is_crisis=True`: return immediately (use fallback title)
  - Open fresh DB session
  - Check `title_generated` flag — if already True, return (idempotency guard)
  - Call Gemini with title prompt
  - Validate word count: 4–10 words
  - On success: UPDATE `chat_sessions` SET `title=generated_title`, `title_generated=true`
  - On failure: UPDATE `chat_sessions` SET `title=fallback_title`, `title_generated=false`

#### 4.3 `chat.py` — Wire Background Tasks
- [ ] Import `summary_service` and `title_service`
- [ ] After PostgreSQL writes and session update: fire two background tasks
  ```python
  import asyncio
  asyncio.create_task(
      title_service.maybe_generate_title(
          session_id=session.id,
          first_user_msg=data.message,
          first_ai_resp=ai_result["response"],
          is_crisis=ai_result["is_crisis"],
          db_session_factory=AsyncSessionLocal,
      )
  )
  asyncio.create_task(
      summary_service.maybe_generate_summary(
          session_id=session.id,
          message_count=new_message_count,  # after increment
          db_session_factory=AsyncSessionLocal,
      )
  )
  ```
- [ ] Do NOT await these tasks — fire and forget

#### 4.4 `ai_service.py` — Inject Session Summary into Prompt
- [ ] Modify `process_message()` signature to accept `session_summary: str | None = None`
- [ ] In Step 6 (Build Prompt): prepend summary to dynamic system prompt when non-null
  ```python
  if session_summary:
      dynamic_system_prompt = f"[Previous session context: {session_summary}]\n\n" + dynamic_system_prompt
  ```

#### 4.5 `chat.py` — Pass session_summary to ai_service
- [ ] Fetch `session.session_summary` before calling `process_message()`
- [ ] Pass `session_summary=session.session_summary` to `process_message()`

#### 4.6 Pydantic Schema Updates
- [ ] `SessionResponse`: add `title_generated: bool = False`, `session_summary: str | None = None`, `summary_updated_at: datetime | None = None`

**Definition of Done:**
- Send 21 messages to a session; after the 20th, wait 5 seconds and check `session_summary` is non-null
- First message of a new session: within 3 seconds, `title_generated=true` and title is descriptive
- Crisis first message: `title_generated=false`, title is truncated first message
- All background task failures are silent (no 500 errors for users)

---

## Milestone 5 — Test Infrastructure (FR-08)

**Goal:** Restructure and expand the test suite. All new features from M1–M4 must have test coverage.

**Duration:** 1.5 weeks

### Tasks

#### 5.1 Directory Structure
- [ ] Create `backend/tests/unit/` directory with `__init__.py`
- [ ] Create `backend/tests/integration/` directory with `__init__.py`
- [ ] Create `backend/tests/regression/` directory with `__init__.py`
- [ ] Create `backend/tests/performance/` directory with `__init__.py`
- [ ] Move `test_ai_pipeline.py` into `tests/unit/test_embedder.py` (rename and update)

#### 5.2 `requirements.txt` — Test Dependencies
- [ ] Add `pytest-mock>=3.14.0`
- [ ] Add `fakeredis[aioredis]>=2.23.0`
- [ ] Add `pytest-cov>=5.0.0`
- [ ] Add `pytest-benchmark>=4.0.0`

#### 5.3 `conftest.py` — Fixture Updates
- [ ] Load `TEST_EMAIL` and `TEST_PASS` from environment variables (not hardcoded)
- [ ] Add `fake_redis` fixture using `fakeredis.aioredis.FakeRedis`
- [ ] Add `mock_gemini` fixture that patches `_gemini_model.generate_content` to return a fixed string
- [ ] Add `mock_embedder` fixture (already initialized)

#### 5.4 Unit Tests — `tests/unit/`

**`test_crisis_service.py`:**
- [ ] `test_keyword_detection_positive()` — all CRISIS_KEYWORDS variants
- [ ] `test_keyword_detection_negative()` — false positive guard phrases
- [ ] `test_existential_not_crisis()` — 10 existential phrases return `(False, True)`
- [ ] `test_genuine_crisis_embedding()` — known crisis phrases return `(True, False)`

**`test_emotion_tagger.py`:**
- [ ] `test_all_7_emotions_detected()` — each anchor phrase returns its own emotion
- [ ] `test_short_message_returns_null()` — 1-word messages return `(None, score)`
- [ ] `test_threshold_fallback()` — off-topic text returns `None`

**`test_importance_scorer.py`:**
- [ ] `test_crisis_message_score()` — crisis=True → score >= 0.90
- [ ] `test_filler_score()` — "okay", "yes" → score <= 0.20
- [ ] `test_high_confidence_long_message()` — conf>=0.80, len>20 words → score > 0.60
- [ ] `test_score_clamped_to_1()` — score never exceeds 1.0

**`test_memory_service.py`:**
- [ ] `test_append_and_get_history()` — using fakeredis
- [ ] `test_warm_load()` — verify Redis is populated after warm_load
- [ ] `test_warm_load_empty_noop()` — warm_load with empty list does nothing
- [ ] `test_warm_load_caps_at_max_history()` — 30 messages → only 20 stored
- [ ] `test_append_turn_includes_emotion_and_importance()`
- [ ] `test_redis_unavailable_graceful_degradation()`

**`test_embedder.py`:**
- [ ] `test_relevance_check_positive()` — mental health queries
- [ ] `test_relevance_check_negative()` — off-topic queries
- [ ] `test_crisis_embedding_detection()`
- [ ] `test_existential_not_crisis()`
- [ ] `test_few_shot_retrieved_count()`
- [ ] `test_emotion_aware_retrieval_boost()` — matching emotion tag scores higher

**`test_ai_pipeline.py`:**
- [ ] Mock all external dependencies (Gemini, Redis)
- [ ] `test_process_message_returns_emotion_tag()`
- [ ] `test_crisis_message_short_circuits()`
- [ ] `test_existential_message_not_crisis()`
- [ ] `test_empty_message_returns_early()`
- [ ] `test_session_summary_injected_into_prompt()`

#### 5.5 Regression Tests — `tests/regression/`

**`test_crisis_regression.py`:**
- [ ] List of 20+ crisis phrases, each must return `is_crisis=True`
- [ ] Use `embedder` singleton (no mocking — real behavior)

**`test_existential_regression.py`:**
- [ ] List of 10 existential phrases, each must return `is_crisis=False, is_existential=True`

**`test_false_positive_guard.py`:**
- [ ] The 6 existing short messages from `e2e_test.py` must return `is_crisis=False`
- [ ] Additional 10 non-crisis short messages

#### 5.6 Integration Tests — `tests/integration/`

**`test_session_title.py`:**
- [ ] Send first message → poll `GET /sessions` for up to 5s → assert `title_generated=true`
- [ ] Crisis first message → assert `title_generated=false`

**`test_session_summary.py`:**
- [ ] Helper to send N messages to a session
- [ ] Send 21 messages → poll `GET /sessions` for up to 10s → assert `session_summary` is not null

#### 5.7 Performance Tests — `tests/performance/`

**`test_pipeline_latency.py`:**
- [ ] Benchmark `embedder.embed()` + `classifier_service.predict()` + `emotion_tagger.tag()` + `embedder.get_few_shot_examples_by_category_and_emotion()`
- [ ] Assert p95 < 200ms
- [ ] Use `pytest-benchmark` fixture

#### 5.8 CI Configuration
- [ ] Update `.github/workflows/` (or create `ci.yml` if none exists):
  - `pytest tests/unit/ --cov=app --cov-fail-under=80`
  - `pytest tests/regression/`
  - `pytest tests/performance/`
  - Integration tests run only when `RUN_INTEGRATION=true` env var is set (requires live services)

**Definition of Done:**
- `pytest tests/unit/ -v` passes with 0 failures
- `pytest tests/regression/ -v` passes with 0 failures
- `pytest tests/performance/ -v` passes with p95 < 200ms
- Coverage report: `app/services/` >= 80% line coverage

---

## Cross-Milestone Dependencies

```
M1 (Existential Guard)
  └─ embedder.check_crisis_embedding() signature changes
  └─ Required before M3 (ai_service.py integration)

M2 (Memory Foundation)
  └─ Database migration (schema ready)
  └─ warm_load() method
  └─ Required before M3 (Redis schema for emotion_tag/importance_score)
  └─ Required before M4 (DB columns for session_summary, title_generated)

M3 (Emotional Intelligence)
  └─ Requires M1 (ai_service.py already updated)
  └─ Requires M2 (Redis schema ready, migration applied)

M4 (Session Intelligence)
  └─ Requires M2 (DB migration applied)
  └─ Can be developed in parallel with M3

M5 (Testing)
  └─ Requires M1-M4 (all features complete for full regression coverage)
  └─ Unit tests for individual services CAN be written in parallel with M1-M4
```

---

## File Change Summary

| File | Change Type | Milestone |
|------|-------------|-----------|
| `app/services/embedder.py` | Modify | M1, M3 |
| `app/services/crisis_service.py` | Modify | M1 |
| `app/services/ai_service.py` | Modify | M1, M3, M4 |
| `app/services/memory_service.py` | Modify | M2, M3 |
| `app/services/auth_service.py` | No change | — |
| `app/services/classifier_service.py` | No change | — |
| `app/services/classifier.py` | No change | — |
| `app/services/emotion_tagger.py` | **New file** | M3 |
| `app/services/importance_scorer.py` | **New file** | M3 |
| `app/services/summary_service.py` | **New file** | M4 |
| `app/services/title_service.py` | **New file** | M4 |
| `app/models/message.py` | Modify | M2 |
| `app/models/session.py` | Modify | M2 |
| `app/models/user.py` | Modify | M2 |
| `app/models/__init__.py` | No change | — |
| `app/schemas/chat.py` | Modify | M3, M4 |
| `app/schemas/user.py` | Modify | M2 |
| `app/api/v1/chat.py` | Modify | M2, M3, M4 |
| `app/api/v1/users.py` | Modify | M2 |
| `app/api/v1/auth.py` | No change | — |
| `app/api/v1/mood.py` | No change | — |
| `app/api/v1/router.py` | No change | — |
| `app/ws/chat_ws.py` | Modify | M2, M3 |
| `app/main.py` | Modify | M1, M3 |
| `app/config.py` | Modify | M1, M2 |
| `app/database.py` | No change | — |
| `app/dependencies.py` | No change | — |
| `migrations/versions/002_*.py` | **New file** | M2 |
| `migrations/versions/003_*.py` | **New file** | M2 |
| `tests/conftest.py` | Modify | M5 |
| `tests/unit/` (7 files) | **New directory** | M5 |
| `tests/integration/` (5 files) | **New directory** | M5 |
| `tests/regression/` (3 files) | **New directory** | M5 |
| `tests/performance/` (1 file) | **New directory** | M5 |
| `requirements.txt` | Modify | M5 |

---

## Risk Registry

| Risk | Milestone | Probability | Mitigation |
|------|-----------|-------------|------------|
| Existential margin miscalibrated — genuine crisis missed | M1 | Low | Keyword layer unaffected; validate with 20+ crisis phrases before ship |
| Gemini API changes break title/summary generation | M4 | Low | Both services have fallback paths; errors are non-fatal |
| fakeredis behavior differs from real Redis in edge cases | M5 | Medium | Keep e2e_test.py as integration test against real Redis |
| warm_load() causing extra DB load at scale | M2 | Medium | Only fires on Redis miss with PG history present; monitor in staging |
| Background tasks not awaited → exceptions silently lost | M4 | Low | Wrap task bodies in try/except with structured logging |
| Coverage target (80%) not achievable with mocked dependencies | M5 | Low | Mock only external I/O (Gemini, Redis); test service logic with real implementations |

---

## Pre-Release Checklist

Before merging any milestone to main:
- [ ] All automated tests pass
- [ ] Code review approved
- [ ] Staging deployment verified
- [ ] `/health` endpoint shows all expected flags
- [ ] Manual smoke test: send 3-turn conversation, verify `emotion_tag`, `memory_used`, and `session_id` continuity
- [ ] For M1 specifically: confirm safety net with crisis keyword phrases on staging
