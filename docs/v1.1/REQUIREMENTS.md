# MindBridge AI v1.1 — Requirements Specification

**Theme: Intelligent Memory & Emotional Intelligence**  
**Status:** Design (pre-implementation)  
**Authors:** MindBridge Engineering  
**Date:** 2026-07-10  
**Supersedes:** v1.0 initial release

---

## Table of Contents

1. [FR-01 Emotion Tagging](#fr-01-emotion-tagging)
2. [FR-02 Memory Importance Scoring](#fr-02-memory-importance-scoring)
3. [FR-03 Emotion-Aware Retrieval](#fr-03-emotion-aware-retrieval)
4. [FR-04 Rolling Conversation Summaries](#fr-04-rolling-conversation-summaries)
5. [FR-05 Improved Existential vs. Crisis Distinction](#fr-05-improved-existential-vs-crisis-distinction)
6. [FR-06 AI-Generated Session Titles](#fr-06-ai-generated-session-titles)
7. [FR-07 Memory Persistence Improvements](#fr-07-memory-persistence-improvements)
8. [FR-08 Better Testing](#fr-08-better-testing)

---

## FR-01 Emotion Tagging

### Problem
The v1.0 system classifies messages into 10 broad mental health categories (anxiety, depression, stress, etc.) using a trained PyTorch classifier. However, **no granular emotional state** is captured at the message level. The classifier output — `predicted_category` — describes the *topic* of a conversation, not the user's *present emotional state*.

This means two messages like "I'm so angry at myself for failing" and "I feel hopeless because I keep failing" both land in the same bucket, yet they carry meaningfully different emotional valence, arousal level, and therapeutic response needs.

### Current Limitation
- `Message` model has no emotion field.
- Redis memory schema (`mb:memory:{session_id}`) stores only `role`, `content`, `category`, `confidence`, `is_crisis`, and `timestamp`.
- The LLM prompt is not conditioned on the user's detected emotional state — it only receives the raw message history.
- Downstream analytics (mood correlation, trend detection) cannot distinguish emotional quality within a category.

### Proposed Solution
Introduce a lightweight, deterministic **emotion tagger** that runs in the AI pipeline immediately after Step 2 (Embed). The tagger maps the 384-dim MiniLM embedding to one of a fixed set of **primary emotions** using a rule-based cosine similarity approach against anchor emotion vectors, rather than training a new model (to minimize deployment risk).

**Emotion taxonomy (7 primary emotions, aligned with Ekman's model):**
- `joy`, `sadness`, `fear`, `anger`, `disgust`, `surprise`, `neutral`

A second dimension captures **valence** (positive / negative / ambiguous) and **arousal** (high / low). These are derived from the primary emotion mapping rather than independently predicted.

The detected emotion tag is:
1. Stored on the `Message` database row (new `emotion_tag` column, nullable `VARCHAR(20)`).
2. Stored in the Redis memory entry (new `emotion_tag` field).
3. Returned in the API response (new `emotion_tag` field on `ChatResponse`).
4. Injected into the Gemini prompt as a one-line prefix: `"[Detected user emotion: SADNESS — LOW AROUSAL]"`.

### Acceptance Criteria
- [ ] `POST /api/v1/chat/message` response includes `emotion_tag: string | null`.
- [ ] `emotion_tag` is stored in both the `messages` PostgreSQL table and the Redis memory entry for every user message.
- [ ] The Gemini prompt includes the detected emotion when the tagger returns a non-null result.
- [ ] Emotion tagger returns a result within 5 ms (measured as additional latency on top of the existing embed step — it reuses the same embedding vector, so no extra model call is needed).
- [ ] If the emotion tagger fails for any reason, the pipeline continues without it (`emotion_tag = null`) — no user-facing degradation.
- [ ] Unit tests cover all 7 emotion anchors and the `neutral` fallback case.
- [ ] The `/health` endpoint reports `emotion_tagger_loaded: true`.

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Cosine-anchor approach may mis-tag mixed-emotion messages | Medium | Low | Use neutral fallback for low-confidence tags (< 0.30 similarity to any anchor) |
| Adding emotion to prompt may slightly alter Gemini response style | Low | Low | A/B test prompt variants in staging before release |
| MiniLM embeddings not optimal for fine-grained emotion detection | Medium | Low | Accuracy is acceptable at this stage; full fine-tuned emotion model deferred to v2.0 |

### Edge Cases
- **Ambiguous message** ("I don't know"): similarity below threshold → `emotion_tag = null`.
- **Crisis message**: emotion tagger runs but result is not injected into prompt (crisis response is static).
- **Empty or very short message** (< 4 words): tagger returns `null` rather than guessing.
- **Mixed emotions** ("happy but also scared"): highest-similarity anchor wins; no multi-label emotion in v1.1.
- **Non-English input**: MiniLM handles some multilingual content; emotion anchor vectors may be less accurate — graceful degradation to `null`.

---

## FR-02 Memory Importance Scoring

### Problem
The v1.0 memory engine stores the last 20 messages in a simple Redis FIFO list (`RPUSH` + `LTRIM`). All messages are treated as equally important. When the 20-message window fills up, early messages are silently discarded regardless of whether they contained **high-value context** (crisis mention, core disclosure, stated goals) or **low-value filler** (greetings, single-word acknowledgements like "okay", "yes").

This means the LLM can lose critical early disclosures while retaining filler turns that contribute nothing to response quality.

### Current Limitation
- `append_turn()` in `memory_service.py` uses a dumb FIFO strategy.
- No mechanism to prevent important messages from being evicted.
- `MAX_HISTORY = 20` and `HISTORY_FOR_LLM = 12` are hardcoded constants with no awareness of content significance.

### Proposed Solution
Assign an **importance score** (float 0.0–1.0) to every stored memory entry. The score is computed deterministically at write time using a weighted combination of signals already available in the pipeline:

| Signal | Weight | Rationale |
|--------|--------|-----------|
| `is_crisis = True` | +0.90 (floor) | Crisis disclosures are always critical |
| `classifier_confidence >= 0.80` | +0.30 | High-confidence category = semantically rich |
| word count > 20 | +0.20 | Longer messages carry more context |
| `relevance_score >= 0.70` | +0.15 | Highly relevant to mental health topics |
| Contains first-person disclosure ("I feel", "I am", "my") | +0.10 | Personal disclosures are high-value |
| Greeting / single-word / filler | -0.40 (floor penalty) | Discard candidates |

Score is capped at [0.0, 1.0].

**Retention strategy:** When eviction occurs (list > `MAX_HISTORY`), LTRIM removes oldest-first by default. The importance score is stored alongside the message in Redis. A new `trim_by_importance()` method will, on every write, scan the in-memory list and drop the *lowest-importance* message that falls outside the `HISTORY_FOR_LLM` active window if any message scores below 0.20. Messages with score >= 0.80 are pinned and never evicted within the TTL window.

The importance score is also stored in the `messages` PostgreSQL table (`importance_score FLOAT DEFAULT 0.5`) for analytics.

### Acceptance Criteria
- [ ] Every Redis memory entry includes `importance_score: float`.
- [ ] Every `Message` row includes `importance_score FLOAT`.
- [ ] Crisis messages always have `importance_score >= 0.90`.
- [ ] Filler messages (single-word, < 3 tokens) have `importance_score <= 0.20`.
- [ ] `trim_by_importance()` never evicts messages with `importance_score >= 0.80` within the TTL window.
- [ ] Pipeline latency increase for importance scoring is < 2 ms.
- [ ] Unit tests validate scoring formula for a representative set of message types.

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Scoring heuristics may be wrong for edge cases | Medium | Low | Start conservative; importance score is advisory, not used for crisis decisions |
| trim_by_importance scan adds Redis read on every write | Low | Medium | Only perform scan when list length >= MAX_HISTORY (amortized O(1) in practice) |

### Edge Cases
- **All messages have high importance**: FIFO fallback applies; no messages are artificially evicted.
- **All messages are filler**: FIFO applies normally; no change from v1.0 behavior.
- **Redis unavailable**: importance scoring is computed but not persisted; no degradation.

---

## FR-03 Emotion-Aware Retrieval

### Problem
The v1.0 few-shot retrieval system (`get_few_shot_examples_by_category`) selects corpus examples based on:
1. The classifier-predicted *topic category* (e.g., "anxiety").
2. Cosine similarity of the user's message embedding to corpus item embeddings.

This retrieves examples that are *topically* similar but **emotionally mismatched**. A user expressing anger about a situation receives the same pool of "anxiety" examples as a user who is quietly worried — even though these call for very different tonal responses.

### Current Limitation
- `embedder.get_few_shot_examples_by_category()` is the only retrieval strategy.
- No emotion dimension is considered in retrieval ranking.
- Corpus JSON entries have no emotion annotation.

### Proposed Solution
Extend the retrieval pipeline to incorporate the emotion tag from FR-01 as a **secondary filter** applied after category selection.

**Two-stage retrieval:**
1. **Stage 1 (existing):** Category-restricted or full-corpus cosine similarity, returning top-K*2 candidates (double the usual pool).
2. **Stage 2 (new):** Re-rank the candidate pool by adding an **emotion alignment bonus** to each candidate's cosine similarity score:
   - If the candidate's corpus entry has the same `emotion_tag` as the detected user emotion: +0.15 bonus.
   - If valence matches (positive/negative): +0.05 bonus.
   - Final ranking: `adjusted_score = cosine_similarity + emotion_bonus`.
   - Return top-K from the re-ranked pool.

**Corpus extension:** Add an optional `emotion_tag` field to each corpus JSON entry. Entries without this field behave as before (no bonus, no penalty). Corpus enrichment is a data task, not a code change — it can be done incrementally.

**New method:** `get_few_shot_examples_by_category_and_emotion(query_vec, category, emotion_tag)` in `embedder.py`. Old method is preserved for backward compatibility.

### Acceptance Criteria
- [ ] New retrieval method implemented and called from `ai_service.py` when `emotion_tag` is not null.
- [ ] Falls back to `get_few_shot_examples_by_category` when `emotion_tag` is null.
- [ ] Corpus JSON schema updated to support optional `emotion_tag` field.
- [ ] At least 10% of existing corpus entries annotated with emotion tags for the initial release (full annotation is a data milestone, not a code gate).
- [ ] Unit tests confirm that corpus entries with matching emotion tag score higher than equivalent entries without tag when emotion is detected.
- [ ] No regression in response quality for unannotated corpus entries (measured manually on 20 test conversations).

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Sparse corpus emotion annotation undermines benefit | High | Low | Feature degrades gracefully — no annotation = no bonus |
| Emotion misdetection leads to mismatched examples | Medium | Low | Secondary signal only; cosine similarity is still primary |

### Edge Cases
- **No annotated corpus entries for detected emotion**: re-ranking has no effect; original ranking stands.
- **Emotion tag is null** (short message, low confidence): old retrieval path used unchanged.
- **Category is "crisis"**: retrieval is skipped entirely (existing behavior preserved).

---

## FR-04 Rolling Conversation Summaries

### Problem
When a session accumulates many messages, the LLM's effective context window shrinks because only the last 12 messages (`HISTORY_FOR_LLM = 12`) are injected into the prompt. Early conversation context — including initial disclosures, identified themes, and progress notes — is invisible to the LLM after 6 turns.

Additionally, there is no persistent human-readable summary of a session's content, which would be valuable for:
- Future session continuity (user returns after >24h when Redis TTL expires).
- Safeguarding reviews (operators reviewing flagged sessions).
- User-facing memory ("what have we talked about?").

### Current Limitation
- No summarization logic exists in v1.0.
- After Redis TTL expiry (24h), the session restarts with no memory of prior context.
- PostgreSQL stores all messages but there is no way to synthesize them back into a usable context payload.

### Proposed Solution
Introduce **automatic rolling summaries** generated by Gemini when a session crosses a message-count threshold.

**Trigger:** After every 20 user messages (i.e., when `message_count` mod 20 == 0 and `message_count > 0`).

**Summary generation:**
1. Retrieve the last 40 messages from PostgreSQL (the "summarization window").
2. Send a dedicated Gemini call with a compact summarization prompt:
   > "You are a compassionate clinical note writer. Summarize the following therapy conversation in 3-5 sentences, noting: the user's main concern, any themes that emerged, the emotional arc, and any progress or coping strategies mentioned. Do not include the user's name or any identifying details. Keep it factual and warm."
3. Store the result in a new `session_summary` TEXT column on `chat_sessions`.
4. Update `summary_updated_at` TIMESTAMPTZ.

**Injection into LLM prompt:** When `session_summary` is non-null, prepend it to the prompt as:
> "[Previous session context: {summary}]"

This gives the LLM a compressed but semantically rich view of earlier conversation history, even after the Redis rolling window has dropped those messages.

**Async execution:** Summary generation runs as a **background task** (`asyncio.create_task`) after the main message response is returned to the user. The user sees no latency impact.

### Acceptance Criteria
- [ ] `chat_sessions` table has `session_summary TEXT NULL` and `summary_updated_at TIMESTAMPTZ NULL` columns.
- [ ] Summary is triggered automatically at every 20th user message (configurable via `SUMMARY_TRIGGER_EVERY = 20` in config).
- [ ] Summary generation is non-blocking — response is returned to user before summary is generated.
- [ ] If summary generation fails (Gemini error), session continues without summary — no user-facing error.
- [ ] Summary is injected into the LLM prompt when non-null.
- [ ] `GET /api/v1/chat/sessions` response includes `session_summary: string | null`.
- [ ] Integration test: send 21 messages to a session; assert `session_summary` is non-null after the 20th.
- [ ] Summary generation prompt is a configurable constant (not hardcoded in business logic).

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Summary Gemini call adds latency | N/A (async) | N/A | Run as background task |
| Summary overwrites earlier summary (rolling summaries accumulate changes) | Low | Low | `session_summary` is always replaced on trigger — not appended |
| Summary may reveal sensitive information in logs | Medium | High | Summary stored in DB only; never logged beyond DEBUG level |
| Gemini cost increase from extra summarization calls | Medium | Medium | Trigger threshold configurable; monitor usage in staging |

### Edge Cases
- **Gemini unavailable during summary**: background task fails silently; summary column stays null.
- **Session with < 20 messages**: no summary generated.
- **Crisis session**: summarization still runs (clinical context is valuable) but summary is never exposed to users via a public listing endpoint.
- **Concurrent writes at message 20 boundary**: background task is idempotent — duplicate summaries overwrite harmlessly.

---

## FR-05 Improved Existential vs. Crisis Distinction

### Problem
The v1.0 crisis detection pipeline uses three layers:
1. **Keyword regex**: compiled pattern against `CRISIS_KEYWORDS` list.
2. **Embedding similarity**: cosine similarity >= 0.70 to crisis sub-corpus vectors.
3. **Classifier**: `predicted_category == "crisis"` + confidence >= 0.75 + uncertainty < 0.04 + word count >= 4.

**False positive scenario**: Users expressing **existential distress** — "What's the point of anything?", "Nothing feels real anymore", "I feel like I'm disappearing" — semantically overlap with crisis language and can trigger Layer 2 (embedding similarity). These are not crises; they are philosophical and dissociative expressions that call for empathetic engagement, not an emergency helpline response.

Sending the crisis response to a user expressing existential distress is harmful because:
- It is jarring and feels dismissive of the philosophical nature of their expression.
- It may cause the user to disengage or distrust the system.
- It under-responds to the real emotional content.

### Current Limitation
- `check_crisis_embedding()` in `embedder.py` uses a single threshold (0.70) with no distinguishing between crisis intent and existential distress.
- No "existential" category exists in the classifier's 10-category taxonomy.
- `CRISIS_KEYWORDS` list focuses on action-oriented phrases; existential language is handled by the embedding layer only.

### Proposed Solution
Introduce a dedicated **existential expression corpus** — a small set of embedding anchors for existential/philosophical distress patterns. These anchors are used to **reduce the crisis similarity score** if the user's message is more similar to existential anchors than to genuine crisis anchors.

**Algorithm change in `check_crisis_embedding()`:**

```
crisis_similarity = max cosine similarity to crisis vectors
existential_similarity = max cosine similarity to existential anchor vectors

If crisis_similarity >= CRISIS_THRESHOLD (0.70):
    If existential_similarity > crisis_similarity - EXISTENTIAL_MARGIN (0.08):
        Classify as "existential", NOT crisis → Return (False, True)
    Else:
        Classify as genuine crisis → Return (True, False)
Else:
    Return (False, False)
```

**Existential anchor phrases (10 examples):**
- "What is the point of anything"
- "Nothing feels real anymore"
- "I feel like I'm disappearing"
- "Life seems meaningless but I'm okay"
- "I question whether anything matters"
- "I feel detached from reality"
- "Who am I really"
- "I don't know what I'm doing here"
- "Everything feels empty but I'm not in danger"
- "I feel like a ghost going through the motions"

Additionally, add a dedicated **`predicted_category = "existential"`** response in the `ai_service` pipeline that triggers a tailored, grounding system prompt injection (NOT the helpline crisis response).

**New config constants:**
- `EXISTENTIAL_MARGIN = 0.08` — how close existential similarity must be to crisis similarity to redirect.
- `EXISTENTIAL_RESPONSE_HINT = "[The user may be expressing existential or philosophical distress, not immediate crisis. Respond with grounding, curiosity, and warmth. Do NOT suggest emergency resources.]"`

### Acceptance Criteria
- [ ] Existential anchor vectors are pre-computed at startup and loaded by `embedder`.
- [ ] `check_crisis_embedding()` now returns a tuple `(is_crisis: bool, is_existential: bool)`.
- [ ] `ai_service.py` checks `is_existential` and conditionally injects `EXISTENTIAL_RESPONSE_HINT` into the prompt.
- [ ] `predicted_category` can return `"existential"` as a new category value.
- [ ] The following phrases must return `is_crisis=False`: "What is the point of anything?", "Nothing feels real anymore", "I feel like I'm disappearing".
- [ ] The following phrases must still return `is_crisis=True`: "I want to kill myself", "I'm thinking about suicide".
- [ ] Regression test suite includes >= 10 existential phrases, all asserting `is_crisis=False`.
- [ ] Regression test suite includes >= 10 genuine crisis phrases, all asserting `is_crisis=True`.
- [ ] `EXISTENTIAL_MARGIN` is a named constant in `crisis_service.py`, not a magic number.

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Existential margin miscalibrated; genuine crisis misclassified as existential | Low | CRITICAL | Safety net: keyword layer is unaffected; Layer 1 always runs first and is authoritative |
| Existential anchors not comprehensive enough | Medium | Low | Start with 10 anchors; add more in v1.2 based on production data |
| "existential" category leaks into few-shot retrieval | Low | Low | Filter `existential` from few-shot examples same as `crisis` |

### Edge Cases
- **Message matches both keyword list and existential anchor**: keyword layer is authoritative → `is_crisis=True`. Existential check only applies to embedding layer.
- **Existential phrases with explicit crisis intent**: "What is the point of anything, I want to die" — keyword layer catches "want to die" → `is_crisis=True`.
- **Short existential statements** (< 4 words, e.g., "why bother"): classifier trust guard applies. Keyword and embedding still run.

---

## FR-06 AI-Generated Session Titles

### Problem
In v1.0, a session title is set to the **first 50 characters of the first message** (`title = data.message[:50] + "..." if len > 50`). This produces titles like:

- "I've been feeling really anxious lately and I don't..."
- "yes"
- "okay"

These are not meaningful. They:
- Don't help users identify sessions in their history.
- Are frequently truncated mid-word.
- Expose raw user text in UI list views, which may feel intrusive.

### Current Limitation
- Title is set in `chat.py` `send_message()`, line 104: truncation of first message.
- Same behavior in `chat_ws.py` — title is never updated from the default "New Conversation".
- No AI-generated title logic exists.

### Proposed Solution
After the **first AI response** in a session, generate a short, descriptive title using Gemini. The generation runs as a **background task** (non-blocking, same pattern as FR-04 summaries).

**Generation prompt:**
> "Based on this first exchange in a mental health support conversation, generate a short, compassionate, 4-8 word title that captures the core theme without being clinical or alarming. Return only the title, no quotes or punctuation.
>
> User: {first_user_message}
> Assistant: {first_ai_response}"

**Fallback:** If generation fails or returns an empty string, keep the v1.0 truncation behavior as fallback.

**Persistence:** Update `chat_sessions.title` via an atomic SQL UPDATE after generation.

**New field:** Add `title_generated: bool` column to `chat_sessions` to distinguish AI-generated vs. fallback titles (useful for analytics and potential re-generation triggers).

### Acceptance Criteria
- [ ] Session title is updated to an AI-generated string after the first message.
- [ ] Generation runs in background — first message response latency is unaffected.
- [ ] Fallback to truncated first message if Gemini fails.
- [ ] Generated title is 4–10 words (validated with a length check; reject and fallback if outside range).
- [ ] `chat_sessions` table has `title_generated BOOLEAN DEFAULT false`.
- [ ] `GET /api/v1/chat/sessions` response includes `title_generated: bool`.
- [ ] AI title is never generated for crisis-flagged sessions where `is_crisis=True` on the first message — fallback title only.
- [ ] Integration test: create a session, send first message, wait 3 seconds, fetch session list, assert title is non-empty and `title_generated=true`.

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Title generation leaks sensitive content (echoing user message) | Low | Medium | Prompt instructs model to use themes, not verbatim quotes; review title format |
| Gemini rate limit during high message-20 trigger volume | Low | Low | Background task; failure defaults to truncation fallback |

### Edge Cases
- **First message is a crisis message**: title generation is skipped; fallback used.
- **Session with only one message**: title generated from the single exchange.
- **Very short first message** ("yes", "hi"): Gemini may return a generic title — acceptable; length validation still applied.
- **Title generation called twice** (race condition between REST and WS): `title_generated=true` is set atomically; second call is a no-op (only generate when `title_generated=false`).

---

## FR-07 Memory Persistence Improvements

### Problem
The v1.0 memory system has two significant gaps:

**Gap 1 — Redis-only persistence:** Redis stores the rolling conversation window (`MAX_HISTORY = 20`, TTL = 24h). If Redis restarts, the memory is **permanently lost** even though PostgreSQL has the full message history.

**Gap 2 — No warm-load from PostgreSQL:** When a user returns to a session after Redis TTL expiry (> 24h), `memory_service.get_history()` returns `[]`. The AI pipeline falls back to PostgreSQL session history, but Redis is **not repopulated**. Subsequent requests get `redis_history = []` again, causing repeated PostgreSQL fallback on every message.

**Gap 3 — Missing fields in Redis schema:** All v1.1 features (FR-01 through FR-03) need `emotion_tag` and `importance_score` stored in Redis entries. The current Redis schema does not support these.

### Current Limitation
- `memory_service.py` has no `warm_load()` method.
- Redis entry schema is fixed to: `role`, `content`, `category`, `confidence`, `is_crisis`, `timestamp`.
- The WebSocket path in `chat_ws.py` passes `session_history` from PostgreSQL but does not restore Redis after TTL expiry.

### Proposed Solution

**Fix Gap 1 — Schematic Redis entry upgrade:**
Add `emotion_tag: str | null` and `importance_score: float` to the Redis JSON entry schema. Backward-compatible: old entries without these fields default to `null / 0.5` when read.

**Fix Gap 2 — Warm-load on Redis miss:**
Add `warm_load(session_id, messages)` method to `MemoryService`:
- Called when `get_history()` returns `[]` AND `session_history` from PostgreSQL is non-empty.
- Re-populates Redis with the last `MAX_HISTORY` messages from PostgreSQL.
- Each message is assigned a default `importance_score = 0.5` and `emotion_tag = null` (historical messages are not re-analyzed).
- Called from both `chat.py` and `chat_ws.py` before the AI pipeline runs.

**Fix Gap 3 — Configurable TTL:**
Expose `memory_ttl_preference` as a user setting:
- Store on the `User` model as `memory_ttl_preference VARCHAR(20) DEFAULT '24h'`.
- Accepted values: `'24h'`, `'72h'`, `'7d'`, `'session'`.
- Applied as TTL in seconds when calling Redis EXPIRE.

### Acceptance Criteria
- [ ] `MemoryService.warm_load(session_id, messages)` method exists and is called when Redis returns empty.
- [ ] After `warm_load()`, subsequent `get_history()` calls for the same session return the warm-loaded messages.
- [ ] Redis entry schema includes `emotion_tag` and `importance_score` fields.
- [ ] Old Redis entries (without new fields) are read without errors (graceful defaults).
- [ ] `User` model has `memory_ttl_preference` column (VARCHAR 20, nullable, default `'24h'`).
- [ ] `GET /api/v1/users/me` response includes `memory_ttl_preference`.
- [ ] `PATCH /api/v1/users/me` accepts `memory_ttl_preference` update.
- [ ] Integration test: expire a Redis session key manually, send a new message, assert `memory_used=True` (warm-load triggered).
- [ ] Unit test: `warm_load()` with empty messages is a no-op.

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| warm_load adds PostgreSQL query on every session init | Medium | Medium | Only triggered when Redis returns empty AND PostgreSQL has messages |
| User-configurable TTL creates complex key management | Medium | Low | TTL is per-write; MemoryService reads user preference and passes to EXPIRE |

### Edge Cases
- **New session (no PostgreSQL history either)**: `warm_load()` with empty list is a no-op.
- **Session with 100+ messages in PostgreSQL**: warm_load caps at `MAX_HISTORY` (20 most recent).
- **Redis unavailable during warm_load**: warm_load is skipped; fallback path proceeds.

---

## FR-08 Better Testing

### Problem
The v1.0 test suite consists of:
1. `test_ai_pipeline.py` — 4 pytest unit tests (embedder, crisis keyword, crisis embedding, few-shot count).
2. `e2e_test.py` — 5 end-to-end tests that require a live server + Redis + PostgreSQL.

**Gaps identified:**
- No unit tests for `ai_service.process_message()` pipeline as a whole.
- No unit tests for `MemoryService` (all Redis operations untested in isolation).
- No unit tests for `ClassifierService.predict()`.
- No unit tests for `crisis_service.is_crisis_message()` with the existential guard (FR-05).
- No integration tests that use a test database (all tests hit the live server).
- No performance benchmarks for pipeline latency.
- No regression tests for the new v1.1 features (FR-01 through FR-07).
- Test configuration is hardcoded in `conftest.py` (email and password literals).

### Proposed Solution
Restructure the test suite following the standard pytest hierarchy:

```
backend/tests/
├── conftest.py                     # shared fixtures (updated)
├── unit/
│   ├── test_crisis_service.py      # keyword detection + existential guard
│   ├── test_embedder.py            # relevance, crisis embedding, retrieval
│   ├── test_classifier.py          # predict(), graceful degradation
│   ├── test_memory_service.py      # all Redis methods (mocked Redis)
│   ├── test_emotion_tagger.py      # FR-01: all 7 emotion anchors
│   ├── test_importance_score.py    # FR-02: scoring formula
│   └── test_ai_pipeline.py         # process_message() with mocked services
├── integration/
│   ├── test_chat_api.py            # REST chat endpoints (test DB)
│   ├── test_auth_api.py            # register, login, refresh
│   ├── test_mood_api.py            # mood log, history, stats
│   ├── test_session_summary.py     # FR-04: rolling summary trigger
│   └── test_session_title.py       # FR-06: AI title generation
├── regression/
│   ├── test_crisis_regression.py       # >= 20 crisis phrases must trigger crisis
│   ├── test_existential_regression.py  # >= 10 existential phrases must NOT trigger crisis
│   └── test_false_positive_guard.py    # short messages must not trigger crisis
└── performance/
    └── test_pipeline_latency.py        # pipeline p95 < 200ms (mocked Gemini)
```

**Test tooling additions:**
- `pytest-mock` for mocking Redis and Gemini.
- `fakeredis[aioredis]` for in-process Redis simulation (no Docker dependency for unit tests).
- `pytest-asyncio` (already installed) for async test support.
- `pytest-benchmark` for performance tests.

**Coverage gate:** Add `pytest --cov=app --cov-fail-under=80` to CI. Minimum 80% line coverage required to merge.

### Acceptance Criteria
- [ ] All existing tests continue to pass after v1.1 changes.
- [ ] Unit test coverage >= 80% of `app/services/` directory.
- [ ] Crisis regression test: all >= 20 crisis phrases return `is_crisis=True`.
- [ ] Existential regression test: all >= 10 existential phrases return `is_crisis=False`.
- [ ] False-positive guard test: all 6 existing short messages return `is_crisis=False`.
- [ ] Performance test: `process_message()` (embed + classify + emotion tag + retrieval) completes in < 200ms p95 without Gemini call (mocked).
- [ ] `fakeredis` used for all unit tests — no live Redis required for `pytest tests/unit/`.
- [ ] CI workflow runs `pytest tests/unit/` and `pytest tests/regression/` on every pull request.
- [ ] `conftest.py` credentials are loaded from environment variables, not hardcoded.

### Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Mocked Gemini may mask real integration bugs | Medium | Medium | Keep e2e tests for pre-release validation |
| Performance targets too aggressive for CI hardware | Low | Low | Benchmark values calibrated against CI machine |

### Edge Cases
- **Test isolation:** Each unit test must be fully isolated — no shared state between tests.
- **Async tests:** All async service methods use `pytest-asyncio` with `@pytest.mark.asyncio`.

---

## Non-Functional Requirements

### Performance
- `process_message()` end-to-end latency (excluding Gemini): p95 < 200ms.
- Emotion tagger: < 5ms additional latency (reuses existing embedding).
- Importance scoring: < 2ms per message.
- Summary generation: non-blocking; no user-facing latency.
- Title generation: non-blocking; no user-facing latency.

### Reliability
- All new services degrade gracefully; no new single points of failure introduced.
- New Redis schema changes must be backward-compatible with v1.0 Redis entries.
- All new Gemini calls have try/except with graceful fallback.

### Security
- Session summaries and emotion tags are never logged above DEBUG level.
- User-configurable TTL changes are validated against an allowlist: `['24h', '72h', '7d', 'session']`.
- Emotion tags are not exposed in any public (unauthenticated) endpoint.

### Backward Compatibility
- All v1.0 REST API clients continue to work — new response fields are additive only.
- Existing v1.0 Redis memory entries can be read; new fields default gracefully.
- Existing database rows are unaffected; all column additions are nullable with sensible defaults.

---

## Summary Table

| ID | Feature | Priority | Complexity | New Tables/Columns | New API Changes |
|----|---------|----------|------------|-------------------|-----------------|
| FR-01 | Emotion Tagging | P0 | Medium | `messages.emotion_tag` | `ChatResponse.emotion_tag` |
| FR-02 | Importance Scoring | P0 | Medium | `messages.importance_score` | Internal only |
| FR-03 | Emotion-Aware Retrieval | P1 | Low | None | Internal only |
| FR-04 | Rolling Summaries | P1 | Medium | `sessions.session_summary`, `sessions.summary_updated_at` | `SessionResponse.session_summary` |
| FR-05 | Existential vs. Crisis | P0 | Medium | None | `ChatResponse.predicted_category` (new value) |
| FR-06 | AI Session Titles | P2 | Low | `sessions.title_generated` | `SessionResponse.title_generated` |
| FR-07 | Memory Persistence | P0 | Medium | `users.memory_ttl_preference` | `UserResponse.memory_ttl_preference`, new PATCH endpoint |
| FR-08 | Better Testing | P0 | Medium | None | None |
