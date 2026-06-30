# Agentic Job Matching System

Full-stack job matching application for extracting, scoring, reviewing, and tracking job opportunities against user role profiles.

The project is a production-ready starting point built around a small local stack: React for the UI, FastAPI for the API, SQLite for durable records, Qdrant for vector similarity, and LangGraph for extraction workflow orchestration.

## Architecture

```text
React + Vite UI
    |
FastAPI REST API
    |
LangGraph extraction workflow and business services
    |
SQLite job/profile/application records
    |
Qdrant derived vector index for similarity scoring
```

SQLite is the source of truth. Qdrant stores derived vectors for scorable job posts and can be rebuilt from retained application state if needed.

## Retained Capabilities

- Role profile creation and selection.
- Job ingestion from Tavily search results.
- Job ingestion from a public job URL.
- Job ingestion from manually pasted job text.
- LangGraph extraction with OpenAI structured output and one repair attempt.
- URL text extraction with size, timeout, and low-content handling.
- Deterministic deduplication before vector writes.
- Multi-factor scoring across embedding similarity, skills, location, level, and JD confidence.
- Review queue for pending jobs.
- Tracked job dashboard with application status transitions.
- Batch summary metrics for parsed jobs, token usage, cost, and extraction timing.
- Generated API contract shared with the frontend.

## Repository Layout

```text
backend/
  app/
    agents/       LangGraph graph, nodes, prompts, and state schemas
    api/          FastAPI routes and Pydantic API schemas
    core/         Settings, constants, and logging setup
    db/           SQLAlchemy models and async SQLite session setup
    services/     Extraction, LLM, embedding, scoring, dedup, Qdrant, and search services
  scripts/        API contract export utility
  tests/          Pytest suite
frontend/job-agent-ui/
  src/
    api/          Axios API client
    components/   Shared UI components
    pages/        Review and dashboard pages
    styles/       Application styling
    test/         Vitest suite
    types/        Contract-aligned TypeScript types
    utils/        Local UI state helpers
shared/
  api-contract.json
docs/superpowers/
  specs/          Approved cleanup/design specs
  plans/          Implementation plans
```

## Prerequisites

- Python 3.11 or newer.
- Node.js 18 or newer.
- Docker with Compose support.
- OpenAI API key for extraction and embeddings.
- Tavily API key for web search ingestion.

## Environment

Create a local environment file from the template:

```powershell
Copy-Item .env.example .env
```

Set these values in `.env`:

```text
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

The remaining defaults are suitable for local development:

```text
DATABASE_URL=sqlite+aiosqlite:///./data/job_matching.db
SQLITE_DB_PATH=./data/job_matching.db
QDRANT_URL=http://localhost:6333
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

## Backend Setup

Start Qdrant:

```powershell
docker compose up -d qdrant
```

Install backend dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Initialize SQLite schema:

```powershell
.\.venv\Scripts\python.exe -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"
```

Export the API contract after backend schema or route changes:

```powershell
.\.venv\Scripts\python.exe scripts/export_api_contract.py
```

Run backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs are available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Frontend Setup

Install frontend dependencies:

```powershell
cd frontend/job-agent-ui
npm install
```

Run frontend:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

## Verification

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe scripts/export_api_contract.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Frontend:

```powershell
cd frontend/job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm ls
```

## Operational Notes

- Keep SQLite and Qdrant running together for local end-to-end ingestion and scoring.
- Treat `shared/api-contract.json` as generated from backend owners.
- Regenerate the contract before updating frontend client/types after API changes.
- Tests replace external network providers with deterministic test doubles.
- Real provider calls require valid OpenAI and Tavily credentials.
