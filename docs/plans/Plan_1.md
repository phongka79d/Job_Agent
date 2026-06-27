# Phase 1 Plan: Foundation

## 1. Objective

Build the local foundation for the Agentic Job Matching System MVP: project structure, Python backend environment, single root environment config, Qdrant Local via Docker Compose, and a SQLite database initialized through SQLAlchemy async models.

Phase 1 must leave the project ready for later extraction, LangGraph, scoring, API, ingestion, Qdrant vector, and UI phases without implementing those later-phase behaviors.

## 2. Source of Truth

Use `docs/plans/Master_Plan.md` as the single source of truth, especially:

- Section 21: SQLite Database Design
- Sections 22-24: `role_profiles`, `job_posts`, `applications`
- Section 25: SQLite indexes
- Section 31: Project directory structure
- Sections 32-34: environment setup, root `.env`, Docker Compose

Hard rules:

- Use SQLite with `sqlite+aiosqlite`.
- Do not use PostgreSQL, PostgreSQL Docker services, `psycopg2`, `asyncpg`, or PostgreSQL-only SQL.
- Store UUIDs as canonical UUID strings in `TEXT`, generated with `uuid.uuid4()`.
- Do not add `matching_text` to `role_profiles`.
- Keep Qdrant local and Docker-only in this phase.
- Keep a single root `.env`; do not add `backend/.env` or frontend `.env` files.

## 3. Scope

Phase 1 includes:

- Create the backend/project directory foundation.
- Create Python virtual environment setup instructions and backend dependencies.
- Create root `.env.example`; local `.env` is copied from it and gitignored.
- Create `docker-compose.yml` for Qdrant Local only.
- Create SQLAlchemy async SQLite setup with `sqlite+aiosqlite`.
- Create the local SQLite database file at `backend/data/job_matching.db`.
- Create the 3 core tables:
  - `role_profiles`
  - `job_posts`
  - `applications`
- Add required SQLite-compatible indexes and constraints.
- Add backend configuration foundation.
- Add basic database initialization and schema verification.

Phase 1 may create schema columns and indexes needed by later phases, but it must not implement the behavior that uses them.

## 4. Out of Scope

Do not implement:

- Role profile API endpoints.
- FastAPI route implementation.
- Job ingestion orchestration.
- URL parsing or URL extraction.
- Text extraction.
- LangGraph nodes, graph wiring, prompts, or agent execution.
- LLM extraction.
- Scoring behavior.
- Deduplication behavior.
- Qdrant collections, vector upsert, vector search, vector delete, embeddings, or payload indexes.
- Tavily search logic.
- Demo seeding.
- React/Vite UI.
- Application workflow screens.
- PostgreSQL or database containers.

These topics may appear only as out-of-scope notes or later-phase handoff notes.

## 5. Target Directory Structure

Create this Phase 1 structure:

```text
Job_Agent/
|-- backend/
|   |-- app/
|   |   |-- __init__.py
|   |   |-- api/.gitkeep
|   |   |-- agents/.gitkeep
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py
|   |   |   `-- logging.py
|   |   |-- db/
|   |   |   |-- __init__.py
|   |   |   |-- models.py
|   |   |   |-- session.py
|   |   |   `-- migrations/.gitkeep
|   |   `-- services/.gitkeep
|   |-- data/.gitkeep
|   |-- scripts/
|   |   |-- init_db.py
|   |   `-- verify_db_schema.py
|   `-- requirements.txt
|-- frontend/.gitkeep
|-- mock_data/.gitkeep
|-- docker-compose.yml
|-- .env.example
|-- .gitignore
`-- docs/plans/Plan_1.md
```

Do not create route files, agent graph files, service implementations, Qdrant service code, or Vite app files in Phase 1.

## 6. Environment Setup

Create `backend/requirements.txt` using the backend requirements from `Master_Plan.md`:

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

Dependency ownership note:

```text
These dependencies may be installed during Phase 1 for environment bootstrap convenience only. Their presence does not mean Phase 1 implements extraction, LangGraph, scoring, search, Qdrant vector logic, or API workflows.
```

Setup commands for Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create root `.env.example`:

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

Create `.gitignore` entries:

```text
.env
backend/.venv/
backend/data/*.db
backend/data/*.db-*
__pycache__/
.pytest_cache/
```

Environment file rules:

- The only environment file in Phase 1 is the root `.env` copied from `.env.example`.
- No `backend/.env` file is required.
- No frontend `.env` or `frontend/.env.example` file is introduced in Phase 1.
- `backend/app/core/config.py` must resolve the root `.env` by absolute path, not by current working directory.

## 7. Docker Compose Plan

Create `docker-compose.yml` with Qdrant Local only:

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

Commands:

```powershell
docker compose config
docker compose up -d qdrant
docker compose ps
docker compose down
```

Acceptance criteria:

- `docker compose config --services` outputs only `qdrant`.
- Qdrant Local can start using Docker Compose.
- No PostgreSQL service exists.
- SQLite remains a local file managed by the backend, not Docker.

## 8. SQLite Database Plan

SQLite database file:

```text
backend/data/job_matching.db
```

Rules:

- Use `sqlite+aiosqlite`.
- Store UUIDs as `TEXT`.
- Generate IDs with `str(uuid.uuid4())`.
- Store JSON-like arrays such as `skills` as `TEXT` containing JSON strings.
- Store timestamps using SQLAlchemy `DateTime` or ISO-8601-compatible SQLite values.
- Store booleans with SQLAlchemy `Boolean`, which SQLite persists compatibly.
- Use SQLite `?` placeholders or SQLAlchemy bound parameters, not PostgreSQL `$1`.
- Resolve the SQLite file consistently so database initialization creates `backend/data/job_matching.db`.
- Enable these PRAGMAs on SQLAlchemy connections:
  - `PRAGMA foreign_keys=ON`
  - `PRAGMA journal_mode=WAL`

WAL mode is recommended for local development stability. If enabled, verify it explicitly.

No `search_runs` table is created. Use `job_posts.batch_id`.

## 9. SQLAlchemy Model Plan

Create `backend/app/db/models.py` with SQLAlchemy 2.0 declarative models.

Common helpers:

- `id` defaults use `lambda: str(uuid.uuid4())`.
- Timestamp defaults use UTC datetime.
- Keep all UUID foreign keys as `String(36)` or `Text`.

These models define storage only. They do not implement extraction, scoring, deduplication behavior, ingestion, or API workflows.

### `role_profiles`

Do not add `matching_text`.

| Column | SQLAlchemy type | Required behavior |
|---|---|---|
| `id` | `String(36)` | primary key, UUID string |
| `target_role` | `Text` | not null |
| `level` | `String` | nullable |
| `location` | `Text` | nullable |
| `accept_remote` | `Boolean` | not null, default `False` |
| `skills` | `Text` | not null, default `"[]"` JSON string |
| `resume_text` | `Text` | nullable |
| `created_at` | `DateTime` | not null |
| `updated_at` | `DateTime` | not null, updates on change |

### `job_posts`

| Column | SQLAlchemy type | Required behavior |
|---|---|---|
| `id` | `String(36)` | primary key, UUID string |
| `batch_id` | `String(36)` | not null |
| `role_profile_id` | `String(36)` | FK to `role_profiles.id`, not null |
| `title` | `Text` | nullable |
| `company` | `Text` | nullable |
| `location` | `Text` | nullable |
| `work_mode` | `String` | default `unknown` |
| `level` | `String` | default `unknown` |
| `employment_type` | `String` | default `unknown` |
| `salary` | `Text` | nullable |
| `responsibilities` | `Text` | nullable |
| `requirements` | `Text` | nullable |
| `skills` | `Text` | not null, default `"[]"` JSON string |
| `source_url` | `Text` | nullable |
| `source_platform` | `String` | nullable until later ingestion code sets it |
| `parse_status` | `String` | default `success` |
| `raw_content_hash` | `Text` | nullable |
| `dedup_key` | `Text` | nullable |
| `duplicate_of_job_id` | `String(36)` | nullable FK to `job_posts.id` |
| `jd_status` | `String` | default `unclear` |
| `extraction_status` | `String` | default `failed` |
| `error_reason` | `Text` | nullable |
| `should_score_similarity` | `Boolean` | not null, default `False` |
| `embedding_text` | `Text` | nullable |
| `embedding_similarity` | `Float` | nullable |
| `skill_overlap_score` | `Float` | nullable |
| `location_match_score` | `Float` | nullable |
| `level_match_score` | `Float` | nullable |
| `base_score` | `Float` | nullable |
| `jd_confidence_multiplier` | `Float` | nullable |
| `final_score` | `Float` | nullable |
| `final_score_percent` | `Float` | nullable |
| `status` | `String` | not null, default `pending_review` |
| `input_tokens` | `Integer` | not null, default `0` |
| `output_tokens` | `Integer` | not null, default `0` |
| `estimated_cost_usd` | `Float` | not null, default `0.0` |
| `extraction_time_ms` | `Integer` | nullable |
| `discovered_at` | `DateTime` | not null |
| `created_at` | `DateTime` | not null |
| `updated_at` | `DateTime` | not null, updates on change |

### `applications`

| Column | SQLAlchemy type | Required behavior |
|---|---|---|
| `id` | `String(36)` | primary key, UUID string |
| `job_post_id` | `String(36)` | FK to `job_posts.id`, not null |
| `status` | `String` | not null |
| `cv_version` | `Text` | nullable |
| `notes` | `Text` | nullable |
| `applied_at` | `DateTime` | nullable |
| `updated_at` | `DateTime` | not null, updates on change |

## 10. Indexes and Constraints

Add required indexes exactly from `Master_Plan.md`:

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

Implement the partial unique index in SQLAlchemy with SQLite-compatible `sqlite_where`.

Explicit verification requirement:

```sql
SELECT name, sql
FROM sqlite_master
WHERE type = 'index'
  AND name = 'idx_job_posts_raw_content_hash';
```

Expected: the returned SQL includes:

```text
WHERE raw_content_hash IS NOT NULL
```

Add SQLite-compatible constraints:

- Primary keys on all `id` columns.
- Foreign key from `job_posts.role_profile_id` to `role_profiles.id`.
- Self foreign key from `job_posts.duplicate_of_job_id` to `job_posts.id`.
- Foreign key from `applications.job_post_id` to `job_posts.id`.
- Check constraints for enum-like values:
  - `work_mode`: `onsite`, `remote`, `hybrid`, `unknown`
  - `level`: `intern`, `fresher`, `junior`, `mid`, `senior`, `unknown`
  - `employment_type`: `internship`, `full-time`, `part-time`, `contract`, `unknown`
  - `parse_status`: `success`, `needs_manual_input`, `failed`
  - `jd_status`: `full_jd`, `partial_jd`, `contact_for_jd`, `no_jd`, `unclear`
  - `extraction_status`: `success`, `retried`, `failed`
  - `status`: `pending_review`, `saved`, `applied`, `interview`, `rejected`, `offer`, `ignored`
  - `applications.status`: `applied`, `interview`, `rejected`, `offer`
- Check score fields are either null or in valid ranges:
  - normalized scores: `0 <= value <= 1`
  - `final_score_percent`: `0 <= value <= 100`

## 11. Configuration Plan

Create `backend/app/core/config.py` using `pydantic-settings`.

Requirements:

- Load the root `.env` from the project root, not `backend/.env`.
- Resolve the root `.env` by path from `backend/app/core/config.py`, not by process current working directory.
- Running backend scripts from `backend/` still loads values from the root `.env`.
- Running backend modules from the project root also loads the same root `.env`.
- No second backend `.env` file is required.
- No frontend `.env` file is introduced in Phase 1.
- Expose typed settings for:
  - `ENV`
  - `BACKEND_PORT`
  - `FRONTEND_PORT`
  - `DATABASE_URL`
  - `SQLITE_DB_PATH`
  - `QDRANT_URL`
  - `QDRANT_API_KEY`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_EMBEDDING_MODEL`
  - `EMBEDDING_DIMENSION`
  - `TAVILY_API_KEY`
  - all max/timeout limits from `.env.example`
- Keep API keys backend-only.
- Do not expose frontend config in Phase 1.

Recommended path handling:

- Define project root from `Path(__file__).resolve().parents[3]`.
- Define backend root from `project_root / "backend"`.
- Load `env_file=project_root / ".env"`.
- Resolve relative `SQLITE_DB_PATH` against `backend/` so the database file remains `backend/data/job_matching.db` regardless of launch directory.

Create `backend/app/db/session.py`:

- Build an async engine from the resolved SQLite async URL.
- Create `async_sessionmaker`.
- Register SQLite PRAGMA connection listener on `engine.sync_engine`.
- Export `Base` or import it from `models.py`.

Create `backend/scripts/init_db.py`:

- Ensure `backend/data/` exists.
- Import all SQLAlchemy models.
- Run `Base.metadata.create_all()` through the async engine.
- Print created database path and table names.

Create `backend/scripts/verify_db_schema.py`:

- Inspect the initialized SQLite schema automatically.
- Verify all 3 tables exist.
- Verify required columns exist.
- Verify foreign keys exist.
- Verify required indexes exist.
- Verify `idx_job_posts_raw_content_hash` is a partial unique index with `WHERE raw_content_hash IS NOT NULL`.
- Verify `PRAGMA foreign_keys;` returns `1` on the configured SQLAlchemy connection.
- Verify `PRAGMA journal_mode;` returns `wal` if WAL mode is enabled.
- Exit nonzero with a clear message if any required check fails.

## 12. Implementation Steps

1. Create directory skeleton and `.gitkeep` files.
2. Add `.gitignore`.
3. Add root `.env.example`.
4. Add `docker-compose.yml` with only Qdrant.
5. Add `backend/requirements.txt`.
6. Create and activate the backend virtual environment.
7. Install backend dependencies.
8. Add `backend/app/core/config.py` with root `.env` resolution that works from project root and `backend/`.
9. Add `backend/app/core/logging.py` with minimal reusable logging setup.
10. Add `backend/app/db/models.py` with the three tables, UUID defaults, constraints, and indexes.
11. Add `backend/app/db/session.py` with async engine/session and SQLite PRAGMAs.
12. Add `backend/scripts/init_db.py`.
13. Add `backend/scripts/verify_db_schema.py`.
14. Run `python scripts/init_db.py` from `backend/`.
15. Verify the SQLite file exists at `backend/data/job_matching.db`.
16. Run `python scripts/verify_db_schema.py` from `backend/`.
17. Verify the partial unique index SQL includes `WHERE raw_content_hash IS NOT NULL`.
18. Verify `PRAGMA foreign_keys;` returns `1`.
19. Verify `PRAGMA journal_mode;` returns `wal` if WAL is enabled.
20. Verify config loading from both project root and `backend/`.
21. Run `docker compose config --services` and confirm only `qdrant`.
22. Run Qdrant locally with `docker compose up -d qdrant`.
23. Confirm no PostgreSQL dependencies or services were added.
24. Confirm Phase 1 has not implemented APIs, extraction, LangGraph, scoring, deduplication behavior, Qdrant vectors, or React UI.

## 13. Verification Checklist

Run from project root unless stated otherwise.

```powershell
docker compose config --services
```

Expected:

```text
qdrant
```

Run Qdrant:

```powershell
docker compose up -d qdrant
docker compose ps
Invoke-RestMethod http://localhost:6333/
```

Run DB initialization:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/init_db.py
```

Expected:

- `backend/data/job_matching.db` exists.
- Tables exist:
  - `role_profiles`
  - `job_posts`
  - `applications`
- Indexes exist:
  - `idx_job_posts_status`
  - `idx_job_posts_final_score`
  - `idx_job_posts_jd_status`
  - `idx_job_posts_batch_id`
  - `idx_job_posts_role_profile_status_score`
  - `idx_job_posts_raw_content_hash`
  - `idx_job_posts_dedup_key`
  - `idx_applications_job_post_id`

Run automated schema inspection:

```powershell
python scripts/verify_db_schema.py
```

The script must verify at least:

- all 3 tables exist
- required columns exist
- foreign keys exist
- indexes exist
- partial unique index exists
- `PRAGMA foreign_keys=ON`
- WAL mode if enabled

Manual schema inspection command:

```powershell
@'
import sqlite3

conn = sqlite3.connect("data/job_matching.db")
rows = conn.execute("""
SELECT type, name, tbl_name, sql
FROM sqlite_master
WHERE type IN ('table', 'index')
ORDER BY type, name
""").fetchall()

for row in rows:
    print(row[0], row[1], row[2])
    if row[3]:
        print(row[3])
        print()
'@ | python -
```

Partial unique index verification:

```powershell
@'
import sqlite3

conn = sqlite3.connect("data/job_matching.db")
row = conn.execute("""
SELECT name, sql
FROM sqlite_master
WHERE type = 'index'
  AND name = 'idx_job_posts_raw_content_hash'
""").fetchone()

print(row[0])
print(row[1])
assert "WHERE raw_content_hash IS NOT NULL" in row[1]
'@ | python -
```

Expected SQL includes:

```text
WHERE raw_content_hash IS NOT NULL
```

SQLite PRAGMA verification:

```powershell
@'
import asyncio
from sqlalchemy import text
from app.db.session import engine

async def main():
    async with engine.connect() as conn:
        foreign_keys = (await conn.execute(text("PRAGMA foreign_keys"))).scalar()
        journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
        print(foreign_keys)
        print(journal_mode)

asyncio.run(main())
'@ | python -
```

Expected:

```text
1
wal
```

If WAL is intentionally skipped, document the reason in `backend/scripts/verify_db_schema.py` output and in the implementation report. Otherwise, treat a non-`wal` result as a Phase 1 verification failure.

Dependency safety check:

```powershell
Select-String -Path requirements.txt -Pattern "psycopg2|asyncpg|postgres" -CaseSensitive
```

Expected: no matches.

Config import check from `backend/`:

```powershell
python -c "from app.core.config import settings; print(settings.database_url); print(settings.sqlite_db_path)"
```

Expected:

```text
sqlite+aiosqlite:///./data/job_matching.db
./data/job_matching.db
```

Config import check from project root:

```powershell
python -c "import sys; sys.path.insert(0, 'backend'); from app.core.config import settings; print(settings.database_url); print(settings.sqlite_db_path)"
```

Expected: the same root `.env` values printed by the `backend/` command.

No extra env files:

```powershell
Get-ChildItem -Recurse -Force -Filter ".env*" | Select-Object FullName
```

Expected:

- `.env.example` at project root
- optional local `.env` at project root
- no `backend/.env`
- no frontend `.env`

## 14. Acceptance Criteria

- Qdrant Local can start using Docker Compose.
- SQLite database file is created locally.
- `role_profiles`, `job_posts`, and `applications` tables exist.
- UUID fields are stored as TEXT.
- JSON-like fields are stored in SQLite-compatible format.
- `idx_job_posts_raw_content_hash` is a partial unique index with `WHERE raw_content_hash IS NOT NULL`.
- `idx_job_posts_dedup_key` exists.
- `idx_job_posts_role_profile_status_score` exists.
- `idx_applications_job_post_id` exists.
- Foreign keys are enabled with `PRAGMA foreign_keys=ON`.
- WAL mode is enabled or explicitly documented if skipped.
- Root `.env` is loaded correctly from both project root and `backend/`.
- Running backend scripts from `backend/` still loads values from the root `.env`.
- Running backend modules from the project root also loads the same root `.env`.
- No second backend `.env` file is required.
- No frontend `.env` file is introduced in Phase 1.
- No PostgreSQL dependency or Docker service is introduced.
- Phase 1 does not implement APIs, extraction, LangGraph, scoring, deduplication, Qdrant vectors, or React UI.

## 15. Expected Final State

After Phase 1 implementation:

- `docs/plans/Plan_1.md` exists with this plan.
- The project has a clean backend-first directory foundation.
- A root `.env.example` documents all required MVP environment values.
- `.env` is ignored and safe for local secrets.
- Qdrant Local runs through Docker Compose only.
- No PostgreSQL service, driver, or SQL syntax exists.
- SQLite database initializes locally at `backend/data/job_matching.db`.
- SQLAlchemy async configuration is reusable by later FastAPI routes and services.
- The three core tables, constraints, and required indexes exist.
- `idx_job_posts_raw_content_hash` is verified as a SQLite partial unique index with `WHERE raw_content_hash IS NOT NULL`.
- Foreign keys and WAL mode are verified.
- Root `.env` loading is verified from both project root and `backend/`.
- `backend/scripts/verify_db_schema.py` can inspect and fail fast on schema drift.

## 16. Handoff Notes for Phase 2

- Phase 1 provides config, DB session, SQLite models, and project structure.
- Phase 2 can build extraction services and LangGraph state on top of the shared config/session. FastAPI endpoints and ingestion orchestration remain Phase 4.
- Phase 2 consumes these foundations for extraction and LangGraph only.
- APIs and end-to-end ingestion are Phase 4 responsibilities.
- Use `backend/app/core/config.py` and `backend/app/db/session.py`; do not create a second config system.
- Always generate IDs with `uuid.uuid4()` and store them as UUID strings.
- Continue storing JSON-like fields such as `skills` as JSON strings unless a later plan explicitly changes this.
- Keep `role_profiles.matching_text` out of the schema; role query text is generated dynamically later in scoring.
- Use `job_posts.batch_id`; do not add a `search_runs` table for MVP.
- Keep raw SQL SQLite-compatible with `?` placeholders or SQLAlchemy bound parameters.
- Qdrant collection creation, embeddings, vector upsert/search/delete, payload indexes, and SQLite-Qdrant status sync belong to later phases.
- Deduplication behavior belongs to a later phase; Phase 1 only provides the schema fields and indexes.
