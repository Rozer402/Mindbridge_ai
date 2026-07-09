<div align="center">

<h1>🧠 MindBridge AI</h1>

<p><strong>An open-source, production-grade AI mental health companion powered by Google Gemini, sentence transformers, and a custom crisis detection pipeline.</strong></p>

<p>
  <a href="#-features"><img src="https://img.shields.io/badge/status-stable-brightgreen" alt="Status: Stable"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"/></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"/></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/node.js-18%2B-green" alt="Node.js 18+"/></a>
  <a href="#-api-docs"><img src="https://img.shields.io/badge/API-FastAPI-teal" alt="FastAPI"/></a>
</p>

<p>
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-api-docs">API Docs</a> ·
  <a href="#-contributing">Contributing</a>
</p>

</div>

---

## 🌟 Overview

MindBridge AI is a full-stack AI companion designed to provide empathetic, non-judgmental first-line mental health support. It combines a modern **Next.js frontend**, a **FastAPI backend**, and a layered AI pipeline to deliver safe, context-aware conversations.

**Key design principles:**

- **Safety first.** A three-layer crisis detection pipeline (keyword regex → embedding similarity → ML classifier) ensures that genuine crisis messages are never missed. False positives are aggressively guarded.
- **Memory-driven conversations.** Redis-backed conversation memory persists across sessions, with PostgreSQL as a durable fallback. The LLM receives the last 6 turns for deep context.
- **Graceful degradation.** Redis unavailable? PostgreSQL takes over. Gemini rate-limited? Corpus fallback examples respond. The system never crashes silently.

> **This is not a replacement for professional mental health care.** MindBridge AI provides empathetic first-line support and always directs users to qualified professionals when needed.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🤖 AI Chat | Google Gemini 2.5 Flash with few-shot retrieval and conversation memory |
| 🧩 ML Classifier | Custom 2-layer PyTorch network (28K params, 10 mental health categories) |
| 🚨 Crisis Detection | 3-layer pipeline: keyword regex → cosine embedding → MC Dropout classifier |
| 🧠 Memory Engine | Redis-backed rolling window (20 messages / 24 hours TTL), PostgreSQL fallback |
| 📊 Mood Tracking | Log daily mood scores (1–10), view trends and 30-day statistics |
| 🔐 Auth | JWT access + refresh tokens, bcrypt password hashing |
| ⚡ Real-time | WebSocket chat support alongside REST API |
| 📖 Semantic Retrieval | `all-MiniLM-L6-v2` embeddings with category-aware few-shot retrieval |
| 🛡️ Rate Limiting | Input sanitization, 1000-char message cap, relevance threshold |

---

## 🏛️ Architecture

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                         │
│  Login → Chat → Mood Dashboard → Session History           │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST / WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                                                             │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────┐  │
│  │ /auth    │  │ /chat      │  │ /mood    │  │  /ws    │  │
│  └──────────┘  └─────┬──────┘  └──────────┘  └─────────┘  │
│                      │                                      │
│              ┌───────▼────────────────────────────────┐    │
│              │         AI Pipeline (ai_service.py)    │    │
│              │                                        │    │
│              │  1. Sanitise message (1000 char cap)   │    │
│              │  2. Embed  (all-MiniLM-L6-v2, 384-dim) │    │
│              │  3. Relevance gate  (cosine ≥ 0.25)    │    │
│              │  4. Crisis detection (3 layers)        │    │
│              │     ├── Keyword regex (100% recall)    │    │
│              │     ├── Embedding sim (cosine ≥ 0.70)  │    │
│              │     └── ML Classifier (conf ≥ 0.75,    │    │
│              │                        words ≥ 4)      │    │
│              │  5. Few-shot retrieval (category-aware) │    │
│              │  6. Inject Redis memory (last 6 turns) │    │
│              │  7. Gemini 2.5 Flash generation        │    │
│              │  8. Persist to Redis + PostgreSQL       │    │
│              └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
          │                     │                  │
          ▼                     ▼                  ▼
    ┌──────────┐         ┌────────────┐     ┌──────────────┐
    │PostgreSQL│         │   Redis    │     │  Gemini API  │
    │(sessions,│         │ (memory,   │     │ (LLM gen)    │
    │ messages,│         │ TTL 24h)   │     └──────────────┘
    │ mood)    │         └────────────┘
    └──────────┘
```

---

## 🤖 AI Pipeline

### 1. Embedding Layer
`all-MiniLM-L6-v2` (384-dim) from Sentence Transformers is used for all semantic operations:
- **Relevance gating**: cosine similarity ≥ 0.25 to mental health corpus
- **Crisis embedding**: cosine similarity ≥ 0.70 to crisis-labeled examples
- **Few-shot retrieval**: top-K=3 most semantically similar examples

### 2. Crisis Detection Pipeline
Three independent checks run on every message. **Any one trigger activates the crisis protocol.**

| Layer | Method | Threshold | Notes |
|---|---|---|---|
| **Keyword** | Compiled regex with word boundaries | Match = crisis | 100% recall on known phrases; no false positives from substrings |
| **Embedding** | Cosine similarity to crisis corpus vectors | ≥ 0.70 | Catches novel phrasings not in keyword list |
| **Classifier** | MC Dropout confidence | conf ≥ 0.75, uncertainty < 0.04, words ≥ 4 | Short messages (< 4 words) are never trusted — confidence is deceptively high on "yes", "I don't know" etc. |

### 3. Trained Classifier
A lightweight 2-layer feed-forward network trained on frozen MiniLM embeddings:
- **Architecture**: `Linear(384→64) → ReLU → Dropout(0.5) → Linear(64→10)`
- **Categories**: anxiety, depression, stress, sleep, loneliness, self_esteem, grief, anger, relationships, crisis
- **Inference**: Monte Carlo Dropout (20 passes) for uncertainty estimation
- **Fallback**: If no trained weights exist, falls back to pure cosine-similarity retrieval

### 4. Memory Engine
Redis-backed rolling conversation window:
- Stores last 20 messages per session (10 turns) with atomic RPUSH+LTRIM pipeline
- Injects last 12 messages (6 turns) into the Gemini prompt
- 24-hour TTL, reset on every write — idle sessions auto-expire
- Falls back to PostgreSQL when Redis is unavailable — chat never breaks

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Zustand, Recharts |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy (async), Alembic |
| **Database** | PostgreSQL 16 |
| **Cache / Memory** | Redis 7 (AOF persistence) |
| **AI / ML** | Google Gemini 2.5 Flash, Sentence Transformers, PyTorch |
| **Auth** | JWT (access + refresh), bcrypt |
| **Embeddings** | `all-MiniLM-L6-v2` (384-dim) via `sentence-transformers` |
| **Deployment** | Docker Compose |

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (for PostgreSQL + Redis)
- **Python 3.11+**
- **Node.js 18+**
- **Google Gemini API Key** — free at [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 1. Start Infrastructure

```bash
git clone https://github.com/your-org/mindbridge-ai
cd mindbridge-ai
docker compose up -d
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env → add GEMINI_API_KEY and JWT_SECRET_KEY

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open **http://localhost:3000** — register an account and start chatting.

API docs are at **http://localhost:8000/docs**.

---

## ⚙️ Environment Variables

See [`backend/.env.example`](backend/.env.example) for the full reference.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | *(docker value)* | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | ✅ | — | Random 32+ character secret |
| `GEMINI_API_KEY` | ⚠️ | — | Enables full Gemini responses (fallback works without) |
| `REDIS_URL` | ✅ | `redis://localhost:6380` | Redis for conversation memory |
| `CORPUS_PATH` | ✅ | `./corpus/mental_health_corpus.json` | Mental health corpus for embeddings |
| `CORS_ORIGINS` | ✅ | `http://localhost:3000` | Comma-separated allowed origins |
| `MEMORY_TTL_SECONDS` | ❌ | `86400` (24h) | Redis session TTL |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `30` | JWT access token lifetime |

Generate a secure JWT secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🧪 Testing

### Unit Tests (no server required)
```bash
cd backend
python -m pytest tests/test_ai_pipeline.py -v
```

### Integration Tests (server + Docker required)
```bash
# Ensure server is running, then:
cd backend
python tests/e2e_test.py
```

The e2e suite covers: health check, multi-turn memory, crisis false-positive guard, genuine crisis detection, and enriched response fields.

---

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | — | Register new user |
| `POST` | `/api/v1/auth/login` | — | Login, get tokens |
| `POST` | `/api/v1/auth/refresh` | — | Refresh access token |
| `GET` | `/api/v1/users/me` | ✅ | Get current user profile |
| `POST` | `/api/v1/chat/message` | ✅ | Send message, get AI response |
| `GET` | `/api/v1/chat/sessions` | ✅ | List chat sessions |
| `GET` | `/api/v1/chat/sessions/{id}/messages` | ✅ | Get messages in a session |
| `DELETE` | `/api/v1/chat/sessions/{id}` | ✅ | Delete session + clear Redis memory |
| `POST` | `/api/v1/mood/log` | ✅ | Log a mood entry |
| `GET` | `/api/v1/mood/history` | ✅ | Get mood history (up to 365 days) |
| `GET` | `/api/v1/mood/stats` | ✅ | Get mood statistics and trend |
| `GET` | `/health` | — | System health check |
| `WS` | `/ws/chat` | ✅ | WebSocket chat endpoint |

Full interactive docs: **http://localhost:8000/docs**

---

## 📁 Project Structure

```
mindbridge-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (auth, chat, mood, users)
│   │   ├── models/          # SQLAlchemy ORM models + classifier weights
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # AI pipeline, memory, auth, embeddings
│   │   ├── ws/              # WebSocket handler
│   │   ├── config.py        # Pydantic settings (reads .env)
│   │   ├── database.py      # Async SQLAlchemy engine + session factory
│   │   ├── dependencies.py  # FastAPI dependency injection (JWT auth)
│   │   └── main.py          # App entry point, lifespan, CORS
│   ├── corpus/              # Mental health training corpus (JSON)
│   ├── migrations/          # Alembic migrations
│   ├── tests/               # Unit + e2e test suites
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                 # Next.js 14 App Router pages
│   ├── components/          # React components (chat, dashboard, UI)
│   ├── lib/                 # API client, utilities
│   ├── store/               # Zustand global state
│   └── types/               # TypeScript type definitions
├── docs/                    # Additional documentation
├── docker-compose.yml       # PostgreSQL 16 + Redis 7
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full feature roadmap.

**v1.1 (planned)**
- [ ] Retrain classifier on larger, balanced dataset
- [ ] Add optional Pushover/SMS crisis alert to emergency contact
- [ ] Session search and filtering

**v1.2 (planned)**
- [ ] Conversation summarization for long sessions
- [ ] Admin dashboard (usage analytics, crisis event log)
- [ ] Rate limiting per user / per IP

**Backlog**
- [ ] Multi-language support (Hindi, Spanish)
- [ ] Voice input
- [ ] Mobile app (React Native)

---

## 🔒 Safety & Ethics

MindBridge AI takes safety seriously:

- **Crisis detection** uses a layered approach with 100% recall on known crisis phrases
- **No diagnosis** — the system explicitly never claims to diagnose or treat any condition
- **Escalation** — all crisis responses include India-specific and international helplines
- **Data privacy** — conversations are stored encrypted; Redis sessions auto-expire in 24 hours

Please read [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — LLM generation
- [Sentence Transformers](https://www.sbert.net/) — `all-MiniLM-L6-v2` embeddings
- [FastAPI](https://fastapi.tiangolo.com/) — async Python web framework
- [IEEE ICDSBS 2025](https://icdsbs.org/) — research methodology and evaluation framework

---

<div align="center">
  <sub>Built with ❤️ for better mental health support. Remember: you are not alone. 💙</sub>
</div>
