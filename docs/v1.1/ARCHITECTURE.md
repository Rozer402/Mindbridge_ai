# MindBridge AI v1.1 — Architecture

**Theme: Intelligent Memory & Emotional Intelligence**  
**Status:** Design (pre-implementation)  
**Date:** 2026-07-10

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [v1.0 Architecture (Baseline)](#2-v10-architecture-baseline)
3. [v1.1 Architecture (Target)](#3-v11-architecture-target)
4. [New Components](#4-new-components)
5. [Data Flow Diagrams](#5-data-flow-diagrams)
6. [Memory Flow](#6-memory-flow)
7. [Emotion Pipeline](#7-emotion-pipeline)
8. [Retrieval Pipeline](#8-retrieval-pipeline)
9. [Existential vs Crisis Pipeline](#9-existential-vs-crisis-pipeline)
10. [Sequence Diagrams](#10-sequence-diagrams)
11. [Class Diagrams](#11-class-diagrams)
12. [Configuration Changes](#12-configuration-changes)
13. [Startup Sequence](#13-startup-sequence)

---

## 1. System Overview

MindBridge AI is a mental health support platform with a Next.js frontend, FastAPI backend, PostgreSQL persistent store, Redis conversation memory, and Google Gemini for language generation.

v1.1 adds the following to the service layer:
- `EmotionTagger` service (new singleton)
- `ImportanceScorer` utility (new module)
- `SummaryService` (new singleton)
- `TitleService` (new singleton)
- Extended `MemoryService` with `warm_load()` and `trim_by_importance()`
- Extended `MentalHealthEmbedder` with existential anchor vectors and emotion-aware retrieval

The API layer gains one new endpoint (`PATCH /api/v1/users/me`) and several additive response fields. No endpoints are removed or modified in a breaking way.

---

## 2. v1.0 Architecture (Baseline)

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                       │
│  state: Zustand  |  forms: React Hook Form + Zod             │
│  charts: Recharts  |  UI: Tailwind CSS, Radix UI             │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTPS / WSS
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ API Layer (/api/v1/)                                 │    │
│  │  auth.py   chat.py   mood.py   users.py              │    │
│  │  ws/chat_ws.py (WebSocket)                           │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Service Layer                                        │    │
│  │  ai_service.py       ← 9-step pipeline orchestrator │    │
│  │  embedder.py         ← MiniLM + corpus ops          │    │
│  │  classifier.py       ← PyTorch model definition     │    │
│  │  classifier_service.py ← model load + MC Dropout    │    │
│  │  crisis_service.py   ← keyword regex detection      │    │
│  │  memory_service.py   ← Redis rolling window         │    │
│  │  auth_service.py     ← JWT + bcrypt                 │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Data Layer                                           │    │
│  │  database.py  models/  migrations/                   │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────┬─────────────────────────┬──────────────┬──────────┘
           │                         │              │
           ▼                         ▼              ▼
     PostgreSQL 16              Redis 7        Google Gemini
  (persistent store)     (conversation memory)  (LLM generation)
```

**v1.0 AI pipeline steps:**
1. Sanitise → 2. Embed → 3. Relevance check → 3.5. Classify
→ 4. Crisis detect → 5. Few-shot retrieve → 6. Build prompt
→ 7. Generate → 8. Persist to Redis + PostgreSQL → 9. Return

---

## 3. v1.1 Architecture (Target)

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                       │
│  (no frontend changes in v1.1)                               │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTPS / WSS
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ API Layer (/api/v1/)  — additive changes only        │    │
│  │  auth.py   chat.py   mood.py   users.py (extended)   │    │
│  │  ws/chat_ws.py (WebSocket — warm_load added)         │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Service Layer — v1.1 additions shown in [NEW]        │    │
│  │                                                      │    │
│  │  ai_service.py         ← 11-step pipeline (updated) │    │
│  │  embedder.py           ← +existential anchors        │    │
│  │                          +emotion-aware retrieval    │    │
│  │  [NEW] emotion_tagger.py   ← Ekman 7-class tagger   │    │
│  │  [NEW] importance_scorer.py ← heuristic scorer      │    │
│  │  [NEW] summary_service.py  ← rolling summaries      │    │
│  │  [NEW] title_service.py    ← AI session titles      │    │
│  │  classifier.py         ← unchanged                  │    │
│  │  classifier_service.py ← unchanged                  │    │
│  │  crisis_service.py     ← +existential anchors       │    │
│  │  memory_service.py     ← +warm_load, +trim_by_imp   │    │
│  │  auth_service.py       ← unchanged                  │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Data Layer                                           │    │
│  │  database.py  models/ (5 new columns)  migrations/  │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────┬─────────────────────────┬──────────────┬──────────┘
           │                         │              │
           ▼                         ▼              ▼
     PostgreSQL 16              Redis 7        Google Gemini
  (+5 new columns            (+2 new fields   +summarization
   +migration 002)            per entry)       +title gen)
```

**v1.1 AI pipeline steps (updated):**
1. Sanitise
2. Embed
3. Relevance check
3.5. Classify
**3.6. Emotion tag [NEW]**
4. Crisis + existential detect [UPDATED]
5. Few-shot retrieve with emotion re-ranking [UPDATED]
6. Build prompt with emotion hint + session summary [UPDATED]
7. Generate
8. Persist (with emotion_tag + importance_score) [UPDATED]
**8.5. Background: generate title (first message only) [NEW]**
**8.6. Background: generate summary (every 20 messages) [NEW]**
9. Return (with emotion_tag) [UPDATED]

---

## 4. New Components

### 4.1 EmotionTagger (`emotion_tagger.py`)

**Responsibility:** Detect the primary emotional state of a user message using cosine similarity to pre-computed anchor emotion vectors. Runs inline (synchronously) in the AI pipeline. Returns a tag from the 7-class Ekman taxonomy or `None`.

**Design:**
- Stateless singleton, initialized once at startup.
- Accepts a pre-computed 384-dim embedding vector (reuses the vector from Step 2 — no additional model call).
- Returns `(emotion_tag: str | None, emotion_confidence: float)`.
- Threshold: `EMOTION_CONFIDENCE_THRESHOLD = 0.30` — below this, returns `(None, score)`.

**Anchor phrases (one per emotion class, encoded at startup):**

| Emotion | Anchor Phrase |
|---------|---------------|
| joy | "I feel happy and grateful today" |
| sadness | "I feel so sad and heartbroken" |
| fear | "I am terrified and scared about what might happen" |
| anger | "I am furious and enraged at this situation" |
| disgust | "This makes me feel sick and revolted" |
| surprise | "I can't believe this happened, I'm shocked" |
| neutral | "I want to talk about something that happened today" |

**Dependencies:** `embedder` (for `.model.encode()`), `numpy`, `sklearn.metrics.pairwise.cosine_similarity`.

---

### 4.2 ImportanceScorer (`importance_scorer.py`)

**Responsibility:** Compute a deterministic importance score (0.0–1.0) for a message entry at write time. Pure function — no I/O, no state.

**Scoring function signature:**
```
def compute_importance_score(
    content: str,
    is_crisis: bool,
    classifier_confidence: float,
    relevance_score: float,
) -> float
```

**Scoring table:**

| Condition | Points |
|-----------|--------|
| `is_crisis=True` | floor at 0.90 |
| `classifier_confidence >= 0.80` | +0.30 |
| `word_count(content) > 20` | +0.20 |
| `relevance_score >= 0.70` | +0.15 |
| contains "I feel", "I am", "my ", "I've" | +0.10 |
| `word_count(content) <= 2` (filler guard) | cap at 0.20 |

Result: `min(1.0, max(0.0, sum_of_points))`.

---

### 4.3 SummaryService (`summary_service.py`)

**Responsibility:** Generate rolling conversation summaries via Gemini. Executes as a background task. Stores result in `chat_sessions.session_summary`.

**Interface:**
```
async def maybe_generate_summary(
    session_id: uuid.UUID,
    message_count: int,
    db_session_factory: Callable,
) -> None
```

**Logic:**
- If `message_count % SUMMARY_TRIGGER_EVERY != 0`: return immediately (no-op).
- Fetch last 40 messages from PostgreSQL for this session.
- Build summarization prompt + call Gemini.
- On success: UPDATE `chat_sessions` SET `session_summary = ...`, `summary_updated_at = now()`.
- On any exception: log at WARNING level, return silently.

---

### 4.4 TitleService (`title_service.py`)

**Responsibility:** Generate an AI session title after the first message exchange. Executes as a background task. Stores result in `chat_sessions.title` and sets `title_generated = true`.

**Interface:**
```
async def maybe_generate_title(
    session_id: uuid.UUID,
    first_user_message: str,
    first_ai_response: str,
    is_crisis: bool,
    db_session_factory: Callable,
) -> None
```

**Logic:**
- If `is_crisis=True`: return immediately (no title generation for crisis sessions).
- Query `chat_sessions` — if `title_generated=True`: return (no-op for idempotency).
- Call Gemini with title generation prompt.
- Validate title: 4–10 words. On failure/invalid: use truncation fallback.
- UPDATE `chat_sessions` SET `title = ...`, `title_generated = true`.

---

## 5. Data Flow Diagrams

### 5.1 Normal Message Flow (v1.1)

```
User HTTP POST /api/v1/chat/message
         │
         ▼
chat.py::send_message()
         │
         ├─ [1] Resolve session (PostgreSQL)
         │
         ├─ [2] Load PostgreSQL history (fallback)
         │
         ├─ [3] warm_load Redis if Redis miss + PG has history
         │        └─ memory_service.warm_load(session_id, history)
         │
         ├─ [4] ai_service.process_message()
         │        │
         │        ├─ Step 1: Sanitise
         │        ├─ Step 2: Embed (MiniLM → 384-dim vec)
         │        ├─ Step 3: Relevance (cosine vs corpus)
         │        ├─ Step 3.5: Classify (MC Dropout × 20)
         │        ├─ Step 3.6: EmotionTag (cosine vs anchors)
         │        ├─ Step 4: Crisis + Existential detect
         │        │    └─ keyword check → embedding check (with existential guard)
         │        │       → classifier crisis check
         │        ├─ Step 5: Retrieve (category + emotion re-rank)
         │        ├─ Step 6: Build prompt
         │        │    ├─ static prefix
         │        │    ├─ session_summary (if non-null)
         │        │    ├─ emotion hint (if emotion_tag non-null)
         │        │    ├─ few-shot examples
         │        │    └─ Redis history (12 msgs) / PG fallback
         │        ├─ Step 7: Gemini generate
         │        ├─ Step 8: Redis append_turn (emotion_tag + importance_score)
         │        └─ Step 9: Return enriched dict
         │
         ├─ [5] Persist to PostgreSQL (user msg + AI msg)
         │        └─ with emotion_tag + importance_score on user msg
         │
         ├─ [6] Update session metadata (SQL, atomic)
         │
         ├─ [7] asyncio.create_task(title_service.maybe_generate_title(...))
         │        └─ runs after response is returned
         │
         ├─ [8] asyncio.create_task(summary_service.maybe_generate_summary(...))
         │        └─ runs after response is returned
         │
         └─ [9] Return ChatResponse to client
```

---

## 6. Memory Flow

### v1.0 Memory Flow (FIFO)
```
Write:  RPUSH → LTRIM (cap at 20) → EXPIRE
Read:   LRANGE -12 -1 (last 12 msgs)
Expire: 24h TTL reset on every write
Redis miss: fallback to PostgreSQL (for current request only)
```

### v1.1 Memory Flow (Importance-Aware + Warm Load)

```
Write:
  1. compute importance_score (ImportanceScorer)
  2. build entry: {role, content, category, confidence, is_crisis,
                    emotion_tag, importance_score, timestamp}
  3. RPUSH key entry
  4. LTRIM key -MAX_HISTORY -1
  5. If len(key) was just trimmed AND any evicted msg had score < 0.20:
       → trim_by_importance: re-read list, drop lowest-scoring
         entry not in the HISTORY_FOR_LLM window
  6. EXPIRE key TTL (from user preference)

Read:
  1. LRANGE key -HISTORY_FOR_LLM -1
  2. If result empty AND PostgreSQL has history:
       → warm_load(session_id, pg_history)
       → re-read from Redis

Redis schema per entry (v1.1):
{
  "role":             "user" | "assistant",
  "content":          str,
  "category":         str | null,
  "confidence":       float | null,
  "is_crisis":        bool,
  "emotion_tag":      str | null,          ← NEW
  "importance_score": float,               ← NEW
  "timestamp":        float
}
```

---

## 7. Emotion Pipeline

```
User Message (raw text)
        │
        ▼
  Step 2: Embed
  query_vec = embedder.embed(message)  ← 384-dim MiniLM vector
        │
        ▼
  Step 3.6: EmotionTag
  emotion_tagger.tag(query_vec)
        │
        ├─ For each of 7 anchor vectors:
        │    sim[emotion] = cosine(query_vec, anchor_vec)
        │
        ├─ best_emotion = argmax(sim)
        │  best_score   = max(sim)
        │
        ├─ if best_score >= EMOTION_CONFIDENCE_THRESHOLD (0.30):
        │    emotion_tag = best_emotion
        │  else:
        │    emotion_tag = None  (below threshold → neutral)
        │
        └─ return (emotion_tag, best_score)
        │
        ▼
  Step 6: Build Prompt
  if emotion_tag and not is_crisis:
      prompt += f"[Detected user emotion: {emotion_tag.upper()}]\n"
        │
        ▼
  Step 8: Persist
  message.emotion_tag = emotion_tag
  redis_entry["emotion_tag"] = emotion_tag
```

**Emotion → Valence mapping (derived, not stored):**
```
joy      → positive, high arousal
sadness  → negative, low arousal
fear     → negative, high arousal
anger    → negative, high arousal
disgust  → negative, medium arousal
surprise → ambiguous, high arousal
neutral  → ambiguous, low arousal
```

---

## 8. Retrieval Pipeline

### v1.0 Retrieval
```
query_vec
   │
   └─ get_few_shot_examples_by_category(query_vec, category)
         │
         ├─ if category known and len(category_corpus) >= TOP_K:
         │    → filter corpus to category, rank by cosine, return TOP_K
         └─ else:
              → rank full corpus by cosine, return TOP_K
```

### v1.1 Retrieval (Emotion-Aware)
```
query_vec + emotion_tag
   │
   └─ get_few_shot_examples_by_category_and_emotion(
           query_vec, category, emotion_tag
       )
         │
         ├─ Stage 1: get TOP_K × 2 candidates
         │    (same logic as v1.0, but doubled pool)
         │
         └─ Stage 2: re-rank by emotion alignment
               for each candidate:
                 adjusted = cosine_sim
                 if candidate.emotion_tag == user.emotion_tag:
                     adjusted += 0.15  (EMOTION_BONUS)
                 if valence(candidate.emotion_tag) == valence(user.emotion_tag):
                     adjusted += 0.05  (VALENCE_BONUS)
               sort by adjusted DESC, return TOP_K
         │
         ▼
   Falls back to v1.0 method when:
   - emotion_tag is None
   - no corpus entries have emotion_tag
   - category is "crisis" or "existential"
```

---

## 9. Existential vs Crisis Pipeline

### v1.0 Crisis Embedding Check
```
check_crisis_embedding(query_vec):
    sims = cosine(query_vec, crisis_embeddings)
    return max(sims) >= 0.70
```

### v1.1 Existential-Aware Check
```
check_crisis_embedding(query_vec):
    crisis_sim      = max(cosine(query_vec, crisis_embeddings))
    existential_sim = max(cosine(query_vec, existential_embeddings))

    if crisis_sim >= CRISIS_THRESHOLD (0.70):
        if existential_sim > crisis_sim - EXISTENTIAL_MARGIN (0.08):
            # Message semantically close to BOTH crisis and existential
            # → assume existential (safer assumption, keyword guard is still active)
            return (False, True)   # (is_crisis=False, is_existential=True)
        else:
            return (True, False)   # genuine crisis
    else:
        return (False, False)

ai_service.py Step 4:
    embedding_crisis, is_existential = embedder.check_crisis_embedding(query_vec)

    if not final_is_crisis and is_existential:
        predicted_category = "existential"
        # Step 6: inject EXISTENTIAL_RESPONSE_HINT into prompt
```

**Safety invariant:** Keyword layer (Layer A) always runs before embedding layer (Layer B). If keyword check fires → crisis protocol activates regardless of existential similarity.

---

## 10. Sequence Diagrams

### 10.1 Normal Chat Message (v1.1)

```
Client          chat.py         ai_service.py    memory_service   Gemini        PostgreSQL
  │                │                  │               │               │               │
  │─ POST ─────────▶                  │               │               │               │
  │                │─ get session ────────────────────────────────────────────────────▶
  │                │◀─ session ────────────────────────────────────────────────────────
  │                │─ get pg_history ─────────────────────────────────────────────────▶
  │                │◀─ pg_history ─────────────────────────────────────────────────────
  │                │─ get_history() ───────────────▶   │               │               │
  │                │◀─ [] (Redis miss) ────────────────│               │               │
  │                │─ warm_load(pg_history) ───────────▶               │               │
  │                │─ process_message() ──────────▶    │               │               │
  │                │                 │─ embed ─────    │               │               │
  │                │                 │─ classify ──    │               │               │
  │                │                 │─ emotion tag    │               │               │
  │                │                 │─ crisis check   │               │               │
  │                │                 │─ retrieve ──    │               │               │
  │                │                 │─ build prompt   │               │               │
  │                │                 │─ generate ──────────────────────▶               │
  │                │                 │◀─ ai_text ──────────────────────               │
  │                │                 │─ append_turn() ────────────────▶               │
  │                │◀─ ai_result ─────                 │               │               │
  │                │─ INSERT user msg + ai msg ────────────────────────────────────────▶
  │                │─ UPDATE session ──────────────────────────────────────────────────▶
  │                │─ create_task(title_service) [background]          │               │
  │                │─ create_task(summary_service) [background]        │               │
  │◀─ ChatResponse ─                  │               │               │               │
  │                │                  │    [background: title gen]     │               │
  │                │                  │─ Gemini call ──────────────────▶               │
  │                │                  │◀─ title ───────────────────────               │
  │                │                  │─ UPDATE session.title ─────────────────────────▶
```

---

### 10.2 Summary Generation Trigger (every 20 messages)

```
summary_service.py              PostgreSQL              Gemini
       │                            │                      │
       │─ SELECT msgs (last 40) ────▶                      │
       │◀─ messages ────────────────                       │
       │─ build summary prompt                             │
       │─ generate_content() ──────────────────────────────▶
       │◀─ summary_text ────────────────────────────────────
       │─ UPDATE chat_sessions ─────▶
       │   SET session_summary = ...,
       │       summary_updated_at = now()
```

---

### 10.3 Redis Warm-Load Flow

```
chat.py          memory_service        PostgreSQL
   │                   │                    │
   │─ get_history() ───▶                    │
   │◀─ [] (empty) ──────                   │
   │ (pg_history is non-empty)              │
   │─ warm_load(pg_history) ─▶             │
   │                   │ RPUSH × n entries  │
   │                   │ LTRIM -20 -1       │
   │                   │ EXPIRE TTL         │
   │◀─ done ───────────                    │
   │─ process_message() (will use Redis now)│
```

---

## 11. Class Diagrams

### 11.1 Service Layer (v1.1)

```
┌─────────────────────────────────┐
│      MentalHealthEmbedder       │
├─────────────────────────────────┤
│ model: SentenceTransformer      │
│ corpus_data: list[dict]         │
│ corpus_embeddings: ndarray      │
│ crisis_embeddings: ndarray      │
│ existential_embeddings: ndarray │  ← NEW
│ _loaded: bool                   │
├─────────────────────────────────┤
│ initialize()                    │
│ load_corpus(path)               │
│ embed(text) → ndarray           │
│ check_relevance() → (bool,float)│
│ check_crisis_embedding()        │  ← UPDATED: returns (bool,bool)
│   → (is_crisis, is_existential) │
│ get_few_shot_examples()         │
│ get_few_shot_examples_by_cat()  │
│ get_few_shot_by_cat_and_emotion()│  ← NEW
└─────────────────────────────────┘

┌───────────────────────────────────┐
│          EmotionTagger            │  ← NEW
├───────────────────────────────────┤
│ anchor_embeddings: dict[str,ndarray]│
│ THRESHOLD: float = 0.30           │
│ _loaded: bool                     │
├───────────────────────────────────┤
│ initialize(model)                 │
│ tag(query_vec) → (str|None, float)│
└───────────────────────────────────┘

┌───────────────────────────────────┐
│         ImportanceScorer          │  ← NEW
├───────────────────────────────────┤
│ (stateless — pure functions)      │
├───────────────────────────────────┤
│ compute_score(content, is_crisis, │
│   conf, relevance) → float        │
│ is_filler(content) → bool         │
└───────────────────────────────────┘

┌───────────────────────────────────┐
│          MemoryService            │  ← EXTENDED
├───────────────────────────────────┤
│ _client: aioredis.Redis | None    │
│ _available: bool                  │
├───────────────────────────────────┤
│ initialize()                      │
│ close()                           │
│ get_history(session_id, limit)    │
│ append_message(...)               │
│ append_turn(...)     ← +emotion + importance │
│ warm_load(session_id, messages)   │  ← NEW
│ trim_by_importance(session_id)    │  ← NEW
│ clear_session(session_id)         │
│ ping() → bool                     │
└───────────────────────────────────┘

┌───────────────────────────────────┐
│          SummaryService           │  ← NEW
├───────────────────────────────────┤
│ TRIGGER_EVERY: int = 20           │
│ SUMMARY_PROMPT: str               │
├───────────────────────────────────┤
│ maybe_generate_summary(           │
│   session_id, message_count,      │
│   db_factory) → None              │
└───────────────────────────────────┘

┌───────────────────────────────────┐
│           TitleService            │  ← NEW
├───────────────────────────────────┤
│ TITLE_PROMPT: str                 │
│ MIN_WORDS: int = 4                │
│ MAX_WORDS: int = 10               │
├───────────────────────────────────┤
│ maybe_generate_title(             │
│   session_id, first_user_msg,     │
│   first_ai_resp, is_crisis,       │
│   db_factory) → None              │
└───────────────────────────────────┘
```

### 11.2 Data Models (v1.1)

```
┌─────────────────────────────────────┐
│              User                   │
├─────────────────────────────────────┤
│ id: UUID (PK)                       │
│ email: str                          │
│ hashed_password: str                │
│ full_name: str | None               │
│ is_verified: bool                   │
│ is_active: bool                     │
│ emergency_email: str | None         │
│ memory_ttl_preference: str | None   │  ← NEW ('24h'|'72h'|'7d'|'session')
│ created_at: datetime                │
│ updated_at: datetime                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│           ChatSession               │
├─────────────────────────────────────┤
│ id: UUID (PK)                       │
│ user_id: UUID (FK → users)          │
│ title: str                          │
│ title_generated: bool               │  ← NEW
│ message_count: int                  │
│ crisis_flagged: bool                │
│ session_summary: str | None         │  ← NEW
│ summary_updated_at: datetime | None │  ← NEW
│ started_at: datetime                │
│ ended_at: datetime | None           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│              Message                │
├─────────────────────────────────────┤
│ id: UUID (PK)                       │
│ session_id: UUID (FK → chat_sessions)│
│ role: str ('user'|'assistant')      │
│ content: str                        │
│ relevance_score: float | None       │
│ is_crisis: bool                     │
│ emotion_tag: str | None             │  ← NEW
│ importance_score: float             │  ← NEW (default 0.5)
│ created_at: datetime                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│              MoodLog                │
├─────────────────────────────────────┤
│ id: UUID (PK)                       │
│ user_id: UUID (FK → users)          │
│ mood_score: int (1–10)              │
│ mood_label: str | None              │
│ notes: str | None                   │
│ logged_at: datetime                 │
└─────────────────────────────────────┘
```

---

## 12. Configuration Changes

New settings added to `app/config.py` (`Settings` class):

```python
# FR-01 Emotion Tagging
EMOTION_CONFIDENCE_THRESHOLD: float = 0.30

# FR-02 Importance Scoring
IMPORTANCE_PIN_THRESHOLD: float = 0.80    # messages above this are never evicted
IMPORTANCE_EVICT_THRESHOLD: float = 0.20  # messages below this are evict candidates

# FR-04 Rolling Summaries
SUMMARY_TRIGGER_EVERY: int = 20           # trigger every N user messages
SUMMARIZATION_PROMPT: str = "..."         # see FR-04 specification

# FR-05 Existential Guard
EXISTENTIAL_MARGIN: float = 0.08         # existential vs crisis disambiguation margin

# FR-06 AI Titles
TITLE_MIN_WORDS: int = 4
TITLE_MAX_WORDS: int = 10
TITLE_GENERATION_PROMPT: str = "..."      # see FR-06 specification

# FR-07 Memory TTL Allowlist
MEMORY_TTL_ALLOWLIST: list[str] = ["24h", "72h", "7d", "session"]
```

No existing settings are removed or renamed.

---

## 13. Startup Sequence

Updated `main.py` lifespan order:

```
1. embedder.initialize()
     └─ loads all-MiniLM-L6-v2
2. embedder.load_corpus(CORPUS_PATH)
     └─ pre-computes corpus embeddings
     └─ pre-computes crisis_embeddings
     └─ [NEW] pre-computes existential_embeddings (10 anchors)
3. emotion_tagger.initialize(embedder.model)
     └─ [NEW] pre-computes 7 emotion anchor embeddings
4. classifier_service.initialize()
     └─ loads classifier_weights.pt (non-fatal)
5. _initialize_gemini()
     └─ configures Gemini API
6. memory_service.initialize()
     └─ connects to Redis (non-fatal)
```

All steps are wrapped in `try/except`. Failure in steps 3 or 6 degrades gracefully:
- `emotion_tagger` fails → `emotion_tag=null` for all requests.
- `memory_service` fails → Redis memory disabled; PostgreSQL fallback active.

The `/health` endpoint reports:
```json
{
  "status": "healthy",
  "embedder_loaded": true,
  "corpus_size": 1247,
  "existential_anchors_loaded": true,
  "emotion_tagger_loaded": true,
  "classifier_loaded": true,
  "redis_connected": true,
  "memory_ttl_hours": 24,
  "memory_warm_load_enabled": true
}
```
