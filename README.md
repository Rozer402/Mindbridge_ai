# MindBridge AI

Mental health support platform — Final Year Project (IEEE ICDSBS 2025 research implementation).

## Stack

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Backend:** FastAPI, PostgreSQL, sentence-transformers, Google Gemini
- **AI:** `all-MiniLM-L6-v2` embeddings, cosine relevance (0.4), few-shot retrieval, crisis detection

## Quick start

### Prerequisites

- Node.js 18+
- Python 3.11+ (recommended; 3.14 may need newer `asyncpg`)
- PostgreSQL 14+ or Docker Desktop

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # Add GEMINI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## Project structure

```
mindbridge/
├── backend/          FastAPI + AI pipeline
├── frontend/         Next.js 14 app
├── docs/plan.md      Full FYP blueprint
└── docker-compose.yml
```

## API docs

With backend running: http://localhost:8000/docs
