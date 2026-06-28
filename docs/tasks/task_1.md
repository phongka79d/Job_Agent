# Agentic Job Matching System Plan 1 Execution Tasks

## Purpose

Define the execution work for Plan 1: backend foundation, root environment contract, SQLite schema, local Qdrant infrastructure, and verification gates for later phases.

This task file is for future execution agents. It must not be treated as implementation progress by itself.

## Authoritative Source

- Primary phase source: `docs/plans/Plan_1.md`
- Master architecture source: `docs/plans/Master_Plan.md`
- Output task file: `docs/tasks/task_1.md`

No implementation code, runtime configuration, migrations, or tests are performed by this task-writing pass.

## Source Section Index

- `docs/plans/Plan_1.md` > `## 1. Objective` -> phase goal and stable storage/configuration contract.
- `docs/plans/Plan_1.md` > `## 2. Source of Truth` -> master sections that govern Plan 1.
- `docs/plans/Plan_1.md` > `## 3. Prerequisites from Prior Phases` -> local prerequisites and no prior phase dependency.
- `docs/plans/Plan_1.md` > `## 4. Scope` -> mandatory implementation scope for Plan 1.
- `docs/plans/Plan_1.md` > `## 5. Out of Scope` -> explicit phase boundaries.
- `docs/plans/Plan_1.md` > `## 6. Target Directory Structure` -> required files and folders for this phase.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Environment Settings` -> single root `.env.example` contract and backend-only secrets.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Repository Ignore Rules` -> required `.gitignore` entries and keep rules.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Backend Dependencies` -> runtime and test dependency files.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### SQLite Rules` -> async SQLAlchemy, UUID, JSON, boolean, timestamp, and PRAGMA rules.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### MVP Table Boundary` -> exactly three application tables.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Table: role_profiles` -> exact role profile columns and hard `matching_text` exclusion.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Table: job_posts` -> exact job post columns and status/source values.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Shared Status and Source Constants` -> reusable backend constants contract.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Table: applications` -> exact application columns and delete behavior note.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Required Indexes` -> exact SQLite indexes.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Qdrant Infrastructure` -> local Qdrant Docker Compose only.
- `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Backend Dockerfile Boundary` -> backend image boundary.
- `docs/plans/Plan_1.md` > `## 8. Implementation Steps` -> required phase checklist.
- `docs/plans/Plan_1.md` > `## 9. Verification & Testing Plan` -> required validation commands and expected outcomes.
- `docs/plans/Plan_1.md` > `## 10. Handoff Notes for Phase 2` -> contracts consumed by later phases.
- `docs/plans/Master_Plan.md` > `## 1. System Objective` -> overall MVP system goal.
- `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack` -> approved stack.
- `docs/plans/Master_Plan.md` > `## 3. MVP Scope` -> in-scope and out-of-scope MVP boundaries.
- `docs/plans/Master_Plan.md` > `## 20. SQLite Database Design` -> database file, table set, and SQLite implementation rules.
- `docs/plans/Master_Plan.md` > `## 21. Table: role_profiles` -> master role profile table contract.
- `docs/plans/Master_Plan.md` > `## 22. Table: job_posts` -> master job post table contract.
- `docs/plans/Master_Plan.md` > `## 23. Table: applications` -> master application table contract.
- `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes` -> master index contract and expected query support.
- `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema` -> Qdrant runtime and UUID point ID constraints.
- `docs/plans/Master_Plan.md` > `## 30. Project Directory Structure` -> final project structure.
- `docs/plans/Master_Plan.md` > `## 31. Environment Setup` -> backend runtime and test dependency contract.
- `docs/plans/Master_Plan.md` > `## 32. Single Root .env` -> root `.env` rule and backend-only secrets.
- `docs/plans/Master_Plan.md` > `## 33. Docker Compose` -> local Qdrant compose service.

## Approved Architecture Summary

- The MVP stack is FastAPI, LangChain/LangGraph, SQLite via SQLAlchemy and `aiosqlite`, local Qdrant via Docker Compose, and React in later phases.
- Plan 1 establishes backend folders, dependencies, root `.env.example`, `.gitignore`, config loading, logging, SQLAlchemy async database setup, SQLite models, indexes, constants, minimal FastAPI bootstrap, Qdrant compose, and backend Dockerfile.
- The SQLite database is the durable source of truth. Qdrant is a later derived vector/search index; Plan 1 only creates local Qdrant infrastructure.
- The only Plan 1 application tables are `role_profiles`, `job_posts`, and `applications`.
- UUID values must be generated and stored as canonical `TEXT` strings.
- Backend runtime config must load from the single project-root `.env`; Plan 1 creates only `.env.example` placeholders.
- API keys and backend-only configuration must not be exposed to frontend code.

## Global Implementation Rules

- Implement only Plan 1 scope. Do not add frontend code, extraction workflows, scoring services, LangGraph nodes, Qdrant collection code, public route modules, CORS, auth, organizations, background queues, Redis, Celery, cover letters, or auto-apply behavior.
- Do not create tables other than `role_profiles`, `job_posts`, and `applications`.
- Do not create a `search_runs` table. Batch tracking uses only `job_posts.batch_id`.
- Do not add `matching_text` to `role_profiles`; role query text is derived later in `scoring_service.py`.
- Do not rename or reinterpret any table fields, status values, source values, or environment variable names from Plan 1.
- Use `.env.example` for placeholders only. Do not commit `.env`, real API keys, local database files, virtual environments, frontend dependencies, or build output.
- Keep Docker Compose limited to local Qdrant in this phase. Do not add a backend service to `docker-compose.yml`.
- If user-provided local secrets are missing, report `BLOCKED_BY_USER_ACTION`; do not fabricate keys or mark secret-dependent validation complete.
- If `applications.job_post_id` does not use `ON DELETE CASCADE`, document that Plan 4 reset logic must delete matching `applications` rows before deleting mock-owned `job_posts`.

## Execution Agent Coding Style Requirements

- Write clean, idiomatic, readable Python and configuration files.
- Use descriptive names for modules, functions, variables, settings, models, constants, and tests.
- Keep functions and modules focused on one clear responsibility.
- Prefer simple, explicit control flow over clever abstractions.
- Follow FastAPI, Pydantic v2, SQLAlchemy 2.x async, and pytest conventions.
- Use clear typing where Python supports it.
- Avoid `any`, broad exception handling, hidden global state, and hardcoded configuration values unless explicitly required by Plan 1.
- Add comments only for non-obvious decisions or behavior.
- Keep frontend code free of backend-only secrets and backend-only configuration names.
- Avoid adding formatters, linters, frameworks, services, or architecture changes outside the source plan unless already present or explicitly requested.

## Batch Map

- Batch01 - Repository Foundation and Local Infrastructure
- Batch02 - Backend Configuration and Shared Contracts
- Batch03 - SQLite Models, Indexes, and Session
- Batch04 - App Bootstrap and Verification

## Mandatory Batch01 - Repository Foundation and Local Infrastructure

### Goal

Create the Plan 1 repository structure, backend dependency files, root environment example, ignore rules, local Qdrant compose file, and backend Dockerfile boundary.

### Why this batch exists

Plan 1 must establish a stable project foundation before backend configuration and database code can rely on known paths, dependencies, and local infrastructure.

### Inputs / Dependencies

- `docs/plans/Plan_1.md`
- `docs/plans/Master_Plan.md`
- Local repository root `Job_Agent/`
- Python 3.11+ available locally
- Docker Desktop or Docker Engine available for Qdrant validation

### Tasks

- [x] (01A): Create backend package skeleton and placeholder files
  - Source of Truth: `docs/plans/Plan_1.md` > `## 4. Scope`; `docs/plans/Plan_1.md` > `## 6. Target Directory Structure`; `docs/plans/Master_Plan.md` > `## 30. Project Directory Structure`
  - Source Requirements:
    - Create backend package layout under `backend/app/`.
    - Add `backend/data/.gitkeep` so the local SQLite directory exists.
    - Add `backend/app/db/migrations/.gitkeep`.
  - Details: Create only the Plan 1 backend package skeleton and keep files required for later batches.
  - Dependencies: None
  - User Action: None
  - Agent Work: Create directories and `__init__.py` files for `api`, `agents`, `core`, `db`, and `services`; create data and migration keep files.
  - Specific Steps:
    1. Create `backend/app/api/`, `backend/app/agents/`, `backend/app/core/`, `backend/app/db/migrations/`, `backend/app/services/`, `backend/data/`, and `backend/tests/`.
    2. Add `__init__.py` files under each backend package directory required by Plan 1.
    3. Add `backend/data/.gitkeep`.
    4. Add `backend/app/db/migrations/.gitkeep`.
    5. Confirm no frontend folders or route modules are created as part of this task.
  - Output: Backend folder skeleton and placeholder files.
  - Acceptance: Required Plan 1 directories and package initializers exist, with no out-of-scope application modules added.
  - Validation: List the created paths and compare them against `docs/plans/Plan_1.md` > `## 6. Target Directory Structure`.
  - Blocked Condition: None
  - Files: `backend/app/**/__init__.py`, `backend/data/.gitkeep`, `backend/app/db/migrations/.gitkeep`

- [x] (01B): Add backend runtime and test dependency files
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Backend Dependencies`; `docs/plans/Master_Plan.md` > `## 31. Environment Setup`
  - Source Requirements:
    - `backend/requirements.txt` must include all MVP backend packages.
    - `backend/requirements-dev.txt` must include `-r requirements.txt`, `pytest`, `pytest-asyncio`, and `respx`.
    - A clean backend environment must be able to run `pytest` after installing `requirements-dev.txt`.
  - Details: Create dependency files exactly for backend runtime and test-capable local setup.
  - Dependencies: (01A)
  - User Action: None
  - Agent Work: Add the required package constraints from Plan 1 without adding unrelated tooling.
  - Specific Steps:
    1. Create `backend/requirements.txt` with FastAPI, Uvicorn, Pydantic, LangChain, LangGraph, Qdrant, Tavily, httpx, trafilatura, SQLAlchemy, Alembic, aiosqlite, python-dotenv, tenacity, and numpy requirements.
    2. Create `backend/requirements-dev.txt` with `-r requirements.txt`.
    3. Add `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, and `respx>=0.21.0`.
    4. Do not add frontend dependencies or unrelated developer tools.
  - Output: Backend dependency files.
  - Acceptance: Dependency files match Plan 1 package lists and support future Plans 2 through 4 tests.
  - Validation: Run `pip install -r requirements-dev.txt` from `backend` in a fresh or existing local virtual environment.
  - Blocked Condition: None
  - Files: `backend/requirements.txt`, `backend/requirements-dev.txt`

- [x] (01C): Add root environment example and repository ignore rules
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Environment Settings`; `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Repository Ignore Rules`; `docs/plans/Master_Plan.md` > `## 32. Single Root .env`
  - Source Requirements:
    - Use one root `.env` file loaded by backend configuration.
    - Phase 1 creates `.env.example` only.
    - Local root `.env`, SQLite database files, virtual environments, frontend dependencies, and build outputs must be ignored.
    - No API keys may be exposed to frontend code.
  - Details: Create the root config example and git ignore contract for local secrets and generated artifacts.
  - Dependencies: (01A)
  - User Action: User may later copy `.env.example` to root `.env` and add real local secrets; the agent must not create real secret values.
  - Agent Work: Add safe placeholder variables to `.env.example` and required ignore/keep rules to `.gitignore`.
  - Specific Steps:
    1. Create root `.env.example` using every environment variable listed in Plan 1.
    2. Use placeholder API key values only, never real secrets.
    3. Create or update root `.gitignore` with required ignore entries for `.env`, virtual environments, caches, generated SQLite files, frontend dependencies, and frontend build output.
    4. Add keep rules for `.env.example`, `backend/data/.gitkeep`, and `backend/app/db/migrations/.gitkeep`.
    5. Confirm no frontend-specific `.env` or `.env.example` is created.
  - Output: Root `.env.example` and `.gitignore`.
  - Acceptance: The repository has the single root environment example and git ignore behavior required by Plan 1.
  - Validation: Run `git check-ignore .env`, `git check-ignore backend/data/job_matching.db`, `git check-ignore backend/data/job_matching.db-wal`, `git check-ignore backend/.venv/pyvenv.cfg`, and `git check-ignore frontend/job-agent-ui/node_modules/example`.
  - Blocked Condition: None
  - Files: `.env.example`, `.gitignore`

- [x] (01D): Add local Qdrant Docker Compose infrastructure
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Qdrant Infrastructure`; `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema`; `docs/plans/Master_Plan.md` > `## 33. Docker Compose`
  - Source Requirements:
    - Create only the local Docker Compose service for Qdrant in Plan 1.
    - Use `qdrant/qdrant:latest`, container name `job_agent_qdrant_local`, ports `6333` and `6334`, and persistent `qdrant_data` volume.
    - Do not create Qdrant collections, payload indexes, vectors, upserts, deletes, queries, or Qdrant service code in this phase.
  - Details: Add local vector database infrastructure without implementing vector runtime behavior.
  - Dependencies: None
  - User Action: Docker Desktop or Docker Engine must be running before Docker validation.
  - Agent Work: Create root `docker-compose.yml` with only the Qdrant service and volume.
  - Specific Steps:
    1. Create or update root `docker-compose.yml`.
    2. Add the Qdrant service exactly as specified by Plan 1.
    3. Add the persistent `qdrant_data` volume.
    4. Confirm no backend, SQLite, frontend, Redis, Celery, worker, or cron service is added.
  - Output: Local Qdrant Docker Compose file.
  - Acceptance: `docker-compose.yml` contains only the Plan 1 Qdrant service and volume.
  - Validation: Run `docker compose up -d qdrant`, `docker compose ps`, and `docker compose down` when Docker is available.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` if Docker is not installed or not running.
  - Files: `docker-compose.yml`

- [x] (01E): Add minimal backend Dockerfile
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Backend Dockerfile Boundary`; `docs/plans/Plan_1.md` > `## 8. Implementation Steps`
  - Source Requirements:
    - Backend Dockerfile must package the FastAPI backend only.
    - It must use a Python runtime image, workdir `/app`, install `requirements.txt`, copy backend app code, and run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
    - It must not bake API keys or `.env` values into the image.
    - It must not start Qdrant, SQLite as a service, workers, frontend code, Redis, Celery, or cron jobs.
  - Details: Add a minimal backend containerization boundary for later use without changing Docker Compose scope.
  - Dependencies: (01A), (01B)
  - User Action: None
  - Agent Work: Create `backend/Dockerfile` using only the approved backend runtime behavior.
  - Specific Steps:
    1. Select an appropriate Python runtime image.
    2. Set `WORKDIR /app`.
    3. Copy `requirements.txt` and install backend dependencies.
    4. Copy backend application code.
    5. Set the default command to run Uvicorn on host `0.0.0.0` and port `8000`.
    6. Confirm no `.env`, API key, frontend, Qdrant startup, queue, worker, Redis, Celery, or cron behavior is included.
  - Output: Minimal backend Dockerfile.
  - Acceptance: Dockerfile scope matches Plan 1 and does not alter `docker-compose.yml`.
  - Validation: Review Dockerfile contents against the Plan 1 boundary; optionally build the image after backend app files exist.
  - Blocked Condition: None
  - Files: `backend/Dockerfile`

### Files or Modules Likely Created or Updated

- `.env.example`
- `.gitignore`
- `docker-compose.yml`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/requirements-dev.txt`
- `backend/app/**/__init__.py`
- `backend/data/.gitkeep`
- `backend/app/db/migrations/.gitkeep`

### Required Outputs / Artifacts

- Plan 1 backend folder skeleton.
- Backend runtime and test dependency files.
- Single root `.env.example`.
- Root `.gitignore` with required ignore and keep rules.
- Qdrant-only Docker Compose service.
- Backend-only Dockerfile.

### Acceptance Criteria

- All required files exist in the locations specified by Plan 1.
- `.env.example` contains no real API keys.
- `.gitignore` protects local secrets and generated artifacts while keeping required examples and placeholders.
- Docker Compose is limited to Qdrant.
- Backend Dockerfile packages only the FastAPI backend.

### Required Tests or Validations

- `git check-ignore .env`
- `git check-ignore backend/data/job_matching.db`
- `git check-ignore backend/data/job_matching.db-wal`
- `git check-ignore backend/.venv/pyvenv.cfg`
- `git check-ignore frontend/job-agent-ui/node_modules/example`
- `docker compose up -d qdrant`
- `docker compose ps`
- `docker compose down`

### Explicit Non-Goals

- No backend service in Docker Compose.
- No Qdrant collection or service code.
- No frontend project creation.
- No API route modules beyond package placeholders.
- No LangGraph, extraction, scoring, or Qdrant runtime behavior.

## Mandatory Batch02 - Backend Configuration and Shared Contracts

### Goal

Implement root environment loading, backend logging, shared status/source constants, and a contract test for constants consumed by later phases.

### Why this batch exists

Later phases depend on stable configuration names and shared executable constants. Plan 1 centralizes these contracts so status and source strings do not drift across services, schemas, routes, demo loading, and frontend serialization.

### Inputs / Dependencies

- Completed Batch01.
- Root `.env.example`.
- Backend package skeleton under `backend/app/`.
- Dependency files available for local environment setup.

### Tasks

- [ ] (02A): Implement root `.env` backend settings loader
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Environment Settings`; `docs/plans/Master_Plan.md` > `## 32. Single Root .env`
  - Source Requirements:
    - Backend configuration must load from the repository root, not from `backend/.env`.
    - Required settings must match the master environment contract.
    - API keys must remain backend-only and must not be exposed to frontend code.
  - Details: Add Pydantic settings that can read the root `.env` while preserving safe defaults and explicit names from Plan 1.
  - Dependencies: (01A), (01B), (01C)
  - User Action: User must create a local root `.env` from `.env.example` before validating secret-backed services in later phases.
  - Agent Work: Implement `backend/app/core/config.py` with Pydantic settings for every Plan 1 variable.
  - Specific Steps:
    1. Define a settings class using Pydantic Settings.
    2. Configure environment loading from the repository root `.env`.
    3. Include all variables from Plan 1 with appropriate types for ports, limits, dimensions, timeout, response size, and URLs.
    4. Avoid printing or logging secret values.
    5. Expose a backend-only `settings` instance for imports by later modules.
    6. Verify settings can be imported from the backend working directory.
  - Output: Backend configuration module.
  - Acceptance: `from app.core.config import settings` succeeds and `settings.DATABASE_URL` resolves to the Plan 1 default or local root `.env` value.
  - Validation: From `backend`, run `python -c "from app.core.config import settings; print(settings.DATABASE_URL)"`.
  - Blocked Condition: None for placeholder/default import validation; `BLOCKED_BY_USER_ACTION` for real external API validation without user-provided secrets.
  - Files: `backend/app/core/config.py`

- [ ] (02B): Implement basic backend logging setup
  - Source of Truth: `docs/plans/Plan_1.md` > `## 4. Scope`; `docs/plans/Plan_1.md` > `## 8. Implementation Steps`
  - Source Requirements:
    - Add basic logging setup for backend services.
    - Keep secrets out of logs.
  - Details: Add simple reusable logging configuration without introducing an external logging stack.
  - Dependencies: (01A), (02A)
  - User Action: None
  - Agent Work: Implement `backend/app/core/logging.py` with a simple structured or standard logging setup.
  - Specific Steps:
    1. Create a logging setup function for backend application startup.
    2. Use standard Python logging unless an already-approved dependency provides equivalent behavior.
    3. Avoid logging raw settings or secrets.
    4. Keep logging behavior simple and importable by `app.main`.
  - Output: Backend logging module.
  - Acceptance: Logging setup can be imported without side effects and does not expose secret values.
  - Validation: Import the logging module from `backend` with `python -c "from app.core.logging import setup_logging; setup_logging(); print('logging ok')"`.
  - Blocked Condition: None
  - Files: `backend/app/core/logging.py`

- [ ] (02C): Add shared status and source constants
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Shared Status and Source Constants`; `docs/plans/Master_Plan.md` > `## 22. Table: job_posts`; `docs/plans/Master_Plan.md` > `## 23. Table: applications`
  - Source Requirements:
    - Create reusable backend constants or enum-like literal sets in a single backend module.
    - Include `JOB_STATUSES`, `TRACKED_JOB_STATUSES`, `APPLICATION_STATUSES`, `JD_STATUSES`, `PARSE_STATUSES`, `EXTRACTION_STATUSES`, `SOURCE_PLATFORMS`, and `INPUT_SOURCES`.
    - Constants must not create new tables or alter the database schema.
    - Later phases must import these constants for executable validation.
  - Details: Add central executable status/source values for the backend contract.
  - Dependencies: (01A)
  - User Action: None
  - Agent Work: Implement constants in `backend/app/core/constants.py` with exact Plan 1 values.
  - Specific Steps:
    1. Create `backend/app/core/constants.py`.
    2. Define immutable tuple or frozenset values for each required constant group.
    3. Use exactly the status/source strings from Plan 1.
    4. Do not add extra values, database schema code, imports from models, or external dependencies.
    5. Ensure the module is importable by tests and later backend services.
  - Output: Shared constants module.
  - Acceptance: Constants expose only the Plan-approved values and can be imported by other backend modules.
  - Validation: Run a Python import check for `app.core.constants` from `backend`.
  - Blocked Condition: None
  - Files: `backend/app/core/constants.py`

- [ ] (02D): Add constants contract test
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Shared Status and Source Constants`; `docs/plans/Plan_1.md` > `## 8. Implementation Steps`; `docs/plans/Plan_1.md` > `## 9. Verification & Testing Plan`
  - Source Requirements:
    - Add `backend/tests/test_constants_contract.py` or an equivalent lightweight import check.
    - Test must prove shared constants expose the exact Master Plan status/source values consumed by later phases.
  - Details: Lock the constants contract with a lightweight pytest test.
  - Dependencies: (01B), (02C)
  - User Action: None
  - Agent Work: Create a pytest file that imports the constants and compares exact values.
  - Specific Steps:
    1. Create `backend/tests/test_constants_contract.py`.
    2. Assert every required constant group exists.
    3. Assert each group contains exactly the Plan 1 values.
    4. Assert tracked statuses are a subset of job statuses.
    5. Keep the test independent from database initialization.
  - Output: Constants contract test.
  - Acceptance: `pytest tests/test_constants_contract.py` passes after installing `requirements-dev.txt`.
  - Validation: From `backend`, run `pytest tests/test_constants_contract.py`.
  - Blocked Condition: None
  - Files: `backend/tests/test_constants_contract.py`

### Files or Modules Likely Created or Updated

- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/core/constants.py`
- `backend/tests/test_constants_contract.py`

### Required Outputs / Artifacts

- Importable settings object loading from root `.env`.
- Importable logging setup.
- Central status/source constants.
- Passing constants contract test.

### Acceptance Criteria

- Backend settings use the single root environment contract.
- No secret values are logged or exposed.
- Constants contain exact Plan 1 values and no local service copies are invented.
- Contract test passes after installing backend dev requirements.

### Required Tests or Validations

- `python -c "from app.core.config import settings; print(settings.DATABASE_URL)"`
- `python -c "from app.core.logging import setup_logging; setup_logging(); print('logging ok')"`
- `python -c "from app.core import constants; print(constants.JOB_STATUSES)"`
- `pytest tests/test_constants_contract.py`

### Explicit Non-Goals

- No runtime service logic.
- No frontend config exposure.
- No external API validation using real secrets.
- No database schema creation in this batch.

## Mandatory Batch03 - SQLite Models, Indexes, and Session

### Goal

Implement SQLAlchemy async database setup, exact MVP models, indexes, constraints, UUID/timestamp/JSON storage approach, and SQLite startup PRAGMAs.

### Why this batch exists

Plan 1's primary contract is the durable SQLite schema consumed by later extraction, scoring, route, demo, and frontend phases. This batch must keep the schema exact and verifiable.

### Inputs / Dependencies

- Completed Batch01.
- Completed Batch02.
- `backend/app/core/config.py`
- `backend/app/core/constants.py`
- SQLAlchemy and `aiosqlite` dependencies available.

### Tasks

- [ ] (03A): Add SQLAlchemy model base and storage conventions
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### SQLite Rules`; `docs/plans/Master_Plan.md` > `## 20. SQLite Database Design`
  - Source Requirements:
    - Use SQLAlchemy async engine with `sqlite+aiosqlite`.
    - Store UUID values as `TEXT` canonical UUID strings.
    - Store JSON arrays as JSON encoded `TEXT`.
    - Store booleans as SQLAlchemy Boolean or SQLite integer-compatible values.
    - Store timestamps consistently as SQLAlchemy DateTime or ISO-8601 text.
  - Details: Establish model base and helper conventions used by the three table models.
  - Dependencies: (01B), (02C)
  - User Action: None
  - Agent Work: Create `backend/app/db/models.py` with SQLAlchemy base metadata and consistent column choices.
  - Specific Steps:
    1. Create or update `backend/app/db/models.py`.
    2. Define SQLAlchemy Declarative Base using SQLAlchemy 2.x conventions.
    3. Use string UUID primary key fields with generated canonical UUID defaults where appropriate.
    4. Use `Text` for JSON-encoded skill arrays.
    5. Use consistent timestamp column types and defaults.
    6. Avoid schema objects for non-MVP tables.
  - Output: SQLAlchemy model base and storage conventions.
  - Acceptance: Model metadata exists and is ready for exactly three MVP application tables.
  - Validation: Import `app.db.models` from `backend`.
  - Blocked Condition: None
  - Files: `backend/app/db/models.py`

- [ ] (03B): Define `role_profiles` model exactly
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Table: role_profiles`; `docs/plans/Master_Plan.md` > `## 21. Table: role_profiles`
  - Source Requirements:
    - Required columns are `id`, `target_role`, `level`, `location`, `accept_remote`, `skills`, `resume_text`, `created_at`, and `updated_at`.
    - `id` is `TEXT` primary key.
    - `target_role` is not null.
    - Do not add `matching_text`.
  - Details: Add the role profile ORM model with exact Plan 1 columns.
  - Dependencies: (03A)
  - User Action: None
  - Agent Work: Define `RoleProfile` in `backend/app/db/models.py`.
  - Specific Steps:
    1. Add `RoleProfile.__tablename__ = "role_profiles"`.
    2. Define every required column with the approved storage type.
    3. Mark `target_role` as not nullable.
    4. Add relationship declarations only if they do not change schema or add tables.
    5. Verify `matching_text` is not present.
  - Output: `RoleProfile` ORM model.
  - Acceptance: `role_profiles` schema matches Plan 1 and has no `matching_text` column.
  - Validation: After database initialization, inspect `PRAGMA table_info(role_profiles)` and confirm `matching_text` is absent.
  - Blocked Condition: None
  - Files: `backend/app/db/models.py`

- [ ] (03C): Define `job_posts` model exactly
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Table: job_posts`; `docs/plans/Master_Plan.md` > `## 22. Table: job_posts`; `docs/plans/Master_Plan.md` > `## 16. Simplified Deduplication Strategy`
  - Source Requirements:
    - Required columns include all Plan 1 identifiers, extracted fields, source fields, status fields, dedup fields, score fields, token/cost fields, and timestamps.
    - `id` is `TEXT` primary key.
    - `batch_id` and `role_profile_id` are not null.
    - `role_profile_id` is a foreign key to `role_profiles.id`.
    - Allowed job status values are `pending_review`, `saved`, `applied`, `interview`, `rejected`, `offer`, and `ignored`.
    - Allowed source platform values are `tavily`, `manual_url`, `manual_text`, `mock`, and `job_board`.
  - Details: Add the central job post ORM model without implementing extraction, scoring, or dedup services.
  - Dependencies: (02C), (03A), (03B)
  - User Action: None
  - Agent Work: Define `JobPost` in `backend/app/db/models.py` with exact columns and foreign key.
  - Specific Steps:
    1. Add `JobPost.__tablename__ = "job_posts"`.
    2. Define every required Plan 1 column.
    3. Add `role_profile_id` foreign key to `role_profiles.id`.
    4. Add nullable self-reference `duplicate_of_job_id` to `job_posts.id`.
    5. Use `Text` for JSON skill storage and embedding text.
    6. Use `Float` or equivalent for score and cost fields.
    7. Do not implement scoring formulas, extraction logic, Qdrant upserts, or dedup decisions in this task.
  - Output: `JobPost` ORM model.
  - Acceptance: `job_posts` schema matches Plan 1 and includes all status, dedup, score, token, cost, and timestamp fields.
  - Validation: After database initialization, inspect `PRAGMA table_info(job_posts)` and compare against Plan 1 required columns.
  - Blocked Condition: None
  - Files: `backend/app/db/models.py`

- [ ] (03D): Define `applications` model and delete behavior
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Table: applications`; `docs/plans/Master_Plan.md` > `## 23. Table: applications`
  - Source Requirements:
    - Required columns are `id`, `job_post_id`, `status`, `cv_version`, `notes`, `applied_at`, and `updated_at`.
    - `job_post_id` is not null and references `job_posts.id`.
    - Foreign key delete behavior must be explicit for demo reset safety.
    - If no `ON DELETE CASCADE` is configured, Plan 4 reset must delete matching applications before deleting mock-owned job posts.
  - Details: Add the application tracking ORM model with explicit foreign key behavior.
  - Dependencies: (03A), (03C)
  - User Action: None
  - Agent Work: Define `Application` in `backend/app/db/models.py`.
  - Specific Steps:
    1. Add `Application.__tablename__ = "applications"`.
    2. Define every required column.
    3. Add `job_post_id` foreign key to `job_posts.id`.
    4. Choose and document explicit delete behavior.
    5. Ensure allowed application statuses align with `APPLICATION_STATUSES`.
  - Output: `Application` ORM model.
  - Acceptance: `applications` schema matches Plan 1 and foreign key delete behavior is inspectable.
  - Validation: After database initialization, inspect `PRAGMA foreign_key_list(applications)` and note the `on_delete` value.
  - Blocked Condition: None
  - Files: `backend/app/db/models.py`

- [ ] (03E): Add exact indexes and constraints
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Required Indexes`; `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes`
  - Source Requirements:
    - Create the eight required indexes exactly.
    - Include the partial unique index `idx_job_posts_raw_content_hash` where `raw_content_hash IS NOT NULL`.
    - Include `idx_applications_job_post_id`.
  - Details: Add SQLAlchemy index declarations or equivalent schema creation so SQLite creates the exact required indexes.
  - Dependencies: (03B), (03C), (03D)
  - User Action: None
  - Agent Work: Add model-level indexes/constraints in `backend/app/db/models.py`.
  - Specific Steps:
    1. Add `idx_job_posts_status` on `job_posts(status)`.
    2. Add `idx_job_posts_final_score` on `job_posts(final_score DESC)`.
    3. Add `idx_job_posts_jd_status` on `job_posts(jd_status)`.
    4. Add `idx_job_posts_batch_id` on `job_posts(batch_id)`.
    5. Add `idx_job_posts_role_profile_status_score` on `job_posts(role_profile_id, status, final_score DESC)`.
    6. Add unique partial `idx_job_posts_raw_content_hash` on `raw_content_hash` where not null.
    7. Add `idx_job_posts_dedup_key` on `job_posts(dedup_key)`.
    8. Add `idx_applications_job_post_id` on `applications(job_post_id)`.
  - Output: Exact index declarations.
  - Acceptance: SQLite database contains all required index names after `init_db()`.
  - Validation: Query `sqlite_master` for indexes and confirm no required index is missing.
  - Blocked Condition: None
  - Files: `backend/app/db/models.py`

- [ ] (03F): Implement async session, database initialization, and SQLite PRAGMAs
  - Source of Truth: `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### SQLite Rules`; `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### MVP Table Boundary`; `docs/plans/Plan_1.md` > `## 9. Verification & Testing Plan`; `docs/plans/Master_Plan.md` > `## 20. SQLite Database Design`
  - Source Requirements:
    - Use SQLAlchemy async engine with `sqlite+aiosqlite`.
    - Enable `PRAGMA foreign_keys=ON` and `PRAGMA journal_mode=WAL`.
    - Database initialization creates only `role_profiles`, `job_posts`, and `applications`.
    - No `search_runs`, user, organization, analytics, vector metadata, or other MVP-irrelevant tables.
  - Details: Add database connection/session utilities and initialization guardrails.
  - Dependencies: (02A), (03A), (03B), (03C), (03D), (03E)
  - User Action: None
  - Agent Work: Create `backend/app/db/session.py` with async engine, session maker, and `init_db()`.
  - Specific Steps:
    1. Create async engine using `settings.DATABASE_URL`.
    2. Create async session maker.
    3. Add connection event handling so SQLite foreign keys are enabled.
    4. Ensure WAL mode is enabled for the SQLite database.
    5. Implement `init_db()` that creates metadata for exactly the three MVP models.
    6. Add a local data directory creation guard if needed for `backend/data/job_matching.db`.
    7. Verify metadata table names are exactly `applications`, `job_posts`, and `role_profiles`.
  - Output: Async database session and initialization module.
  - Acceptance: `asyncio.run(init_db())` creates the local database and only the three MVP tables.
  - Validation: From `backend`, run `python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"` and then run the SQLite verification script from Plan 1.
  - Blocked Condition: None
  - Files: `backend/app/db/session.py`

### Files or Modules Likely Created or Updated

- `backend/app/db/models.py`
- `backend/app/db/session.py`
- `backend/data/job_matching.db` during local validation only; generated file must remain ignored.

### Required Outputs / Artifacts

- Exact ORM models for `role_profiles`, `job_posts`, and `applications`.
- Exact required SQLite indexes.
- Async SQLAlchemy engine and session maker.
- Database initialization function.
- SQLite foreign key and WAL PRAGMA behavior.

### Acceptance Criteria

- Database initialization creates exactly the three MVP tables.
- Required columns and indexes exist.
- `role_profiles` has no `matching_text`.
- No `search_runs` or out-of-scope table exists.
- UUIDs are stored as canonical text strings.
- JSON arrays are stored as JSON encoded text.
- Foreign keys are enabled for app-managed connections.
- WAL mode is enabled.

### Required Tests or Validations

- `python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"`
- `python -c "from app.db.models import RoleProfile, JobPost, Application; print(RoleProfile.__tablename__, JobPost.__tablename__, Application.__tablename__)"`
- SQLite table/index/foreign-key verification script from Plan 1.
- App-session PRAGMA verification script from Plan 1.

### Explicit Non-Goals

- No Alembic migration generation beyond creating migration placeholder directory.
- No extraction, scoring, Qdrant service, dedup service, or API workflow logic.
- No new database tables.
- No role query text persistence.

## Mandatory Batch04 - App Bootstrap and Verification

### Goal

Add a minimal FastAPI app entrypoint that initializes the database and run the full Plan 1 verification suite, including scope and handoff checks.

### Why this batch exists

Plan 1 is complete only when the backend foundation can import, initialize the database, satisfy schema/index constraints, protect local files, and hand stable contracts to Plan 2.

### Inputs / Dependencies

- Completed Batch01.
- Completed Batch02.
- Completed Batch03.
- Local Python environment with `backend/requirements-dev.txt` installed.
- Docker available for Qdrant validation where possible.

### Tasks

- [ ] (04A): Add minimal FastAPI application entrypoint
  - Source of Truth: `docs/plans/Plan_1.md` > `## 4. Scope`; `docs/plans/Plan_1.md` > `## 8. Implementation Steps`; `docs/plans/Plan_1.md` > `## 5. Out of Scope`
  - Source Requirements:
    - Add a minimal FastAPI app entrypoint that can initialize the database.
    - Do not implement API job workflows beyond minimal app bootstrap.
    - Do not add CORS, public API route modules, request/response schemas, or frontend integration in this phase.
  - Details: Create `backend/app/main.py` with basic app construction, logging setup, and database startup initialization.
  - Dependencies: (02A), (02B), (03F)
  - User Action: None
  - Agent Work: Implement minimal FastAPI startup behavior.
  - Specific Steps:
    1. Create `backend/app/main.py`.
    2. Instantiate `FastAPI`.
    3. Call logging setup safely.
    4. Register startup or lifespan behavior that runs `init_db()`.
    5. Add only a minimal health/root endpoint if needed for bootstrap sanity.
    6. Do not add route modules, schemas, CORS, frontend integration, extraction, scoring, or Qdrant service code.
  - Output: Minimal FastAPI app entrypoint.
  - Acceptance: `uvicorn app.main:app --reload --port 8000` can import the app and trigger database initialization locally.
  - Validation: From `backend`, run `python -c "from app.main import app; print(app.title)"`.
  - Blocked Condition: None
  - Files: `backend/app/main.py`

- [ ] (04B): Run automated backend setup and import validations
  - Source of Truth: `docs/plans/Plan_1.md` > `## 9. Verification & Testing Plan`; `docs/plans/Master_Plan.md` > `## 31. Environment Setup`
  - Source Requirements:
    - Installing `backend/requirements-dev.txt` succeeds and provides pytest, pytest-asyncio, and respx.
    - Importing settings succeeds.
    - `init_db()` succeeds.
    - ORM table classes are importable.
    - Constants contract test passes.
  - Details: Execute the automated validation commands that prove the backend foundation imports and initializes.
  - Dependencies: (01B), (02A), (02C), (02D), (03F), (04A)
  - User Action: None, unless local Python environment creation is blocked by machine configuration.
  - Agent Work: Run Plan 1 automated checks and capture results for the task execution report.
  - Specific Steps:
    1. From `backend`, create or use a Python 3.11+ virtual environment.
    2. Install `requirements-dev.txt`.
    3. Run settings import check.
    4. Run `init_db()` check.
    5. Run ORM table name import check.
    6. Run `pytest tests/test_constants_contract.py`.
  - Output: Automated validation results.
  - Acceptance: All listed checks pass or blocked conditions are reported with exact safe reasons.
  - Validation: Use the commands under Plan 1 `## 9. Verification & Testing Plan`.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` if Python 3.11+ is unavailable or local environment setup is not permitted by the user environment.
  - Files: Execution report only; no new source files expected beyond prior tasks.

- [ ] (04C): Run SQLite schema, index, foreign key, and PRAGMA validations
  - Source of Truth: `docs/plans/Plan_1.md` > `## 9. Verification & Testing Plan`; `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### MVP Table Boundary`; `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Required Indexes`
  - Source Requirements:
    - Exactly three MVP application tables exist.
    - No `search_runs` table exists.
    - No `matching_text` column exists on `role_profiles`.
    - Required indexes exist.
    - Foreign keys are enabled on app-managed SQLAlchemy connections.
    - WAL mode is enabled.
    - Application foreign-key delete behavior is verified.
  - Details: Run schema-level checks against the initialized SQLite database.
  - Dependencies: (03F), (04B)
  - User Action: None
  - Agent Work: Execute the Plan 1 SQLite verification scripts and summarize results.
  - Specific Steps:
    1. Run the SQLite verification script from Plan 1 after `init_db()`.
    2. Confirm table set equals `applications`, `job_posts`, and `role_profiles`.
    3. Confirm `matching_text` is absent.
    4. Confirm all required indexes exist.
    5. Inspect `PRAGMA foreign_key_list(applications)`.
    6. Run app-session PRAGMA verification and confirm `foreign_keys 1` and `journal_mode wal`.
  - Output: SQLite validation results.
  - Acceptance: Schema/index/PRAGMA checks match Plan 1 expected outcomes.
  - Validation: Use the SQLite verification and PRAGMA scripts from Plan 1.
  - Blocked Condition: None
  - Files: Generated `backend/data/job_matching.db` during validation only; must remain ignored.

- [ ] (04D): Run repository ignore and Qdrant infrastructure validations
  - Source of Truth: `docs/plans/Plan_1.md` > `## 9. Verification & Testing Plan`; `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Repository Ignore Rules`; `docs/plans/Plan_1.md` > `## 7. Technical Specifications` > `### Qdrant Infrastructure`
  - Source Requirements:
    - `.env`, local SQLite files, virtual environments, frontend `node_modules`, and frontend build output are ignored by git.
    - Qdrant container can start locally on ports `6333` and `6334`.
    - `.env.example`, `backend/data/.gitkeep`, and `backend/app/db/migrations/.gitkeep` are not accidentally ignored.
  - Details: Verify local repository safety and Qdrant compose setup.
  - Dependencies: (01C), (01D)
  - User Action: Docker Desktop or Docker Engine must be installed and running before Qdrant validation.
  - Agent Work: Run git ignore checks and Docker Compose checks when available.
  - Specific Steps:
    1. Run required `git check-ignore` commands for ignored paths.
    2. Confirm required keep files are tracked or not ignored.
    3. Run `docker compose up -d qdrant`.
    4. Run `docker compose ps`.
    5. Run `docker compose down`.
    6. Report Docker availability issues as user-action blockers rather than implementation completion.
  - Output: Repository ignore and Qdrant validation results.
  - Acceptance: Ignore checks match expected output and Qdrant starts/stops locally when Docker is available.
  - Validation: Use commands under Plan 1 `## 9. Verification & Testing Plan`.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` if Docker is unavailable or not running.
  - Files: No new source files expected beyond prior tasks.

- [ ] (04E): Perform final Plan 1 scope audit and handoff notes
  - Source of Truth: `docs/plans/Plan_1.md` > `## 5. Out of Scope`; `docs/plans/Plan_1.md` > `## 10. Handoff Notes for Phase 2`; `docs/plans/Master_Plan.md` > `## 3. MVP Scope`
  - Source Requirements:
    - Confirm no extraction, scoring, frontend, or Qdrant service behavior was implemented.
    - Confirm Plan 2 consumes stable package structure, config, async session utilities, models, constants, dependencies, and ignore rules.
    - Later phases must not rename database columns, add `matching_text`, change status values without migration, duplicate executable constants, or create unapproved tables.
  - Details: Close Plan 1 by checking scope boundaries and recording clear handoff notes.
  - Dependencies: (04A), (04B), (04C), (04D)
  - User Action: None
  - Agent Work: Review changed files, validation outputs, and handoff contracts before marking tasks complete.
  - Specific Steps:
    1. Inspect the final changed-file list.
    2. Confirm only Plan 1 files were created or modified.
    3. Confirm no out-of-scope modules or services were added.
    4. Confirm all validation outputs are recorded in the execution report.
    5. Note any user-action blockers such as missing Docker or uncreated `.env`.
    6. Document handoff contracts for Plan 2.
  - Output: Final Plan 1 execution report and handoff notes.
  - Acceptance: Plan 1 is either fully validated or explicitly blocked only by user/environment setup.
  - Validation: Review git diff and task acceptance criteria.
  - Blocked Condition: None, unless unresolved earlier blocked conditions prevent final validation.
  - Files: Execution report path determined by the orchestration workflow; likely `docs/tasks/task_1_report.md` or equivalent if used by future agents.

### Files or Modules Likely Created or Updated

- `backend/app/main.py`
- Generated validation artifacts such as `backend/data/job_matching.db`, ignored by git
- Future execution report file if required by the execution workflow

### Required Outputs / Artifacts

- Minimal importable FastAPI app.
- Successful backend import/init/test validations.
- Successful SQLite schema/index/PRAGMA validations.
- Successful git ignore validations.
- Qdrant validation result or user-action blocker.
- Final scope audit and handoff notes.

### Acceptance Criteria

- `app.main:app` imports successfully.
- Database initialization occurs through the app bootstrap path.
- All automated checks pass when local prerequisites are present.
- Scope audit confirms no Plan 1 boundary violations.
- Any environment blockers are clearly marked as `BLOCKED_BY_USER_ACTION`.

### Required Tests or Validations

- `python -c "from app.main import app; print(app.title)"`
- `python -c "from app.core.config import settings; print(settings.DATABASE_URL)"`
- `python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"`
- `python -c "from app.db.models import RoleProfile, JobPost, Application; print(RoleProfile.__tablename__, JobPost.__tablename__, Application.__tablename__)"`
- `pytest tests/test_constants_contract.py`
- SQLite verification script from Plan 1.
- App-session PRAGMA verification script from Plan 1.
- Repository ignore verification commands from Plan 1.
- Qdrant infrastructure check commands from Plan 1.

### Explicit Non-Goals

- No public API route implementation.
- No CORS setup.
- No request/response schemas.
- No frontend integration.
- No extraction, scoring, LangGraph, Tavily, trafilatura workflow, or Qdrant service logic.
- No production SSRF handling.

## Optional Future Tracks

No optional future tracks are part of the mandatory Plan 1 execution chain.

The following work is explicitly outside Plan 1 and belongs to later approved plans only:

- LangGraph state, extraction schemas, prompts, nodes, and retry/fallback behavior.
- Tavily search, URL parsing, raw text parsing, and trafilatura parsing workflows.
- Scoring formulas, embedding text generation, Qdrant collection creation, vector upserts, payload indexes, query filters, and SQLite/Qdrant status sync.
- FastAPI route modules, API contracts, dashboard endpoints, and frontend integration.
- React frontend, demo seed script, mock data, score breakdown UI, and metrics panel.

## Dependency Chain

- Batch01 -> Batch02
- Batch02 -> Batch03
- Batch03 -> Batch04

## Global Verification Checklist

- [ ] Backend skeleton matches Plan 1 target structure.
- [ ] Dependency files match Plan 1 runtime and test requirements.
- [ ] Root `.env.example` uses only placeholder values and contains no real API keys.
- [ ] `.gitignore` protects local secrets, generated SQLite files, virtual environments, frontend dependencies, and frontend build output.
- [ ] Qdrant Docker Compose service starts and stops locally when Docker is available.
- [ ] Backend Dockerfile packages only FastAPI backend behavior.
- [ ] Backend settings load from the project root `.env`.
- [ ] Secrets are never logged, printed, committed, or exposed to frontend code.
- [ ] Shared constants expose exact Plan 1 status/source values.
- [ ] `pytest tests/test_constants_contract.py` passes.
- [ ] Database initializes with exactly `role_profiles`, `job_posts`, and `applications`.
- [ ] `role_profiles` does not contain `matching_text`.
- [ ] No `search_runs` or other out-of-scope table exists.
- [ ] Required SQLite indexes exist.
- [ ] SQLite foreign keys are enabled for app-managed connections.
- [ ] SQLite WAL mode is enabled.
- [ ] Application foreign-key delete behavior is inspected and reported.
- [ ] Minimal FastAPI app imports and can initialize the database.
- [ ] Implementation code is clean, idiomatic, typed where appropriate, and easy to understand.
- [ ] No Plan 1 non-goals were implemented.

## Progress Tracker

### Batches

- [x] Batch01 - Repository Foundation and Local Infrastructure
- [ ] Batch02 - Backend Configuration and Shared Contracts
- [ ] Batch03 - SQLite Models, Indexes, and Session
- [ ] Batch04 - App Bootstrap and Verification

### Task IDs

#### Batch01

- [x] (01A): Create backend package skeleton and placeholder files
- [x] (01B): Add backend runtime and test dependency files
- [x] (01C): Add root environment example and repository ignore rules
- [x] (01D): Add local Qdrant Docker Compose infrastructure
- [x] (01E): Add minimal backend Dockerfile

#### Batch02

- [ ] (02A): Implement root `.env` backend settings loader
- [ ] (02B): Implement basic backend logging setup
- [ ] (02C): Add shared status and source constants
- [ ] (02D): Add constants contract test

#### Batch03

- [ ] (03A): Add SQLAlchemy model base and storage conventions
- [ ] (03B): Define `role_profiles` model exactly
- [ ] (03C): Define `job_posts` model exactly
- [ ] (03D): Define `applications` model and delete behavior
- [ ] (03E): Add exact indexes and constraints
- [ ] (03F): Implement async session, database initialization, and SQLite PRAGMAs

#### Batch04

- [ ] (04A): Add minimal FastAPI application entrypoint
- [ ] (04B): Run automated backend setup and import validations
- [ ] (04C): Run SQLite schema, index, foreign key, and PRAGMA validations
- [ ] (04D): Run repository ignore and Qdrant infrastructure validations
- [ ] (04E): Perform final Plan 1 scope audit and handoff notes

## Completion Reporting Rules for Future Execution Agents

### BatchXX Execution Result

#### Completed Task IDs

- (XXA): complete / partial / blocked

#### Files Created or Modified

- path

#### Tests or Validations Run

- command: result

#### User Actions Required

- action: completed / pending / not required
- details: safe summary only, never include secrets

#### Blocked-by-User Status

- status: none / BLOCKED_BY_USER_ACTION
- reason: missing API key, missing provider project, missing manual setup, unavailable Docker, unavailable Python, or other safe summary

#### Validation Responsibility

- user-provided setup confirmed: yes / no / not required
- agent validation run after setup: yes / no
- validation command: result

#### Acceptance Criteria Check

- criterion: satisfied / not satisfied / blocked

#### Artifacts Produced

- artifact

#### Progress Tracker Update

- task IDs updated

#### Key Implementation Decisions

- decision

#### Risks or Open Issues

- issue

#### Notes for Next Batch

- handoff notes

Future execution agents must not claim completion unless task validations and acceptance criteria are satisfied.
