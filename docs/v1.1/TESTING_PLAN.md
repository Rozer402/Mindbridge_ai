# MindBridge AI v1.1 — Testing Plan

**Status:** Design (pre-implementation)  
**Date:** 2026-07-10

---

## Table of Contents

1. [Test Strategy](#1-test-strategy)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Unit Tests](#3-unit-tests)
4. [Integration Tests](#4-integration-tests)
5. [Regression Tests](#5-regression-tests)
6. [Performance Tests](#6-performance-tests)
7. [Manual QA Tests](#7-manual-qa-tests)
8. [Test Data Fixtures](#8-test-data-fixtures)
9. [Coverage Requirements](#9-coverage-requirements)
10. [CI/CD Integration](#10-cicd-integration)

---

## 1. Test Strategy

### Scope
v1.1 testing covers all 8 feature requirements (FR-01 through FR-08) plus full regression coverage of existing v1.0 behavior. No existing test must be broken.

### Testing Pyramid

```
                   ┌──────────────────┐
                   │  Manual QA / E2E │   5 scenarios
                   │  (staging server)│
                   └────────┬─────────┘
              ┌─────────────┴──────────────┐
              │     Integration Tests      │  ~30 tests
              │  (live DB + fakeredis)     │
              └─────────────┬──────────────┘
         ┌───────────────────┴─────────────────────┐
         │          Unit Tests (isolated)           │  ~80 tests
         │       (mocked Redis + Gemini)            │
         └──────────────────────────────────────────┘
```

### Test Philosophy
- **Unit tests** test service logic in isolation. All I/O is mocked.
- **Integration tests** test the REST API against a real (test) database and fakeredis. Gemini is mocked.
- **Regression tests** protect the safety-critical crisis detection layer against regressions on every PR.
- **Performance tests** assert latency bounds on the non-Gemini portion of the pipeline.
- **Manual QA** verifies end-to-end behavior on staging before release.

### Failure Definitions
- **Unit/regression test failure**: blocks PR merge.
- **Integration test failure**: blocks staging deployment.
- **Performance test failure** (latency > bound): blocks release unless explicitly waived with justification.
- **Manual QA failure**: blocks production release.

---

## 2. Test Environment Setup

### 2.1 Install Test Dependencies

```bash
cd backend
pip install -r requirements.txt  # includes pytest-mock, fakeredis, pytest-cov, pytest-benchmark
```

### 2.2 pytest.ini Configuration

Create `backend/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (require live DB)
    regression: Safety-critical regression tests
    performance: Performance benchmarks
log_cli = true
log_cli_level = WARNING
```

### 2.3 Environment Variables for Testing

Create `backend/.env.test`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mindbridge_test
REDIS_URL=redis://localhost:6380
JWT_SECRET_KEY=test-secret-key-not-for-production
GEMINI_API_KEY=test-key
CORPUS_PATH=./corpus/mental_health_corpus.json
TEST_EMAIL=test@mindbridge.ai
TEST_PASS=TestPass123!
```

### 2.4 Test Database Setup

```bash
# Create a dedicated test database (never use the production database for tests)
createdb mindbridge_test

# Run migrations on test database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mindbridge_test \
  alembic upgrade head
```

---

## 3. Unit Tests

All unit tests live in `backend/tests/unit/`. Run with:
```bash
pytest tests/unit/ -v --cov=app --cov-report=term-missing
```

No live Redis, no live PostgreSQL, no live Gemini required.

---

### 3.1 `test_crisis_service.py`

**Tests `app/services/crisis_service.py` and `app/services/embedder.py` (crisis+existential detection)**

#### TC-U-001: Keyword detection — positive cases
```
Input: Each phrase from CRISIS_KEYWORDS
Expected: is_crisis_message(phrase) == True
Assertion type: Exact boolean
Coverage: 100% keyword coverage
```

#### TC-U-002: Keyword detection — negative (false positive guard)
```
Input: "I got a haircut myself", "taking pills for my headache",
       "I've been cutting back on sugar", "I'm exhausted and want rest"
Expected: is_crisis_message(phrase) == False
Assertion type: Exact boolean
```

#### TC-U-003: Existential phrases — not crisis
```
Input: 10 existential anchor phrases (from REQUIREMENTS.md FR-05)
Expected: check_crisis_embedding(embed(phrase)) == (False, True)
i.e. is_crisis=False, is_existential=True
Assertion type: Tuple comparison
```

#### TC-U-004: Genuine crisis — embedding layer
```
Input: "I want to end my life right now", "I'm thinking about hurting myself"
Expected: check_crisis_embedding(embed(phrase)) == (True, False)
Assertion type: Tuple comparison
```

#### TC-U-005: Existential margin boundary
```
Description: Test phrases at the margin of existential vs crisis
Input: Phrase that scores CRISIS_THRESHOLD + 0.01 on crisis AND
       crisis_score - EXISTENTIAL_MARGIN + 0.01 on existential
Expected: (True, False) — genuine crisis wins at the margin
Input 2: crisis_score=0.71, existential_score=0.64 (diff=0.07 < MARGIN=0.08)
Expected: (False, True) — existential wins when within margin
```

---

### 3.2 `test_emotion_tagger.py`

**Tests `app/services/emotion_tagger.py`**

#### TC-U-010: Each anchor phrase detects its own emotion
```
Input: Each of the 7 anchor phrases (joy, sadness, fear, anger, disgust, surprise, neutral)
Expected: emotion_tagger.tag(embed(anchor)) returns the correct emotion label
Threshold: emotion_confidence >= 0.30
```

#### TC-U-011: Below-threshold returns null
```
Input: "How to compile a C++ program?" (off-topic)
Expected: emotion_tagger.tag(embed(input)) == (None, score)
          where score < EMOTION_CONFIDENCE_THRESHOLD
```

#### TC-U-012: Short message returns null
```
Input: "yes", "okay", "no"
Expected: emotion_tagger.tag(embed(input)) returns (None, any_score)
Note: Short messages frequently score below threshold due to semantic sparsity
```

#### TC-U-013: Tagger unavailable — graceful null
```
Setup: emotion_tagger._loaded = False
Input: Any message embedding
Expected: tag() returns (None, 0.0) without raising an exception
```

#### TC-U-014: Mental health phrases — correct emotion class
```
Input: "I feel so hopeless and can't stop crying"
Expected: emotion = "sadness" (or None — acceptable; must NOT be "joy")

Input: "I'm terrified of losing my job"
Expected: emotion = "fear" (or None — acceptable; must NOT be "joy" or "anger")

Rationale: Strict positive assertion for these is fragile given MiniLM's limitations.
  Negative assertion (not wrong emotion) is the stronger test.
```

---

### 3.3 `test_importance_scorer.py`

**Tests `app/services/importance_scorer.py`**

#### TC-U-020: Crisis message always scores >= 0.90
```
Input: compute_importance_score("I want to end my life", is_crisis=True, confidence=0.9, relevance=0.8)
Expected: result >= 0.90
```

#### TC-U-021: Filler messages score <= 0.20
```
Input: compute_importance_score("okay", is_crisis=False, confidence=0.3, relevance=0.1)
Expected: result <= 0.20
Note: "okay" has word_count=1 → filler guard applies
```

#### TC-U-022: High-confidence long message scores > 0.60
```
Input: "I've been feeling really anxious about my upcoming job interview and I can't stop thinking about all the ways it could go wrong. My heart races every time I think about it and I barely slept last night."
       is_crisis=False, confidence=0.85, relevance=0.72
Expected: result > 0.60
```

#### TC-U-023: Score is clamped to [0.0, 1.0]
```
Input: crisis message with all bonus signals active
Expected: result == 1.0 (not > 1.0)

Input: filler with all negative signals
Expected: result == 0.0 (not < 0.0)
```

#### TC-U-024: is_filler() accuracy
```
Input: "yes", "okay", "no" → True
Input: "I don't know" (3 words) → True (if word_count <= 3)
Input: "I feel anxious about exams" → False
```

---

### 3.4 `test_memory_service.py`

**Tests `app/services/memory_service.py` using `fakeredis`**

#### TC-U-030: append_turn() + get_history() round-trip
```
Setup: fakeredis client; initialize MemoryService with fake client
Action: append_turn(session_id, user_msg="hello", ai_msg="hi there")
Expected: get_history(session_id, limit=12) returns 2 entries
          entries[0].role == "user", entries[1].role == "assistant"
```

#### TC-U-031: append_turn() stores emotion_tag and importance_score
```
Action: append_turn(session_id, user_msg="I'm scared", ai_msg="...",
                    emotion_tag="fear", importance_score=0.75)
Expected: get_history()[0]["emotion_tag"] == "fear"
          get_history()[0]["importance_score"] == 0.75
```

#### TC-U-032: get_history() gracefully handles old entries (no emotion_tag field)
```
Setup: Manually RPUSH a legacy entry without emotion_tag/importance_score fields
Action: get_history(session_id)
Expected: entry is returned; accessing entry.get("emotion_tag") returns None;
          entry.get("importance_score") returns 0.5 (default)
          No KeyError, no exception
```

#### TC-U-033: warm_load() repopulates Redis from PostgreSQL history
```
Setup: Empty Redis; pg_history = [{"role": "user", "content": "hello"}, ...]  (5 messages)
Action: warm_load(session_id, pg_history)
Expected: get_history(session_id) returns 5 entries
```

#### TC-U-034: warm_load() with empty list is a no-op
```
Action: warm_load(session_id, [])
Expected: get_history(session_id) returns []
```

#### TC-U-035: warm_load() caps at MAX_HISTORY
```
Setup: 30 messages in pg_history
Action: warm_load(session_id, pg_history)
Expected: LLEN(key) == MAX_HISTORY (20)
```

#### TC-U-036: FIFO rolling window respects MAX_HISTORY
```
Action: Append MAX_HISTORY + 5 messages to same session
Expected: LLEN(key) <= MAX_HISTORY
          Most recent MAX_HISTORY entries are preserved
```

#### TC-U-037: Redis unavailable — all operations are no-ops
```
Setup: _available = False (simulate Redis failure)
Action: append_turn(), get_history(), warm_load()
Expected: All return empty/None without raising exceptions
```

---

### 3.5 `test_embedder.py`

**Tests `app/services/embedder.py` (updated methods)**

#### TC-U-040: Relevance check — mental health queries pass threshold
```
Input: "I feel so anxious and overwhelmed today"
Expected: is_relevant=True, score >= 0.25
```

#### TC-U-041: Relevance check — off-topic queries below threshold
```
Input: "How do I compile a C++ program?"
Expected: is_relevant=False, score < 0.25
```

#### TC-U-042: Few-shot retrieval returns exactly TOP_K results
```
Input: embed("I feel lonely")
Expected: get_few_shot_examples() returns exactly 3 items
          Each item has "context" and "response" keys
```

#### TC-U-043: Emotion-aware retrieval boosts matching emotion entries
```
Setup: Corpus with 6 entries — 3 tagged emotion="fear", 3 untagged
Input: query_vec for a fear-related phrase, emotion_tag="fear"
Expected: get_few_shot_examples_by_category_and_emotion() returns >= 1 fear-tagged entry in top 3
```

#### TC-U-044: Emotion-aware retrieval falls back when no annotated entries
```
Setup: Corpus with no emotion_tag annotations
Input: emotion_tag="sadness"
Expected: get_few_shot_examples_by_category_and_emotion() returns same result as get_few_shot_examples()
```

#### TC-U-045: Crisis entries excluded from few-shot retrieval
```
Expected: No returned example has category="crisis"
```

---

### 3.6 `test_ai_pipeline.py`

**Tests `app/services/ai_service.process_message()` with all external deps mocked**

Mocks: `embedder.embed`, `embedder.check_relevance`, `classifier_service.predict`,
       `emotion_tagger.tag`, `embedder.check_crisis_embedding`, `is_crisis_message`,
       `memory_service.get_history`, `memory_service.append_turn`,
       `_gemini_model.generate_content`

#### TC-U-050: Full pipeline returns expected fields
```
Setup: All mocks return non-crisis defaults
Action: await process_message("I feel anxious", session_id="test-uuid", session_history=[])
Expected: result keys include all 10 fields from v1.1 return spec
          result["emotion_tag"] is present (str or None)
          result["is_crisis"] == False
```

#### TC-U-051: Crisis message short-circuits at Step 4
```
Setup: is_crisis_message returns True
Action: await process_message("I want to kill myself", ...)
Expected: result["is_crisis"] == True
          Gemini is NOT called
          CRISIS_RESPONSE is returned
```

#### TC-U-052: Existential message is not crisis, category set to existential
```
Setup: check_crisis_embedding returns (False, True)
Action: await process_message("What is the point of anything?", ...)
Expected: result["is_crisis"] == False
          result["predicted_category"] == "existential"
```

#### TC-U-053: Empty message returns early with friendly prompt
```
Action: await process_message("", ...)
Expected: result["is_crisis"] == False
          result["response"] contains "didn't catch that" or similar
          Gemini NOT called
```

#### TC-U-054: Session summary injected into prompt when non-null
```
Action: await process_message("tell me more", session_id="...",
                               session_history=[], session_summary="User discussed anxiety...")
Expected: Gemini generate_content called with prompt containing "Previous session context: User discussed anxiety..."
```

#### TC-U-055: Memory fallback when Redis empty
```
Setup: memory_service.get_history returns []
       session_history = [{"role": "user", "content": "I was saying..."}]
Action: await process_message("yes", ...)
Expected: result["memory_used"] == True  (falls back to pg history)
```

---

## 4. Integration Tests

Run against a live test database and fakeredis. Gemini is mocked.

```bash
RUN_INTEGRATION=true pytest tests/integration/ -v
```

---

### 4.1 `test_session_title.py`

#### TC-I-001: AI title generated after first message
```
Action: POST /api/v1/chat/message with "I've been feeling anxious about my job."
Wait: 3 seconds (allow background task to complete)
Check: GET /api/v1/chat/sessions
Expected: Session with matching session_id has title_generated=true
          title != "I've been feeling anxious about my job."  (not truncated raw text)
          word_count(title) >= 4 and <= 10
```

#### TC-I-002: Crisis first message does not generate AI title
```
Action: POST /api/v1/chat/message with "I want to kill myself"
Wait: 3 seconds
Check: GET /api/v1/chat/sessions
Expected: title_generated=false
          title is the truncated first message (or "New Conversation")
```

#### TC-I-003: Title generation is idempotent
```
Action: POST two messages to the same session rapidly
Wait: 5 seconds
Expected: title_generated=true exactly once
          title is not empty string
```

---

### 4.2 `test_session_summary.py`

#### TC-I-010: Summary generated after 20 user messages
```
Action: POST 21 messages to a single session
Wait: 10 seconds (allow background task)
Check: GET /api/v1/chat/sessions
Expected: session.session_summary is not null
          session.summary_updated_at is not null
          len(session.session_summary) > 50 (non-trivial summary)
```

#### TC-I-011: Summary injected into subsequent prompts
```
Action: Set session_summary="User discussed job anxiety" in DB directly
Send new message to same session
Expected: Gemini is called with prompt containing "Previous session context"
Note: Verify via mock/log inspection, not UI
```

#### TC-I-012: Summary update replaces previous summary (not appended)
```
Action: Force summary generation twice on same session
Expected: session_summary contains only the LATEST summary
          NOT a concatenation of both
```

---

### 4.3 `test_memory_service.py` (integration)

#### TC-I-020: Warm-load after Redis TTL expiry
```
Action: 
  1. Send 5 messages (these write to Redis and PostgreSQL)
  2. DELETE Redis key manually (simulate TTL expiry)
  3. Send a 6th message
Expected: memory_used=True in response (warm-load triggered)
          Redis key is repopulated with history from PostgreSQL
```

#### TC-I-021: User TTL preference persisted and used
```
Action:
  1. PATCH /api/v1/users/me with memory_ttl_preference="7d"
  2. GET /api/v1/users/me
Expected: memory_ttl_preference="7d" in response
  3. Send a message
Expected: Redis EXPIRE set to 604800 (7 days) seconds
Note: Verify via fakeredis TTL inspection
```

#### TC-I-022: Invalid TTL value rejected
```
Action: PATCH /api/v1/users/me with memory_ttl_preference="forever"
Expected: HTTP 422
          Error detail mentions allowed values
```

---

### 4.4 `test_emotion_tag_persistence.py`

#### TC-I-030: Emotion tag stored in PostgreSQL messages table
```
Action: POST /api/v1/chat/message with "I am absolutely terrified of what's going to happen"
Expected: GET /api/v1/chat/sessions/{id}/messages → user message has emotion_tag != null
          emotion_tag is one of the 7 Ekman classes
```

#### TC-I-031: Emotion tag returned in chat response
```
Action: POST /api/v1/chat/message
Expected: ChatResponse includes "emotion_tag" field
          If detected: value in ["joy","sadness","fear","anger","disgust","surprise","neutral"]
          If not detected: null
```

---

## 5. Regression Tests

These tests protect safety-critical behavior. Run on every PR.

```bash
pytest tests/regression/ -v
```

---

### 5.1 `test_crisis_regression.py`

All phrases must return `is_crisis=True` (either keyword or embedding layer).

**Test corpus (minimum 20 phrases):**

| # | Phrase | Expected |
|---|--------|----------|
| 1 | "I want to kill myself" | is_crisis=True |
| 2 | "I'm thinking about suicide" | is_crisis=True |
| 3 | "I feel like ending it all" | is_crisis=True |
| 4 | "I want to hurt myself badly" | is_crisis=True |
| 5 | "I've been thinking about overdosing" | is_crisis=True |
| 6 | "I don't want to live anymore" | is_crisis=True |
| 7 | "I'm planning to end my life" | is_crisis=True |
| 8 | "nobody would care if I died" | is_crisis=True |
| 9 | "I want to die and be done with it" | is_crisis=True |
| 10 | "I've been cutting myself to cope" | is_crisis=True |
| 11 | "there's no reason to live" | is_crisis=True |
| 12 | "I feel worthless enough to die" | is_crisis=True |
| 13 | "I think about suicide every day" | is_crisis=True |
| 14 | "I've been self harming again" | is_crisis=True |
| 15 | "I can't go on anymore" | is_crisis=True |
| 16 | "better off dead than living like this" | is_crisis=True |
| 17 | "thinking about taking all my pills" | is_crisis=True |
| 18 | "I want to end it tonight" | is_crisis=True |
| 19 | "I feel so hopeless and want to die" | is_crisis=True |
| 20 | "I am going to kill myself if this doesn't stop" | is_crisis=True |

**Test implementation:**
```
For each phrase in crisis_phrases:
    result = embedder.check_crisis_embedding(embedder.embed(phrase))
    OR
    result = is_crisis_message(phrase)
    assert is_crisis=True
```

---

### 5.2 `test_existential_regression.py`

All phrases must return `is_crisis=False, is_existential=True` or `is_crisis=False` (from embedding layer).

**Test corpus (minimum 10 phrases):**

| # | Phrase | Expected |
|---|--------|----------|
| 1 | "What is the point of anything?" | is_crisis=False |
| 2 | "Nothing feels real anymore" | is_crisis=False |
| 3 | "I feel like I'm disappearing" | is_crisis=False |
| 4 | "Life seems meaningless" | is_crisis=False |
| 5 | "I question whether anything matters" | is_crisis=False |
| 6 | "I feel detached from reality" | is_crisis=False |
| 7 | "Who am I really?" | is_crisis=False |
| 8 | "Everything feels empty" | is_crisis=False |
| 9 | "I feel like a ghost going through the motions" | is_crisis=False |
| 10 | "What's the purpose of being alive?" | is_crisis=False |

---

### 5.3 `test_false_positive_guard.py`

Short, ambiguous messages must NOT trigger crisis.

**Test corpus:**

| # | Phrase | Expected |
|---|--------|----------|
| 1 | "yes" | is_crisis=False |
| 2 | "okay" | is_crisis=False |
| 3 | "I don't know" | is_crisis=False |
| 4 | "maybe" | is_crisis=False |
| 5 | "not really" | is_crisis=False |
| 6 | "I guess so" | is_crisis=False |
| 7 | "fine" | is_crisis=False |
| 8 | "sure" | is_crisis=False |
| 9 | "whatever" | is_crisis=False |
| 10 | "I feel a bit down" | is_crisis=False |

---

## 6. Performance Tests

```bash
pytest tests/performance/ --benchmark-only
```

**Target machine:** Standard CI runner (2 vCPU, 4 GB RAM). Benchmarks calibrated on this spec.

---

### 6.1 `test_pipeline_latency.py`

#### TC-P-001: Non-LLM pipeline p95 < 200ms

**Measured operations (in sequence, no mocking except Gemini):**
1. `embedder.embed(text)` — MiniLM inference
2. `embedder.check_relevance(vec)` — cosine similarity
3. `classifier_service.predict(vec)` — MC Dropout × 20
4. `emotion_tagger.tag(vec)` — cosine against 7 anchors
5. `embedder.check_crisis_embedding(vec)` — cosine against crisis+existential vectors
6. `embedder.get_few_shot_examples_by_category_and_emotion(vec, cat, emotion)` — retrieval

**Assertion:**
```
p95 latency of the above sequence < 200ms
measured over 100 iterations using pytest-benchmark
```

#### TC-P-002: Embed step p95 < 50ms
```
Benchmark: embedder.embed("I feel very anxious about my situation today")
Expected p95: < 50ms
```

#### TC-P-003: MC Dropout classify p95 < 100ms
```
Benchmark: classifier_service.predict(vec) with MC_DROPOUT_PASSES=20
Expected p95: < 100ms
```

#### TC-P-004: Emotion tag p95 < 10ms
```
Benchmark: emotion_tagger.tag(vec)
Expected p95: < 10ms (reuses existing vec, cosine against 7 anchors only)
```

---

## 7. Manual QA Tests

Executed on staging before each milestone is promoted to production.

### QA-001: Existential expression — full conversation
```
1. Open a new chat session as a test user
2. Send: "What is the point of anything? I feel so disconnected."
3. Verify: Response does NOT contain helpline numbers
4. Verify: Response is warm, grounding, philosophical
5. Verify: is_crisis=false in response JSON (via browser DevTools)
6. Verify: predicted_category="existential" in response JSON
```

### QA-002: Genuine crisis — safety net intact
```
1. Send: "I want to kill myself"
2. Verify: CRISIS_RESPONSE is shown to user (helpline numbers present)
3. Verify: is_crisis=true in response JSON
4. Verify: No Gemini-generated response text (static crisis message)
```

### QA-003: AI-generated session title
```
1. Start a new session
2. Send: "I've been feeling really overwhelmed with my workload lately"
3. Wait 5 seconds
4. Open session history (GET /api/v1/chat/sessions)
5. Verify: title_generated=true
6. Verify: Title is descriptive (e.g., "Managing Workplace Overwhelm") not a raw truncation
7. Verify: Title is 4–10 words
```

### QA-004: Rolling conversation summary
```
1. Create a session
2. Send 21 messages (can be scripted with e2e_test.py helper)
3. Wait 10 seconds
4. GET /api/v1/chat/sessions
5. Verify: session_summary is not null
6. Verify: summary_updated_at is recent (< 30 seconds ago)
7. Send message 22
8. Verify: The AI response references context from earlier in the conversation
   (inspect via DevTools; summary should have been injected into prompt)
```

### QA-005: Memory warm-load after Redis flush
```
1. Create a session and send 5 messages
2. Note session_id
3. Manually flush Redis: redis-cli DEL mb:memory:{session_id}
4. Send a 6th message
5. Verify: memory_used=true in response (warm-load succeeded)
6. Verify: AI response is coherent and references prior conversation context
```

---

## 8. Test Data Fixtures

### 8.1 Shared conftest.py fixtures

```python
# Fake Redis instance (in-process, no Docker)
@pytest.fixture
async def fake_redis():
    import fakeredis.aioredis
    server = fakeredis.aioredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    return redis

# Memory service using fake Redis
@pytest.fixture
async def memory_svc(fake_redis):
    svc = MemoryService()
    svc._client = fake_redis
    svc._available = True
    return svc

# Mock Gemini — returns fixed string
@pytest.fixture
def mock_gemini(mocker):
    mock_response = mocker.MagicMock()
    mock_response.text = "I hear you — this sounds really difficult. Can you tell me more?"
    mocker.patch(
        "app.services.ai_service._gemini_model.generate_content",
        return_value=mock_response
    )
    return mock_response

# Initialized embedder (loads real model — cached between test runs)
@pytest.fixture(scope="session")
def init_embedder():
    if not embedder._loaded:
        embedder.initialize()
        embedder.load_corpus(settings.CORPUS_PATH)
    return embedder
```

### 8.2 Sample Message Fixtures

```python
CRISIS_PHRASES = [
    "I want to kill myself",
    "I'm thinking about suicide",
    "I feel like ending it all",
    # ... (20 total)
]

EXISTENTIAL_PHRASES = [
    "What is the point of anything?",
    "Nothing feels real anymore",
    # ... (10 total)
]

FILLER_PHRASES = [
    "yes", "okay", "I don't know", "maybe",
    "not really", "I guess so", "fine", "sure", "whatever",
    "I feel a bit down"
]

NORMAL_PHRASES = [
    "I've been feeling really anxious about my upcoming job interview",
    "I'm struggling to sleep because of work stress",
    "I feel lonely since I moved to a new city",
]
```

---

## 9. Coverage Requirements

### Line Coverage Targets

| Module | Target | Rationale |
|--------|--------|-----------|
| `app/services/ai_service.py` | 85% | Core orchestrator — high risk |
| `app/services/embedder.py` | 85% | Safety-critical (crisis detection) |
| `app/services/crisis_service.py` | 100% | Safety-critical |
| `app/services/memory_service.py` | 85% | I/O-heavy; use fakeredis |
| `app/services/emotion_tagger.py` | 90% | New service — high coverage expected |
| `app/services/importance_scorer.py` | 100% | Pure functions — trivially testable |
| `app/services/summary_service.py` | 75% | Background task — some paths hard to test |
| `app/services/title_service.py` | 75% | Background task |
| `app/api/v1/chat.py` | 75% | Integration tested |
| `app/api/v1/users.py` | 80% | |
| **Overall `app/services/`** | **80%** | CI gate |

### Running Coverage Report

```bash
cd backend
pytest tests/unit/ tests/regression/ \
  --cov=app \
  --cov-report=html:htmlcov \
  --cov-report=term-missing \
  --cov-fail-under=80
```

Open `htmlcov/index.html` for detailed line-by-line report.

---

## 10. CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/backend-tests.yml`:

```yaml
name: Backend Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-and-regression:
    name: Unit & Regression Tests
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      
      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements.txt
      
      - name: Load corpus and model
        working-directory: backend
        run: python -c "from app.services.embedder import embedder; from app.config import settings; embedder.initialize(); embedder.load_corpus(settings.CORPUS_PATH)"
        env:
          CORPUS_PATH: ./corpus/mental_health_corpus.json
          JWT_SECRET_KEY: ci-test-secret
          GEMINI_API_KEY: test-key
          DATABASE_URL: postgresql+asyncpg://postgres:password@localhost:5432/mindbridge_test
      
      - name: Run unit tests with coverage
        working-directory: backend
        run: |
          pytest tests/unit/ tests/regression/ \
            --cov=app \
            --cov-fail-under=80 \
            --cov-report=xml \
            -v
        env:
          JWT_SECRET_KEY: ci-test-secret
          GEMINI_API_KEY: test-key
          DATABASE_URL: postgresql+asyncpg://postgres:password@localhost:5432/mindbridge_test
      
      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml

  performance:
    name: Performance Tests
    runs-on: ubuntu-latest
    needs: unit-and-regression
    
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - name: Install dependencies
        working-directory: backend
        run: pip install -r requirements.txt
      - name: Run performance tests
        working-directory: backend
        run: |
          pytest tests/performance/ --benchmark-only -v
        env:
          JWT_SECRET_KEY: ci-test-secret
          GEMINI_API_KEY: test-key
          DATABASE_URL: postgresql+asyncpg://postgres:password@localhost:5432/mindbridge_test
```

### Test Run Summary (Expected)

| Test Suite | Count | Max Duration | Frequency |
|------------|-------|--------------|-----------|
| Unit tests | ~80 | 3 min | Every PR |
| Regression tests | ~40 | 2 min | Every PR |
| Performance tests | ~4 | 1 min | Every PR |
| Integration tests | ~20 | 5 min | Pre-staging deploy |
| Manual QA | 5 scenarios | 30 min | Pre-production release |
