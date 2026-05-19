# 🧠 MindBridge AI
## Mental Health Support Platform — Final Year Project Blueprint v2.0

| Field | Details |
|---|---|
| **Project Title** | MindBridge AI – Mental Health Support Platform |
| **Tech Stack** | Next.js 14, FastAPI, PostgreSQL, Google Gemini API |
| **Research Foundation** | IEEE ICDSBS 2025 — Few-Shot Prompting + Vector Embeddings |
| **Version** | v2.0 — Realistic FYP-Scoped Blueprint |
| **Target** | Final Year Student — Solo or 2-person team |
| **Timeline** | 8–10 Weeks |

---

# 1. Project Overview

## 1.1 What Is MindBridge AI?

MindBridge AI is a mental health support chatbot that uses **Generative AI**, **sentence embeddings**, and **few-shot prompting** to deliver empathetic, contextual conversations. It detects whether a user's message is mental-health-related, retrieves semantically similar examples, and generates warm, supportive responses using Google Gemini.

This is **not** a medical application. It is an AI research prototype demonstrating the application of NLP techniques to mental wellness — grounded in published IEEE research.

## 1.2 Research Foundation

> **Paper:** *"Mental Health Support Using Gen-AI Shot Prompting Technique and Vector Embeddings"*
> **Authors:** Dr. Ponmagal R.S. et al.
> **Conference:** IEEE ICDSBS 2025

**Key Innovations from the Paper:**
- Sentence Transformer embeddings (`all-MiniLM-L6-v2`, 384-dim) for semantic relevance detection
- Few-shot prompting with dynamically retrieved context examples
- Cosine similarity threshold of **0.4** for off-topic query filtering
- **85% classification accuracy** on mental health dialogue dataset
- Outperforms zero-shot prompting by ~18% in response relevance

## 1.3 Project Goals

| Goal | Measurable Outcome |
|---|---|
| Relevant query detection | Cosine similarity ≥ 0.4 for mental health queries, < 0.4 for off-topic |
| AI response quality | User evaluation score ≥ 4/5 in empathy & helpfulness |
| Crisis detection | 100% recall on 25 crisis keyword test cases |
| System performance | API response < 3s for 95% of messages |
| UI completeness | Chat, Mood Tracker, Dashboard — fully functional |

## 1.4 What Makes This FYP-Worthy?

1. **Novel AI pipeline** — not just calling an LLM, but a multi-stage pipeline: embed → filter → retrieve → generate
2. **IEEE research implementation** — direct applied research contribution
3. **Real-world problem** — mental health is a pressing societal issue
4. **Complete system** — frontend + backend + AI + database + evaluation
5. **Measurable results** — accuracy, response quality, crisis recall can all be tested

---

# 2. Scoped Technology Stack

> **Philosophy:** Choose tools you can master, not tools that impress on paper. Every technology below has a clear reason for being here.

## 2.1 Frontend

| Technology | Version | Why |
|---|---|---|
| Next.js | 14 (App Router) | Industry-standard React framework, great for full-stack |
| TypeScript | 5 | Type safety reduces bugs during development |
| Tailwind CSS | 3.4 | Fast styling, no CSS files to manage |
| shadcn/ui | Latest | Pre-built accessible components |
| Recharts | 2 | Simple charting for mood dashboard |
| React Hook Form + Zod | Latest | Form handling and validation |
| Axios | Latest | HTTP client for API calls |
| Socket.IO Client | 4 | Real-time streaming chat |

## 2.2 Backend

| Technology | Version | Why |
|---|---|---|
| Python | 3.11 | Best ML/AI library ecosystem |
| FastAPI | 0.110 | Fast, async, auto-generates API docs |
| sentence-transformers | Latest | Core AI — `all-MiniLM-L6-v2` embeddings |
| scikit-learn | Latest | Cosine similarity computation |
| Google Generative AI SDK | Latest | Gemini 1.5 Flash — free tier, 1M context |
| SQLAlchemy | 2.0 | ORM — async database access |
| Alembic | Latest | Database migrations |
| python-jose | Latest | JWT auth tokens |
| bcrypt | Latest | Password hashing |
| NumPy | Latest | Vector operations |

## 2.3 Infrastructure (Simplified)

| Component | Choice | Why NOT the complex alternative |
|---|---|---|
| Database | PostgreSQL (local / Supabase) | No need for Redis — simple is fine for FYP |
| Vector Storage | **NumPy in-memory + JSON file** | No Qdrant needed — 200 vectors fit in memory |
| AI Generation | Google Gemini 1.5 Flash | Free tier: 15 RPM, 1M tokens/day — plenty |
| Auth | JWT (access + refresh tokens) | No OAuth complexity needed |
| Deployment | Vercel (frontend) + Railway (backend) | Free tiers, simple setup |
| Real-time | FastAPI WebSocket | No Socket.IO server needed on backend |

> **Why no Redis, Celery, Qdrant, Three.js, Prometheus?**
> These are production-grade infrastructure tools. For an FYP demo with 1-10 users, they add weeks of complexity with zero academic value. Your evaluators care about your AI pipeline, not your DevOps setup.

---

# 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                          │
│                                                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│   │  Landing │  │   Chat   │  │Dashboard │  │  Mood    │  │
│   │   Page   │  │ Interface│  │          │  │ Tracker  │  │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        └─────────────┴──────────────┴──────────────┘        │
│                    Next.js 14 (Vercel)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend (Railway)                   │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │  Auth API   │  │  Chat API   │  │  Mood / Journal API  │ │
│  └─────────────┘  └──────┬──────┘  └──────────────────────┘ │
│                          │                                   │
│              ┌───────────▼──────────────┐                   │
│              │      AI Pipeline          │                   │
│              │                          │                   │
│              │  1. Embed message        │                   │
│              │     (all-MiniLM-L6-v2)   │                   │
│              │  2. Cosine similarity    │                   │
│              │     vs corpus (NumPy)    │                   │
│              │  3. Crisis check         │                   │
│              │  4. Retrieve top-3       │                   │
│              │     few-shot examples    │                   │
│              │  5. Build prompt         │                   │
│              │  6. Gemini 1.5 Flash     │                   │
│              │  7. Stream response      │                   │
│              └──────────────────────────┘                   │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              PostgreSQL (Supabase Free Tier)                  │
│                                                              │
│   users | chat_sessions | messages | mood_logs | journals    │
└─────────────────────────────────────────────────────────────┘
```

---

# 4. Complete Folder Structure

## 4.1 Repository Root

```
mindbridge-ai/
├── frontend/                  → Next.js 14 application
├── backend/                   → FastAPI Python application
├── docs/                      → Report diagrams, API docs
├── evaluation/                → Test scripts, evaluation data
├── .github/
│   └── workflows/
│       └── ci.yml             → Basic CI (lint + test)
├── docker-compose.yml         → Local PostgreSQL only
└── README.md
```

## 4.2 Frontend Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx              → Sidebar + nav wrapper
│   │   ├── page.tsx                → Dashboard home
│   │   ├── chat/
│   │   │   └── page.tsx            → Main AI chat
│   │   ├── mood/
│   │   │   └── page.tsx            → Mood tracker
│   │   └── settings/
│   │       └── page.tsx
│   ├── (landing)/
│   │   └── page.tsx                → Public landing page
│   ├── api/
│   │   └── auth/
│   │       └── [...nextauth]/
│   │           └── route.ts
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                         → shadcn/ui components
│   ├── chat/
│   │   ├── ChatWindow.tsx          → Chat container
│   │   ├── MessageBubble.tsx       → Single message component
│   │   ├── TypingIndicator.tsx     → 3-dot animation
│   │   ├── ChatInput.tsx           → Input bar + send
│   │   ├── QuickReplies.tsx        → Suggested reply chips
│   │   └── CrisisAlert.tsx         → Crisis hotline overlay
│   ├── dashboard/
│   │   ├── MoodChart.tsx           → Recharts line chart
│   │   ├── SessionCard.tsx         → Past session card
│   │   └── WellnessScore.tsx       → Score display
│   └── layout/
│       ├── Sidebar.tsx
│       ├── TopNav.tsx
│       └── MobileNav.tsx
├── hooks/
│   ├── useChat.ts                  → WebSocket hook
│   └── useMoodTracker.ts
├── lib/
│   ├── api.ts                      → Axios instance
│   └── utils.ts
├── store/
│   └── chatStore.ts                → Zustand state
├── types/
│   ├── chat.types.ts
│   └── user.types.ts
├── .env.local.example
├── next.config.js
├── tailwind.config.ts
└── package.json
```

## 4.3 Backend Structure

```
backend/
├── app/
│   ├── main.py                     → FastAPI init, CORS, startup
│   ├── config.py                   → Pydantic settings
│   ├── database.py                 → SQLAlchemy async engine
│   ├── dependencies.py             → get_db, get_current_user
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       ├── auth.py             → /auth/register, /login, /refresh
│   │       ├── chat.py             → /chat/message, /sessions
│   │       ├── mood.py             → /mood/log, /history
│   │       └── users.py            → /users/me
│   ├── ws/
│   │   └── chat_ws.py              → WebSocket /ws/chat/{session_id}
│   ├── models/
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── message.py
│   │   └── mood_log.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── mood.py
│   │   └── user.py
│   └── services/
│       ├── ai_service.py           → Main AI orchestration
│       ├── embedder.py             → SentenceTransformer wrapper
│       ├── crisis_service.py       → Crisis detection
│       ├── auth_service.py         → JWT + bcrypt
│       └── corpus_loader.py        → Load & embed corpus at startup
├── corpus/
│   └── mental_health_corpus.json   → 200+ curated QA pairs
├── migrations/                     → Alembic
├── tests/
│   ├── test_ai_pipeline.py
│   ├── test_auth.py
│   ├── test_chat.py
│   └── test_crisis.py
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

# 5. Database Schema

```sql
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── USERS ────────────────────────────────────────────────────
CREATE TABLE users (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email            VARCHAR(255) UNIQUE NOT NULL,
  hashed_password  VARCHAR(255) NOT NULL,
  full_name        VARCHAR(255),
  is_verified      BOOLEAN DEFAULT false,
  is_active        BOOLEAN DEFAULT true,
  emergency_email  VARCHAR(255),          -- optional crisis contact
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── CHAT SESSIONS ────────────────────────────────────────────
CREATE TABLE chat_sessions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  title            VARCHAR(255) DEFAULT 'New Conversation',
  message_count    INTEGER DEFAULT 0,
  crisis_flagged   BOOLEAN DEFAULT false,
  started_at       TIMESTAMPTZ DEFAULT NOW(),
  ended_at         TIMESTAMPTZ
);

-- ── MESSAGES ─────────────────────────────────────────────────
CREATE TABLE messages (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role             VARCHAR(20) NOT NULL,   -- 'user' | 'assistant'
  content          TEXT NOT NULL,
  relevance_score  FLOAT,                  -- cosine similarity score
  is_crisis        BOOLEAN DEFAULT false,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── MOOD LOGS ────────────────────────────────────────────────
CREATE TABLE mood_logs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  mood_score       INTEGER NOT NULL CHECK (mood_score BETWEEN 1 AND 10),
  mood_label       VARCHAR(50),            -- 'anxious','calm','sad','happy'
  notes            TEXT,
  logged_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_mood_logs_user   ON mood_logs(user_id);
CREATE INDEX idx_sessions_user    ON chat_sessions(user_id);
```

---

# 6. AI Pipeline — Core Design

## 6.1 Message Processing Flow (Step by Step)

```
INPUT: User types a message

STEP 1 ── Sanitize
          Strip HTML tags, trim whitespace, max 1000 chars

STEP 2 ── Embed
          all-MiniLM-L6-v2 → 384-dim normalized vector

STEP 3 ── Relevance Check
          Compute cosine similarity against all corpus vectors (NumPy)
          max_score = max(similarities)
          IF max_score < 0.4 → return off-topic redirect message (STOP)

STEP 4 ── Crisis Detection
          Check for 25+ crisis keywords in message text
          OR cosine similarity to crisis-labeled corpus vectors > 0.7
          IF crisis → return crisis response with hotline numbers (STOP)

STEP 5 ── Few-Shot Retrieval
          Top 3 corpus entries by cosine similarity = dynamic examples

STEP 6 ── Build Prompt
          system_prompt
          + 2 static examples (always included)
          + 3 dynamic examples (retrieved above)
          + last 8 messages from session (context window)
          + current user message

STEP 7 ── Generate
          Call Gemini 1.5 Flash API (streaming=True)
          Stream tokens back via WebSocket

STEP 8 ── Persist
          Save user message + AI response to PostgreSQL
          Update session message_count

OUTPUT: Streamed AI response tokens → frontend renders in real-time
```

## 6.2 Embedder Class

```python
# backend/app/services/embedder.py

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from pathlib import Path

class MentalHealthEmbedder:
    MODEL_NAME = "all-MiniLM-L6-v2"
    RELEVANCE_THRESHOLD = 0.4   # From IEEE paper
    TOP_K = 3                   # Few-shot examples to retrieve
    CRISIS_THRESHOLD = 0.7      # High similarity to crisis vectors

    def __init__(self):
        self.model = SentenceTransformer(self.MODEL_NAME)
        self.corpus_data: list[dict] = []
        self.corpus_embeddings: np.ndarray = None
        self.crisis_embeddings: np.ndarray = None

    def load_corpus(self, corpus_path: str):
        """Load corpus JSON and pre-compute all embeddings at startup."""
        with open(corpus_path) as f:
            data = json.load(f)

        self.corpus_data = data
        contexts = [item["context"] for item in data]
        self.corpus_embeddings = self.model.encode(
            contexts, normalize_embeddings=True, show_progress_bar=True
        )

        # Separate crisis embeddings for faster lookup
        crisis_items = [d for d in data if d.get("category") == "crisis"]
        if crisis_items:
            self.crisis_embeddings = self.model.encode(
                [c["context"] for c in crisis_items],
                normalize_embeddings=True
            )

        print(f"[Embedder] Loaded {len(data)} corpus entries.")

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode([text], normalize_embeddings=True)[0]

    def check_relevance(self, query_vec: np.ndarray) -> tuple[bool, float]:
        """Returns (is_relevant, max_similarity_score)"""
        sims = cosine_similarity([query_vec], self.corpus_embeddings)[0]
        max_sim = float(np.max(sims))
        return max_sim >= self.RELEVANCE_THRESHOLD, max_sim

    def check_crisis_embedding(self, query_vec: np.ndarray) -> bool:
        """Embedding-based crisis check (complements keyword check)."""
        if self.crisis_embeddings is None:
            return False
        sims = cosine_similarity([query_vec], self.crisis_embeddings)[0]
        return float(np.max(sims)) >= self.CRISIS_THRESHOLD

    def get_few_shot_examples(self, query_vec: np.ndarray) -> list[dict]:
        """Retrieve top-K most semantically similar corpus entries."""
        sims = cosine_similarity([query_vec], self.corpus_embeddings)[0]
        top_indices = np.argsort(sims)[::-1][:self.TOP_K]
        return [self.corpus_data[i] for i in top_indices]


# Singleton — loaded once at FastAPI startup
embedder = MentalHealthEmbedder()
```

## 6.3 AI Service (Orchestrator)

```python
# backend/app/services/ai_service.py

import google.generativeai as genai
from .embedder import embedder
from .crisis_service import is_crisis_message, CRISIS_RESPONSE

SYSTEM_PROMPT = """You are MindBridge, a compassionate AI mental health companion.
Your role is to provide empathetic, supportive, non-judgmental responses.

Rules:
- Always validate the user's feelings before offering perspective
- Use open-ended questions to encourage reflection
- NEVER diagnose or prescribe medication
- Always recommend professional help for persistent issues
- Keep tone warm, calm, and supportive
- If unsure, ask a gentle clarifying question
- Responses should be 2-4 sentences unless user needs more
"""

STATIC_EXAMPLES = [
    {
        "user": "I feel overwhelmed and don't know what to do.",
        "assistant": "That sounds really exhausting — feeling overwhelmed takes a lot out of you. You don't have to figure everything out at once. Can you tell me what's weighing on you the most right now?"
    },
    {
        "user": "I've been anxious about everything lately.",
        "assistant": "Anxiety can be so consuming, especially when it feels like it's everywhere at once. You're not alone in this feeling. What situation feels most pressing to you today?"
    }
]

OFF_TOPIC_RESPONSE = (
    "I'm here specifically to support your mental and emotional wellbeing. "
    "It sounds like your question might be about something else — I may not be "
    "the best resource for that. Is there something on your mind emotionally "
    "that I can help with?"
)


async def process_message(
    user_message: str,
    session_history: list[dict]
) -> dict:
    """
    Full AI pipeline. Returns:
    {
        "response": str,
        "is_crisis": bool,
        "is_relevant": bool,
        "relevance_score": float,
        "few_shot_count": int
    }
    """
    # Step 1: Embed
    query_vec = embedder.embed(user_message)

    # Step 2: Relevance check
    is_relevant, relevance_score = embedder.check_relevance(query_vec)
    if not is_relevant:
        return {
            "response": OFF_TOPIC_RESPONSE,
            "is_crisis": False,
            "is_relevant": False,
            "relevance_score": relevance_score,
            "few_shot_count": 0
        }

    # Step 3: Crisis detection
    if is_crisis_message(user_message) or embedder.check_crisis_embedding(query_vec):
        return {
            "response": CRISIS_RESPONSE,
            "is_crisis": True,
            "is_relevant": True,
            "relevance_score": relevance_score,
            "few_shot_count": 0
        }

    # Step 4: Retrieve dynamic few-shot examples
    examples = embedder.get_few_shot_examples(query_vec)

    # Step 5: Build messages for Gemini
    messages = []

    # Static examples
    for ex in STATIC_EXAMPLES:
        messages.append({"role": "user", "parts": [ex["user"]]})
        messages.append({"role": "model", "parts": [ex["assistant"]]})

    # Dynamic examples
    for ex in examples:
        messages.append({"role": "user", "parts": [ex["context"]]})
        messages.append({"role": "model", "parts": [ex["response"]]})

    # Session history (last 8 messages)
    for msg in session_history[-8:]:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [msg["content"]]})

    # Current message
    messages.append({"role": "user", "parts": [user_message]})

    # Step 6: Call Gemini
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(messages)
    ai_text = response.text

    return {
        "response": ai_text,
        "is_crisis": False,
        "is_relevant": True,
        "relevance_score": relevance_score,
        "few_shot_count": len(examples)
    }
```

## 6.4 Crisis Detection

```python
# backend/app/services/crisis_service.py

CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "don't want to live", "no reason to live", "better off dead",
    "self harm", "self-harm", "hurt myself", "cutting myself",
    "overdose", "take pills", "can't go on", "give up on life",
    "nobody cares if i die", "worthless", "hopeless", "no point living"
]

CRISIS_RESPONSE = """I hear you, and I'm really glad you reached out. \
What you're feeling right now is serious, and you deserve immediate support \
from someone trained to help.

Please reach out right now:
• **iCall (India):** 9152987821
• **Vandrevala Foundation:** 1860-2662-345 (24/7, free)
• **NIMHANS Helpline:** 080-46110007
• **SNEHI:** 044-24640050
• **International:** https://www.findahelpline.com

You are not alone, and this feeling will not last forever. \
Are you safe right now?"""


def is_crisis_message(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in CRISIS_KEYWORDS)
```

---

# 7. Mental Health Corpus

## 7.1 Corpus Structure

```json
[
  {
    "id": "mh_001",
    "category": "anxiety",
    "context": "I feel anxious all the time and can't relax",
    "response": "Living with constant anxiety is genuinely exhausting, and your feelings are completely valid. Can you tell me what situations tend to make the anxiety feel strongest? Understanding your triggers can be the first step toward managing them.",
    "keywords": ["anxious", "anxiety", "relax", "tension", "worry"]
  },
  {
    "id": "mh_002",
    "category": "depression",
    "context": "I have no motivation and feel empty inside",
    "response": "That feeling of emptiness is one of the hardest things to carry. You're not broken — what you're describing is something many people experience. Have you been able to talk to anyone else about how you've been feeling?",
    "keywords": ["motivation", "empty", "numb", "depressed", "hollow"]
  },
  {
    "id": "crisis_001",
    "category": "crisis",
    "context": "I don't want to be here anymore and I've been thinking about hurting myself",
    "response": "CRISIS",
    "keywords": ["hurt myself", "don't want to be here", "crisis"]
  }
]
```

## 7.2 Corpus Categories & Minimum Counts

| Category | Min. Pairs | Sample Topics |
|---|---|---|
| Anxiety | 35 pairs | General anxiety, social anxiety, panic attacks, worrying, exam anxiety |
| Depression | 35 pairs | Low mood, emptiness, hopelessness, loss of interest, academic pressure |
| Stress | 25 pairs | Work/study stress, deadline pressure, family conflict |
| Sleep Issues | 20 pairs | Insomnia, nightmares, fatigue, irregular sleep |
| Loneliness | 20 pairs | Social isolation, feeling misunderstood, missing connection |
| Self-Esteem | 20 pairs | Worthlessness, comparison, imposter syndrome |
| Grief | 15 pairs | Loss, bereavement, moving on, acceptance |
| Anger | 15 pairs | Frustration, rage, emotional regulation |
| Relationships | 15 pairs | Conflict, breakups, trust issues |
| Crisis | 15 pairs | ALL trigger crisis escalation — suicidal ideation, self-harm |
| **TOTAL** | **215+ pairs** | |

## 7.3 Where to Source Corpus Data

1. **CounselChat Dataset** — real therapist Q&A pairs (publicly available)
2. **EmpatheticDialogues** (Facebook Research) — 25K empathetic conversations
3. **Daily Dialog Dataset** — for general empathetic conversation patterns
4. **Manual curation** — write 30–50 pairs yourself for local relevance (Indian context, academic stress, etc.)

> **Important for your FYP report:** Document how you curated and validated the corpus. This is a research contribution.

---

# 8. Complete API Specification

## 8.1 Authentication Endpoints

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| POST | `/api/v1/auth/register` | `{ email, password, full_name }` | `{ user, access_token, refresh_token }` |
| POST | `/api/v1/auth/login` | `{ email, password }` | `{ user, access_token, refresh_token }` |
| POST | `/api/v1/auth/refresh` | `{ refresh_token }` | `{ access_token }` |
| POST | `/api/v1/auth/logout` | Bearer token | `{ message }` |

## 8.2 Chat Endpoints

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| POST | `/api/v1/chat/message` | `{ message, session_id? }` | `{ response, is_crisis, relevance_score, session_id }` |
| GET | `/api/v1/chat/sessions` | — | `[{ id, title, message_count, started_at }]` |
| GET | `/api/v1/chat/sessions/{id}/messages` | — | `[{ role, content, created_at }]` |
| DELETE | `/api/v1/chat/sessions/{id}` | — | `{ message }` |
| WS | `/ws/chat/{session_id}` | Token in query param | Streamed tokens |

## 8.3 Mood Endpoints

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| POST | `/api/v1/mood/log` | `{ mood_score, mood_label, notes }` | `{ id, mood_score, logged_at }` |
| GET | `/api/v1/mood/history` | Query: `?days=30` | `[{ mood_score, mood_label, logged_at }]` |
| GET | `/api/v1/mood/stats` | — | `{ avg_score, most_common_label, trend }` |

## 8.4 User Endpoints

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| GET | `/api/v1/users/me` | — | `{ id, email, full_name }` |
| PATCH | `/api/v1/users/me` | `{ full_name, emergency_email }` | `{ user }` |
| DELETE | `/api/v1/users/me` | — | `{ message }` |

---

# 9. Frontend UI Specification

## 9.1 Landing Page `/`

**Goal:** Clearly explain the app, build trust, drive registration.

- **Hero:** Clean centered layout, headline *"Your Mental Wellness Companion"*, subtitle, two CTAs: *"Start Free"* + *"Learn How It Works"*
- **Features Grid:** 3×2 card grid — AI Chat, Mood Tracking, Crisis Support, Private & Secure, 24/7 Available, Research-Backed
- **How It Works:** 3-step horizontal timeline — Sign Up → Talk to MindBridge → Track Your Wellbeing
- **Trust Band:** "Built on IEEE Research" | "No Personal Data Sold" | "India Hotlines Built-in"
- **Footer:** Crisis hotline numbers prominently displayed

## 9.2 Chat Interface `/dashboard/chat`

The centerpiece of the application.

- **Layout:** Sidebar (session list, 240px) + Main chat area
- **Message Bubbles:**
  - User: right-aligned, indigo/violet background, white text
  - AI: left-aligned, white card, subtle shadow, avatar icon
- **Streaming:** Typewriter effect as tokens arrive via WebSocket
- **Typing Indicator:** Animated 3-dot pulse while AI generates
- **Quick Replies:** 3–4 chip suggestions after each AI message
- **Session Starters:** Empty state shows prompt cards — *"I'm feeling anxious"*, *"Work is overwhelming me"*, *"I can't sleep"*
- **Off-topic Card:** Gentle redirect if query isn't mental-health-related (relevance_score < 0.4)
- **Crisis Overlay:** Full-screen overlay with hotline numbers, red border, cannot be dismissed without confirmation
- **Relevance Badge:** Small badge on AI message showing similarity score (helpful for evaluation)

## 9.3 Dashboard `/dashboard`

- **Wellness Score:** Average mood over last 7 days displayed as a number with trend arrow
- **Mood Chart:** Recharts AreaChart — 30-day mood history
- **Recent Sessions:** List of last 5 chats with date + message count
- **Quick Actions:** *Log Mood* and *Start Chat* buttons

## 9.4 Mood Tracker `/dashboard/mood`

- **Log Modal:** Slider 1–10 with emoji labels, mood label selector (5 options), optional notes field
- **History:** List of mood logs with date, score, label
- **Chart:** Line chart of mood scores over time
- **Weekly Average:** Simple stats card

---

# 10. Security Checklist

```
✅ Passwords: bcrypt with cost factor 12 — never store plaintext
✅ JWT: access token 30 min, refresh token 30 days, store in httpOnly cookie
✅ CORS: whitelist only your frontend URL — no wildcard in production
✅ Input sanitization: strip HTML, max 1000 chars per message
✅ SQL injection: SQLAlchemy ORM with parameterized queries — no raw SQL
✅ API keys: always from environment variables, never in code
✅ HTTPS: enforce in production (Railway + Vercel handle this automatically)
✅ Rate limiting: 30 messages/min per user (FastAPI middleware, in-memory)
✅ Crisis logs: store flagged sessions separately for audit
```

---

# 11. Environment Variables

## 11.1 Backend `.env`

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mindbridge

# Authentication
JWT_SECRET_KEY=your-very-long-random-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# AI
GEMINI_API_KEY=your-gemini-api-key-from-aistudio.google.com

# App
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
CORPUS_PATH=./corpus/mental_health_corpus.json
```

## 11.2 Frontend `.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
```

---

# 12. Execution Plan (10 Weeks)

## Week 1 — Research & Setup

**Deliverables:** Working dev environment, corpus v1, literature review drafted

```
Day 1-2: Read IEEE paper thoroughly. Make notes on key algorithms.
          Set up repo, install Node.js + Python, create project structure.

Day 3-4: Set up PostgreSQL locally (Docker: docker run -p 5432:5432 postgres).
          Create database, run SQL schema from Section 5.
          Verify connection with a Python script.

Day 5-7: Begin mental health corpus.
          - Download CounselChat dataset
          - Write 50 manual pairs (anxiety + depression focus)
          - Target: 100 pairs by end of week
```

## Week 2 — AI Pipeline

**Deliverables:** Working AI pipeline with tests passing

```
Day 1:   pip install sentence-transformers scikit-learn numpy
          Test model loads: python -c "from sentence_transformers
          import SentenceTransformer; m=SentenceTransformer('all-MiniLM-L6-v2');
          print(m.encode(['test anxiety']).shape)"
          Expected: (1, 384)

Day 2:   Implement embedder.py (Section 6.2).
          Test: embed 5 mental health queries, print cosine scores.
          Verify relevant > 0.4, irrelevant (e.g. "what is 2+2") < 0.4.

Day 3:   Implement crisis_service.py (Section 6.4).
          Test all 20 crisis keywords return True.

Day 4:   Get Gemini API key from aistudio.google.com (free).
          Implement ai_service.py (Section 6.3).
          Test end-to-end: input text → AI response.

Day 5-7: Write test_ai_pipeline.py. All tests must pass.
          Complete corpus to 150+ pairs.
```

## Week 3 — Backend API (Auth + Chat)

**Deliverables:** Auth endpoints + chat REST endpoint working

```
Day 1-2: FastAPI setup — main.py, config.py, database.py, dependencies.py
          Alembic migrations. Run: alembic upgrade head.
          Test tables created in PostgreSQL.

Day 3-4: Implement auth.py — register, login, refresh, logout.
          Test with httpx: register user, login, get token, access protected route.

Day 5-7: Implement chat.py REST endpoint.
          Wire up ai_service.py to the endpoint.
          Test: POST /api/v1/chat/message with mental health message → get response.
          Verify relevance_score + is_crisis in response.
```

## Week 4 — WebSocket + Remaining Endpoints

**Deliverables:** Streaming chat, mood API, all backend tests pass

```
Day 1-3: Implement WebSocket endpoint (chat_ws.py).
          Test streaming with a Python WebSocket client.

Day 4-5: Implement mood.py endpoints.
          Test: log mood, fetch history, fetch stats.

Day 6-7: Write all backend tests. Run: pytest tests/ -v
          Target: all tests green. Fix any failures.
```

## Week 5 — Frontend Foundation

**Deliverables:** Next.js setup, auth pages, working login/register

```
Day 1:   npx create-next-app@latest frontend --typescript --tailwind --app
          Install: shadcn/ui, axios, zustand, recharts, socket.io-client

Day 2-3: Build landing page (Section 9.1).
          Keep it simple — no Three.js, just clean CSS animations.

Day 4-5: Build login + register pages with form validation (React Hook Form + Zod).
          Connect to backend auth endpoints.

Day 6-7: Test full auth flow: register → login → JWT stored → redirect to dashboard.
```

## Week 6 — Chat Interface

**Deliverables:** Fully working chat UI with WebSocket streaming

```
Day 1-2: Build Sidebar, TopNav, dashboard layout.tsx

Day 3-5: Build ChatWindow, MessageBubble, ChatInput, TypingIndicator.
          Most important component — spend time getting it right.

Day 6:   Connect WebSocket — stream tokens appear in real-time.
          Test: off-topic query shows redirect card.

Day 7:   Build CrisisAlert overlay. Test with crisis keyword.
          Build QuickReplies component.
```

## Week 7 — Dashboard & Mood Tracker

**Deliverables:** Dashboard with mood chart, mood logging working

```
Day 1-3: Build Dashboard page — wellness score, recent sessions, mood chart.
          Connect to backend mood history endpoint.

Day 4-5: Build Mood Tracker page — logging modal, history list, line chart.

Day 6-7: Mobile responsiveness — test on 375px viewport.
          Fix any layout issues.
```

## Week 8 — Integration & Testing

**Deliverables:** Fully connected system, all features working end-to-end

```
Day 1-2: Full integration test — every frontend action hits the backend.
          Fix any CORS issues, missing endpoints, auth token issues.

Day 3-4: User testing — ask 5 classmates to use the app.
          Note any bugs or UX friction points.

Day 5-6: Fix bugs found in user testing.

Day 7:   Performance check — are responses under 3 seconds?
          If slow, check if model is loading on every request (it should load once at startup).
```

## Week 9 — Evaluation & Deployment

**Deliverables:** Evaluation results ready, app deployed

```
Day 1-3: Run formal evaluation (Section 13).
          Document results — classification accuracy, response quality scores, crisis recall.

Day 4-5: Deploy backend to Railway (connect GitHub repo → set env vars → deploy).
          Deploy frontend to Vercel (connect GitHub → set env vars → deploy).
          Set up Supabase free tier for production database.

Day 6-7: Test production URLs. Fix any deployment issues.
          Share link with supervisor for review.
```

## Week 10 — Report & Presentation

**Deliverables:** Complete project report, presentation slides

```
Day 1-4: Write project report (see Section 14 for structure).

Day 5-6: Create presentation slides (15 slides, 10 minutes).

Day 7:   Final rehearsal. Demo the live app.
```

---

# 13. Evaluation Methodology

## 13.1 AI Pipeline Evaluation

### Test 1: Relevance Classification Accuracy

Create a balanced test set of 100 messages:
- 50 mental health relevant (anxiety, depression, stress, etc.)
- 50 off-topic (math questions, weather, coding, recipes, etc.)

Measure:
- **True Positive Rate (Recall):** % of mental health messages correctly classified
- **True Negative Rate (Specificity):** % of off-topic messages correctly rejected
- **Overall Accuracy**
- **Target:** ≥ 85% (matching paper's reported result)

```python
# evaluation/test_relevance.py
from backend.app.services.embedder import embedder

TEST_CASES = [
    ("I feel anxious all the time", True),
    ("I can't stop worrying about my future", True),
    ("What is the capital of France?", False),
    ("Help me with Python code", False),
    # ... 96 more
]

results = []
for text, expected in TEST_CASES:
    vec = embedder.embed(text)
    is_rel, score = embedder.check_relevance(vec)
    results.append(is_rel == expected)

accuracy = sum(results) / len(results)
print(f"Accuracy: {accuracy:.2%}")
```

### Test 2: Crisis Detection Recall

Test all 20 crisis keywords trigger the crisis response.

```python
# All 20 must return is_crisis=True
# Target: 100% recall (zero false negatives on crisis is non-negotiable)
```

### Test 3: Few-Shot Retrieval Quality

For 10 test queries, manually verify the top-3 retrieved examples are semantically appropriate.

## 13.2 Response Quality Evaluation (Human)

Recruit 10–15 participants (classmates, family). Ask them to:
1. Have a 10-message conversation with MindBridge
2. Rate each AI response on:

| Criterion | Scale | Description |
|---|---|---|
| Empathy | 1–5 | Did it acknowledge your feelings? |
| Relevance | 1–5 | Was the response on-topic? |
| Helpfulness | 1–5 | Did it offer useful perspective or questions? |
| Safety | 1–5 | Did it feel appropriate and not harmful? |

**Target average:** ≥ 4.0/5.0 across all criteria

**Compare:** Zero-shot (no examples) vs Few-shot (your system) — this directly validates the paper's contribution.

## 13.3 System Performance

Measure API response time for 50 requests:
- **Target:** p95 < 3 seconds
- **Tools:** Python `time` module or `httpx` benchmarking

---

# 14. Project Report Structure

## Recommended Chapter Outline

```
Chapter 1: Introduction
  1.1 Problem Statement — mental health gap, AI opportunity
  1.2 Objectives — what this project aims to achieve
  1.3 Scope — what is and isn't included
  1.4 Organization of Report

Chapter 2: Literature Review
  2.1 Mental Health AI — existing systems and limitations
  2.2 Sentence Transformers and Semantic Embeddings
  2.3 Few-Shot Prompting — GPT, Gemini, research findings
  2.4 The IEEE ICDSBS 2025 Paper — detailed review
  2.5 Gaps Addressed by This Work

Chapter 3: System Design
  3.1 System Architecture (use diagram from Section 3)
  3.2 AI Pipeline Design (use flowchart from Section 6.1)
  3.3 Database Design (ER diagram from Section 5)
  3.4 API Design

Chapter 4: Implementation
  4.1 Development Environment Setup
  4.2 AI Pipeline Implementation
  4.3 Backend Implementation
  4.4 Frontend Implementation
  4.5 Corpus Curation Process

Chapter 5: Evaluation & Results
  5.1 Relevance Classification Results (Table + Confusion Matrix)
  5.2 Crisis Detection Results
  5.3 Few-Shot vs Zero-Shot Comparison
  5.4 Response Quality Survey Results
  5.5 System Performance Results
  5.6 Discussion

Chapter 6: Conclusion
  6.1 Summary of Contributions
  6.2 Limitations
  6.3 Future Work

References
Appendix A: Corpus Sample (20 entries)
Appendix B: Survey Questionnaire
Appendix C: API Documentation
```

---

# 15. Future Roadmap (Phase 2)

These are for the report's "Future Work" section — do NOT attempt during FYP.

| Feature | Value | Technical Approach |
|---|---|---|
| Multilingual Support | Tamil, Hindi, Telugu | `paraphrase-multilingual-MiniLM-L12-v2` embeddings |
| Fine-tuned Classifier | Better relevance accuracy | Fine-tune BERT on labeled mental health dataset |
| RLHF via Feedback | Improve responses over time | Thumbs up/down → preference dataset → fine-tune |
| Mobile App | Accessibility | React Native (Expo) with same backend |
| Therapist Dashboard | Clinical deployment | B2B: anonymous patient monitoring |
| Voice Mode | Accessibility | Web Speech API + ElevenLabs TTS |

---

# 16. Quick Start Guide

## Prerequisites
```bash
Node.js 18+   # node --version
Python 3.11+  # python --version
PostgreSQL 14+ # or Docker
Git
```

## Local Setup (15 minutes)

```bash
# 1. Clone and enter project
git clone https://github.com/yourname/mindbridge-ai.git
cd mindbridge-ai

# 2. Start PostgreSQL (Docker)
docker run -d --name mindbridge-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=mindbridge \
  -p 5432:5432 postgres:16

# 3. Backend setup
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Fill in your GEMINI_API_KEY
alembic upgrade head              # Create tables
python -c "from app.services.embedder import embedder; \
  embedder.load_corpus('./corpus/mental_health_corpus.json'); \
  print('Corpus loaded!')"       # Verify corpus loads
uvicorn app.main:app --reload --port 8000

# 4. Frontend setup (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev

# 5. Visit http://localhost:3000
```

## Verify AI Pipeline Works

```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "I feel really anxious about my exams"}'

# Expected response includes:
# "is_relevant": true
# "relevance_score": > 0.4
# "is_crisis": false
# "response": empathetic AI message
```

---

# 17. Dependency Files

## backend/requirements.txt

```
fastapi==0.110.0
uvicorn[standard]==0.29.0
python-dotenv==1.0.1
pydantic-settings==2.2.1
sqlalchemy[asyncio]==2.0.29
asyncpg==0.29.0
alembic==1.13.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.0
sentence-transformers==2.7.0
scikit-learn==1.4.2
numpy==1.26.4
google-generativeai==0.5.4
websockets==12.0
pytest==8.1.1
pytest-asyncio==0.23.6
```

## frontend/package.json (dependencies section)

```json
{
  "dependencies": {
    "next": "14.2.3",
    "react": "^18",
    "react-dom": "^18",
    "typescript": "^5",
    "@types/node": "^20",
    "@types/react": "^18",
    "tailwindcss": "^3.4",
    "autoprefixer": "^10",
    "postcss": "^8",
    "axios": "^1.6",
    "zustand": "^4.5",
    "recharts": "^2.12",
    "react-hook-form": "^7.51",
    "zod": "^3.22",
    "@hookform/resolvers": "^3.3",
    "socket.io-client": "^4.7",
    "lucide-react": "^0.383",
    "next-auth": "^5",
    "clsx": "^2.1",
    "tailwind-merge": "^2.3"
  }
}
```

---

> **MindBridge AI — FYP Blueprint v2.0**
> Scoped for Success · Grounded in Research · Built to Demonstrate
>
> *"Build something that works brilliantly, not something that looks impressive in a spec."*