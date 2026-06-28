# Plan 1 - Backend Foundation, Environment, SQLite Schema

## 1. Objective

Establish the backend foundation for the Agentic Job Matching System MVP: FastAPI project skeleton, root environment loading, SQLite database models, SQLite indexes, and local Qdrant infrastructure configuration.

This phase creates the stable storage and configuration contract that all later phases must build on. Later phases may add services and routes, but must not redefine table fields, status values, or environment names without an explicit migration plan.

## 2. Source of Truth

- `Master_Plan.md` section 1, "System Objective"
- `Master_Plan.md` section 2, "Final MVP Stack"
- `Master_Plan.md` section 3, "MVP Scope"
- `Master_Plan.md` section 20, "SQLite Database Design"
- `Master_Plan.md` section 21, "Table: role_profiles"
- `Master_Plan.md` section 22, "Table: job_posts"
- `Master_Plan.md` section 23, "Table: applications"
- `Master_Plan.md` section 24, "SQLite Indexes"
- `Master_Plan.md` section 25, "Qdrant Local Collection Schema"
- `Master_Plan.md` section 30, "Project Directory Structure"
- `Master_Plan.md` section 31, "Environment Setup"
- `Master_Plan.md` section 32, "Single Root .env"
- `Master_Plan.md` section 33, "Docker Compose"

## 3. Prerequisites from Prior Phases

- [ ] No prior implementation phase is required.
- [ ] Python 3.11+ is available locally.
- [ ] Docker Desktop or Docker Engine is available for local Qdrant.
- [ ] The repository root is `Job_Agent/`.

## 4. Scope

- Create backend package layout under `backend/app/`.
- Add backend dependency file with the MVP backend packages.
- Add root `.env.example` matching the master environment contract.
- Add `docker-compose.yml` for local Qdrant with a persistent `qdrant_data` volume.
- Add backend configuration loading from the single root `.env`.
- Add basic logging setup for backend services.
- Add SQLAlchemy async session creation for `sqlite+aiosqlite`.
- Enable SQLite `PRAGMA foreign_keys=ON` and `PRAGMA journal_mode=WAL`.
- Define SQLAlchemy models for:
  - `role_profiles`
  - `job_posts`
  - `applications`
- Ensure database initialization creates only the three MVP tables: `role_profiles`, `job_posts`, and `applications`.
- Ensure no `search_runs`, analytics, vector metadata, user/auth, or organization tables are created in this phase.
- Define required SQLite indexes and constraints from the master plan.
- Ensure UUID values are generated and stored as canonical string values.
- Add a minimal FastAPI app entrypoint that can initialize the database.
- Add `backend/data/.gitkeep` so the local SQLite directory exists.

## 5. Out of Scope

- Do not implement LangGraph, LLM extraction, prompts, or agent nodes.
- Do not implement Tavily search, URL fetching, or trafilatura parsing.
- Do not implement scoring formulas, embeddings, or Qdrant upserts.
- Do not implement API job workflows beyond a minimal app bootstrap.
- Do not implement React frontend.
- Do not add authentication, organizations, background queues, Celery, Redis, cover letters, or auto-apply behavior.
- Do not add a `matching_text` column to `role_profiles`; role query text is derived later in `scoring_service.py`.
- Do not add a `search_runs` table; batch tracking uses `job_posts.batch_id` only.
- Do not add CORS, public API route modules, request/response schemas, or frontend integration in this phase.
- Do not create Qdrant collections, payload indexes, vectors, or Qdrant service code.

## 6. Target Directory Structure

```text
Job_Agent/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   `-- __init__.py
|   |   |-- agents/
|   |   |   `-- __init__.py
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py
|   |   |   `-- logging.py
|   |   |-- db/
|   |   |   |-- __init__.py
|   |   |   |-- models.py
|   |   |   |-- session.py
|   |   |   `-- migrations/
|   |   |       `-- .gitkeep
|   |   |-- services/
|   |   |   `-- __init__.py
|   |   `-- main.py
|   |-- data/
|   |   `-- .gitkeep
|   |-- requirements.txt
|   `-- Dockerfile
|-- docker-compose.yml
`-- .env.example
```

## 7. Technical Specifications

### Environment Settings

Use one root `.env` file. The backend configuration must load from the repository root, not from `backend/.env`.

Required settings:

```env
ENV=development
BACKEND_PORT=8000
FRONTEND_PORT=5173

DATABASE_URL=sqlite+aiosqlite:///./data/job_matching.db
SQLITE_DB_PATH=./data/job_matching.db

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

TAVILY_API_KEY=your-tavily-api-key

MAX_URLS_PER_BATCH=10
MAX_RAW_TEXT_CHARS=20000
MAX_CLEAN_TEXT_CHARS=12000
MAX_RETRY_PER_JOB=1
REQUEST_TIMEOUT_SECONDS=10
MAX_RESPONSE_SIZE_MB=2
```

No API keys may be exposed to the frontend.

### Backend Dependencies

`backend/requirements.txt` must include:

```text
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
langchain>=0.2.0
langchain-core>=0.2.0
langchain-community>=0.2.0
langchain-openai>=0.1.0
langgraph>=0.2.0
qdrant-client>=1.9.0
numpy>=1.24.0
tavily-python>=0.3.0
httpx>=0.27.0
trafilatura>=1.8.0
sqlalchemy>=2.0.0
alembic>=1.13.0
aiosqlite>=0.20.0
python-dotenv>=1.0.0
tenacity>=8.2.0
```

### SQLite Rules

- Use SQLAlchemy async engine with `sqlite+aiosqlite`.
- Store UUID values as `TEXT` canonical UUID strings.
- Store JSON arrays, such as `skills`, as JSON encoded `TEXT`.
- Store booleans as SQLAlchemy Boolean or SQLite integer-compatible values.
- Store timestamps as SQLAlchemy DateTime or ISO-8601 text consistently.
- Enable foreign keys for every SQLite connection.
- Enable WAL mode for smoother local demo reads and writes.

Startup pragmas:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

### MVP Table Boundary

Plan 1 must create exactly these application tables:

```text
role_profiles
job_posts
applications
```

Do not create:

```text
search_runs
users
organizations
analytics tables
qdrant/vector metadata tables
```

Batch tracking is handled only by the `batch_id` column on `job_posts`.

### Table: role_profiles

Required columns:

```text
id TEXT primary key
target_role text not null
level text
location text
accept_remote boolean
skills TEXT JSON
resume_text text
created_at DateTime
updated_at DateTime
```

Hard rule: do not add `matching_text`; Plan 3 derives role query text dynamically.

### Table: job_posts

Required columns:

```text
id TEXT primary key
batch_id TEXT not null
role_profile_id TEXT not null foreign key -> role_profiles.id
title text
company text
location text
work_mode text
level text
employment_type text
salary text
responsibilities text
requirements text
skills TEXT JSON
source_url text
source_platform text
parse_status text
raw_content_hash text
dedup_key text
duplicate_of_job_id TEXT nullable self-reference
jd_status text
extraction_status text
error_reason text
should_score_similarity boolean
embedding_text text
embedding_similarity REAL
skill_overlap_score REAL
location_match_score REAL
level_match_score REAL
base_score REAL
jd_confidence_multiplier REAL
final_score REAL
final_score_percent REAL
status text
input_tokens integer
output_tokens integer
estimated_cost_usd REAL
extraction_time_ms integer
discovered_at DateTime
created_at DateTime
updated_at DateTime
```

Allowed status values:

```text
pending_review
saved
applied
interview
rejected
offer
ignored
```

Allowed source platform values:

```text
tavily
manual_url
manual_text
mock
job_board
```

### Table: applications

Required columns:

```text
id TEXT primary key
job_post_id TEXT not null foreign key -> job_posts.id
status text
cv_version text
notes text
applied_at DateTime
updated_at DateTime
```

Allowed application status values:

```text
applied
interview
rejected
offer
```

### Required Indexes

Create these indexes exactly:

```sql
CREATE INDEX idx_job_posts_status
ON job_posts(status);

CREATE INDEX idx_job_posts_final_score
ON job_posts(final_score DESC);

CREATE INDEX idx_job_posts_jd_status
ON job_posts(jd_status);

CREATE INDEX idx_job_posts_batch_id
ON job_posts(batch_id);

CREATE INDEX idx_job_posts_role_profile_status_score
ON job_posts(role_profile_id, status, final_score DESC);

CREATE UNIQUE INDEX idx_job_posts_raw_content_hash
ON job_posts(raw_content_hash)
WHERE raw_content_hash IS NOT NULL;

CREATE INDEX idx_job_posts_dedup_key
ON job_posts(dedup_key);

CREATE INDEX idx_applications_job_post_id
ON applications(job_post_id);
```

### Qdrant Infrastructure

Create only the local Docker Compose service in this phase:

```yaml
version: "3.8"

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: job_agent_qdrant_local
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

The Qdrant collection, payload indexes, upsert, delete, and query filtering are implemented in Plan 3.

## 8. Implementation Steps

- [ ] Create the backend folder structure and `__init__.py` files.
- [ ] Create `backend/requirements.txt` with all backend dependencies from the master plan.
- [ ] Create `.env.example` at the repository root using the required environment names.
- [ ] Create `docker-compose.yml` for Qdrant local with the persistent `qdrant_data` volume.
- [ ] Create `backend/app/core/config.py` using Pydantic settings and root `.env` loading.
- [ ] Create `backend/app/core/logging.py` with a simple structured logging configuration.
- [ ] Create `backend/app/db/models.py` with SQLAlchemy ORM models for the three MVP tables.
- [ ] Add model-level indexes and the partial unique index for `raw_content_hash`.
- [ ] Create `backend/app/db/session.py` with async engine, async session maker, and database initialization function.
- [ ] Add SQLite connection pragmas for `foreign_keys` and `journal_mode`.
- [ ] Confirm database metadata only defines `role_profiles`, `job_posts`, and `applications`.
- [ ] Confirm `role_profiles` does not include `matching_text`.
- [ ] Confirm no `search_runs` table or extra MVP-irrelevant table is introduced.
- [ ] Create `backend/app/main.py` with FastAPI app initialization and database startup initialization.
- [ ] Add `backend/data/.gitkeep` and `backend/app/db/migrations/.gitkeep`.
- [ ] Confirm no frontend, extraction, scoring, or Qdrant service behavior is implemented in this phase.

## 9. Verification & Testing Plan

Automated checks:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"
python -c "from app.db.models import RoleProfile, JobPost, Application; print(RoleProfile.__tablename__, JobPost.__tablename__, Application.__tablename__)"
```

SQLite verification:

```powershell
cd backend
@'
import sqlite3

conn = sqlite3.connect("data/job_matching.db")

tables = [
    row[0]
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
]
print("tables", tables)

expected_tables = {"applications", "job_posts", "role_profiles"}
unexpected_tables = set(tables) - expected_tables
missing_tables = expected_tables - set(tables)

print("missing_tables", sorted(missing_tables))
print("unexpected_tables", sorted(unexpected_tables))

role_profile_columns = [
    row[1]
    for row in conn.execute("PRAGMA table_info(role_profiles)").fetchall()
]
print("role_profiles columns", role_profile_columns)
print("has matching_text", "matching_text" in role_profile_columns)

indexes = [
    row[0]
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
    ).fetchall()
]
print("indexes", indexes)

required_indexes = {
    "idx_job_posts_status",
    "idx_job_posts_final_score",
    "idx_job_posts_jd_status",
    "idx_job_posts_batch_id",
    "idx_job_posts_role_profile_status_score",
    "idx_job_posts_raw_content_hash",
    "idx_job_posts_dedup_key",
    "idx_applications_job_post_id",
}
print("missing_indexes", sorted(required_indexes - set(indexes)))
'@ | python -
```

App-session PRAGMA verification:

```powershell
cd backend
@'
import asyncio
from sqlalchemy import text
from app.db.session import engine

async def main():
    async with engine.connect() as conn:
        foreign_keys = await conn.scalar(text("PRAGMA foreign_keys"))
        journal_mode = await conn.scalar(text("PRAGMA journal_mode"))
        print("foreign_keys", foreign_keys)
        print("journal_mode", journal_mode)

asyncio.run(main())
'@ | python -
```

Expected:

```text
foreign_keys 1
journal_mode wal
```

Qdrant infrastructure check:

```powershell
docker compose up -d qdrant
docker compose ps
docker compose down
```

Expected outcomes:

- Importing `settings` succeeds and reads root environment defaults.
- `backend/data/job_matching.db` can be created locally.
- Exactly three MVP application tables exist: `role_profiles`, `job_posts`, and `applications`.
- No `search_runs` table exists.
- No `matching_text` column exists on `role_profiles`.
- Required indexes exist.
- Foreign keys are enabled on app-managed SQLAlchemy connections.
- WAL mode is enabled for the SQLite database.
- Qdrant container can start locally on ports `6333` and `6334`.

Manual verification:

- Confirm `.env.example` contains no real API keys.
- Confirm `role_profiles` has no `matching_text` column.
- Confirm no extraction, scoring, frontend, or API workflow scope was added.

## 10. Handoff Notes for Phase 2

Plan 2 consumes:

- Stable backend package structure under `backend/app/`.
- Root environment settings from `backend/app/core/config.py`.
- SQLAlchemy async session utilities from `backend/app/db/session.py`.
- Stable table and field names from `backend/app/db/models.py`.
- Existing dependency set for LangChain, LangGraph, OpenAI, httpx, and trafilatura.

Plan 2 must:

- Add LangGraph state, extraction schemas, prompts, and extraction nodes.
- Preserve the `batch_id`, `role_profile_id`, and `input_source` fields in every graph node update.
- Return extraction results that can later be saved into the Plan 1 `job_posts` schema.

Hard rules for later phases:

- Do not rename database columns from this phase.
- Do not add `matching_text` to `role_profiles`.
- Do not change status values without a migration plan.
- Do not create new database tables unless a later approved plan explicitly requires them.
