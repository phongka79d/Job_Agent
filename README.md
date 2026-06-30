# Agentic Job Matching System MVP

The **Agentic Job Matching System MVP** is a portfolio-ready system designed to help users find jobs matching a target role profile, extract structured details using agentic workflows, classify JD completeness, calculate a normalized match score, and track applications on a React dashboard.

---

## Architecture Overview

The system uses a durable SQL database (SQLite) as the primary source of truth, with a local Qdrant vector database acting as a derived similarity search index. 

```
                               +-----------------------------+
                               |     React Front-End UI      |
                               +--------------+--------------+
                                              | (FastAPI REST API)
                                              v
                               +-----------------------------+
                               |       FastAPI Backend       |
                               +-------+--------------+------+
                                       |              |
                (SQLAlchemy Async)     |              |  (Qdrant Client Async)
                                       v              v
                        +--------------+---+    +-----+-------------+
                        |  SQLite Database |    | Qdrant Vector DB  |
                        | (Durable State)  |    |  (Similarity)     |
                        +------------------+    +-------------------+
```

- **Durable Store:** SQLite (`backend/data/job_matching.db`) containing `role_profiles`, `job_posts`, and `applications` tables.
- **Vector Search:** Qdrant local container running via Docker Compose for similarity search scores.
- **Agentic Workflow:** LangChain and LangGraph executing state-based structured extraction and scoring.

---

## Directory Structure

The project layout including FastAPI app bootstrap, database models, indexes, services, and Phase 3 verification tests is established as follows:

```text
Job_Agent/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- routes_batches.py    # Batch summary metrics endpoint (Phase 4 Batch 02)
|   |   |   |-- routes_jobs.py       # Ingestion, review, dashboard, detail, and status endpoints (Phase 4 Batch 02/03)
|   |   |   |-- routes_role_profiles.py # Role profile create/list endpoints (Phase 4 Batch 02)
|   |   |   `-- schemas.py            # Phase 4 API request/response schemas and JSON Schema source
|   |   |-- agents/
|   |   |   |-- __init__.py
|   |   |   |-- graph.py              # Extraction graph wiring and conditional edges (Batch03)
|   |   |   |-- nodes.py              # Side-effect-free extraction graph nodes (Batch03)
|   |   |   |-- prompts.py            # Extraction and validation-repair prompts (Batch01)
|   |   |   `-- schemas.py            # Extraction state, output schema, and fallback helpers (Batch01)
|   |   |-- core/
|   |   |   |-- __init__.py
|   |   |   |-- config.py             # Root .env settings loader
|   |   |   |-- constants.py          # Shared status and source constants
|   |   |   `-- logging.py            # Basic backend logging configuration
|   |   |-- db/
|   |   |   |-- __init__.py
|   |   |   |-- migrations/
|   |   |   |   `-- .gitkeep
|   |   |   |-- models.py             # SQLite ORM models and indexes (Batch03)
|   |   |   `-- session.py            # Async database session and initialization (Batch03)
|   |   |-- main.py                   # FastAPI app bootstrap with API routers, local CORS, DB startup, and Qdrant startup initialization
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- cost_service.py       # Provider-neutral token, cost, and timing normalization (Batch01)
|   |   |   |-- dedup_service.py      # Null-safe duplicate checking and key generation (Phase 3 Batch 02)
|   |   |   |-- embedding_service.py  # Mockable OpenAI embedding provider boundary (Phase 3 Batch 01)
|   |   |   |-- demo_loader.py      # Demo fixture adapter and safe mock-data reset helper (Phase 4 Batch 04)
|   |   |   |-- extraction_service.py # Bounded raw-text/URL prep and graph entrypoints (Batch02/Batch03)
|   |   |   |-- job_processing_service.py # SQLite-first processing, Qdrant scoring, and status mutation service (Phase 3 Batch 03)
|   |   |   |-- llm_client.py         # Mockable OpenAI structured extraction client boundary (Batch03)
|   |   |   |-- qdrant_service.py     # Local Qdrant collection, payload, filters, and point operations (Phase 3 Batch 03)
|   |   |   |-- scoring_service.py    # Deterministic scoring and clean text builders (Phase 3 Batch 01)
|   |   |   `-- search_service.py     # Mockable Tavily public search boundary (Phase 4 Batch 03)
|   |-- data/
|   |   `-- .gitkeep
|   |-- scripts/
|   |   |-- export_api_contract.py   # Generates the frontend API contract from backend owners
|   |   `-- seed_demo.py             # Seeds local demo data through the backend processing pipeline
|   |-- tests/
|   |   |-- __init__.py
|   |   |-- conftest.py                    # Shared SQLite and fake provider fixtures (Phase 3 Batch 04)
|   |   |-- test_api_contract_export.py    # API contract freshness, CORS, and startup wiring tests (Phase 4 Batch 05)
|   |   |-- test_constants_contract.py        # Shared constants contract test
|   |   |-- test_dedup_service.py            # Focused deduplication policy tests (Phase 3 Batch 04)
|   |   |-- test_embedding_service.py        # Unit tests for embedding provider and dimensions (Phase 3 Batch 01)
|   |   |-- test_extraction_graph.py         # Integration tests for graph and entrypoints (Batch03)
|   |   |-- test_extraction_schema.py        # Focused extraction schema and fallback contract tests (Batch04)
|   |   |-- test_job_persistence.py          # SQLite-first persistence and dedup integration tests (Phase 3 Batch 04)
|   |   |-- test_job_processing_service.py   # Integration tests for persistence, Qdrant scoring, and status sync (Phase 3 Batch 03)
|   |   |-- test_llm_client.py               # Unit tests for mockable extraction client (Batch03)
|   |   |-- test_manual_text_preparation.py   # Manual raw-text parser preparation tests (Batch02)
|   |   |-- test_nodes.py                    # Unit tests for extraction graph nodes (Batch03)
|   |   |-- test_qdrant_service.py           # Mocked Qdrant collection/filter/query tests (Phase 3 Batch 04)
|   |   |-- test_routes_batches.py           # Batch summary route tests (Phase 4 Batch 05)
|   |   |-- test_routes_jobs.py              # Job route, ingestion, search, and status tests (Phase 4 Batch 05)
|   |   |-- test_routes_role_profiles.py     # Role profile route tests (Phase 4 Batch 05)
|   |   |-- test_scoring_service.py          # Unit tests for deterministic scoring and normalization (Phase 3 Batch 01)
|   |   |-- test_seed_demo.py                # Demo loader, seed, mock-load, and scope-boundary tests (Phase 4 Batch 05)
|   |   `-- test_url_cleaning.py             # Mocked URL extraction and fallback tests (Batch02)
|   |-- requirements.txt          # Backend runtime dependencies
|   |-- requirements-dev.txt      # Backend test dependencies
|   |-- .dockerignore             # Docker ignore configuration
|   `-- Dockerfile                # Backend-only Docker build configuration
|-- docker-compose.yml            # Local Qdrant container orchestration
|-- mock_data/
|   |-- demo_jobs.json              # Structured demo job fixtures
|   `-- messy_social_posts.json     # Non-scorable social post fixtures
|-- shared/
|   `-- api-contract.json          # Generated API contract for frontend consumers
|-- frontend/
|   `-- job-agent-ui/              # Vite React TypeScript frontend scaffold
|       |-- src/
|       |   |-- api/
|       |   |   `-- client.ts      # Typed FastAPI client with safe error surfacing
|       |   |-- components/
|       |   |   |-- AppShell.tsx   # Glassmorphic layout wrapper
|       |   |   |-- IngestionPanel.tsx # Search, URL, Text, and Mock controls
|       |   |   |-- JobCard.tsx        # Reusable job display card with match scores & warning alerts
|       |   |   |-- RoleProfilePanel.tsx # Role creation & selection form
|       |   |   |-- ScoreBreakdown.tsx # Null-safe detailed score component (no UI scoring)
|       |   |   `-- StatusSelect.tsx   # Contract-based status transition select dropdown
|       |   |-- pages/
|       |   |   |-- DashboardPage.tsx  # Tracked jobs dashboard (fetching status=tracked)
|       |   |   `-- ReviewPage.tsx     # Review queue with approve/reject mutations
|       |   |-- styles/
|       |   |   `-- app.css        # OLED Black & Cyan theme stylesheet
|       |   |-- test/
|       |   |   |-- setup.ts       # Vitest setup with jsdom
|       |   |   |-- activeBatch.test.tsx # Active batch isolation tests
|       |   |   |-- apiContract.test.ts # API contract drift tests
|       |   |   |-- apiClient.test.ts # API client tests
|       |   |   |-- DashboardPage.test.tsx # Dashboard routing and filtering tests
|       |   |   |-- IngestionPanel.test.tsx # Ingestion behavior tests
|       |   |   |-- JobCard.test.tsx # Job card display and interaction tests
|       |   |   |-- ReviewPage.test.tsx # Review queue approve/reject mutation tests
|       |   |   |-- RoleProfilePanel.test.tsx # Profile workflow tests
|       |   |   `-- StatusSelect.test.tsx # Allowed transitions unit tests
|       |   |-- types/
|       |   |   `-- api.ts         # TypeScript API models & transition types
|       |   |-- utils/
|       |   |   `-- activeBatchStorage.ts # Per-profile batch localStorage helper
|       |   |-- App.tsx
|       |   `-- main.tsx
|       `-- vite.config.ts
|-- .gitignore                    # Repository ignore rules (protecting secrets and local DB)
|-- .env.example                  # Environment configuration template
|-- README.md                     # Project overview and setup documentation
```

---

## Setup and Running Instructions

### 1. Environment Configuration
Create your local environment file by copying the template:
```bash
cp .env.example .env
```
Fill in the required keys (such as `OPENAI_API_KEY` and `TAVILY_API_KEY`) inside the `.env` file.
For official OpenAI, leave the optional OpenAI endpoint fields blank. For OpenAI-compatible providers, set `OPENAI_BASE_URL` as the shared endpoint, or use `OPENAI_LLM_BASE_URL` and `OPENAI_EMBEDDING_BASE_URL` when chat and embedding calls go to different endpoints.

### 2. Infrastructure Setup
Run the vector database locally using Docker Compose:
```bash
docker compose up -d qdrant
```

### 3. Backend Setup
1. Create and activate a Python 3.11+ virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   
   # Linux/macOS
   source .venv/bin/activate
   ```
2. Install the backend runtime and development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

### 4. Running Backend Verification
1. Verify that `pytest` is successfully installed in the virtual environment:
   ```bash
   pytest --version
   ```
2. Run the shared constants contract tests:
   ```bash
   pytest tests/test_constants_contract.py
   ```

### 5. Database Initialization
Verify that the database can be initialized and that SQLite connection PRAGMAs (foreign keys enabled and WAL mode) are active:
```bash
python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"
```

### 6. FastAPI App and Core API Routes
From the `backend` directory, verify that the FastAPI app imports and exposes the core Phase 4 API route surface:
```bash
python -c "from app.main import app; print(app.title)"
python -c "from app.main import app; print(sorted(app.openapi()['paths']))"
```

Run Qdrant before starting the live app because startup initializes the SQLite database and Qdrant collection/payload indexes:

```bash
docker compose up -d qdrant
uvicorn app.main:app --reload --port 8000
```

## Extraction Architecture & Workflows (Phase 2)

Phase 2 provides the complete mockable LangGraph structured extraction, validation retry, JD classification, and public service entrypoints:

- **State and Contracts (Batch01):** `JobAgentState` carries required identifiers, parsing/extraction status, and observability fields. `JobPostExtract` validates the structured job payload.
- **Input Preparation (Batch02):** Bounded raw-text cleaning, URL content downloading (using `httpx` and `trafilatura`), and low-content parser fallback (low content < 150 characters skips LLM with a manual paste warning).
- **LangGraph Orchestration & Services (Batch03):** 
  - Compiled state graph connecting `prepare_content` -> `extract_job` -> `repair_job`/`mark_unclear` -> `classify_jd`/`mark_unclear`.
  - Exactly one repair attempt for LLM validation or parsing errors.
  - Observability metrics (input/output tokens, cost, duration) are accumulated monotonically across extraction and repair steps.
  - Mockable async client protocol (`JobExtractionClientProtocol`) and dynamic client injection via `RunnableConfig` for isolated testing.
  - Three public async entrypoints in `extraction_service.py`: `run_extraction_graph`, `extract_from_raw_text`, and `extract_from_url` which return a complete state without database or vector index side-effects.

From the `backend` directory, smoke-check the app compile and run tests:

```bash
python -m compileall -q app
python -c "from app.agents.graph import graph; from app.services.extraction_service import run_extraction_graph; print('extraction graph and entrypoints import successfully')"
pytest
```

---

## API Schema and Contract Foundation (Phase 4 - Batch 01)

Phase 4 Batch 01 adds the backend-owned API schema layer and a generated frontend contract artifact without adding route handlers or new runtime endpoints yet:

- **API Schema Ownership:** `backend/app/api/schemas.py` defines Pydantic v2 request and response models for role profiles, ingestion requests/results, job rows, status mutations, job lists, and batch summaries.
- **Backend-Owned Contract Export:** `backend/scripts/export_api_contract.py` generates `shared/api-contract.json` from backend constants, `ALLOWED_STATUS_TRANSITIONS`, endpoint metadata, and Pydantic JSON Schema output.
- **Route Handoff:** Future FastAPI route modules should import these schemas instead of defining local response shapes or frontend-maintained status/source unions.

From the `backend` directory, regenerate and smoke-check the API contract:

```bash
python scripts/export_api_contract.py
python -c "from app.api.schemas import JobResponse, IngestionResponse; print('api schemas import successfully')"
```

---

## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)

Phase 4 Batch 02 exposes the core backend HTTP surface while keeping route handlers as thin adapters over existing database and service owners:

- **Role Profiles:** `POST /api/role-profiles` creates profiles and `GET /api/role-profiles` lists them newest-first.
- **Job Review and Dashboard:** `GET /api/jobs/review`, `GET /api/jobs`, and `GET /api/jobs/{id}` read persisted SQLite job rows, exclude duplicates, support `status=tracked`, and do not recompute scoring or deduplication decisions.
- **Status Mutations:** `POST /api/jobs/{id}/approve`, `POST /api/jobs/{id}/reject`, and `PATCH /api/jobs/{id}/status` delegate to the Phase 3 status service so SQLite, application rows, and Qdrant sync stay service-owned.
- **Batch Summary:** `GET /api/batches/{batch_id}/summary` aggregates stored `job_posts` metrics for parsed jobs, scorable jobs, failures, token totals, estimated cost, and extraction timing.
- **App Wiring:** `backend/app/main.py` registers the route modules under `/api`, enables local CORS only for `http://localhost:5173`, preserves database startup initialization, and delegates Qdrant collection/payload-index initialization to the existing Qdrant service.

From the `backend` directory, smoke-check the core route wiring:

```bash
python -m compileall -q app
python -c "from app.main import app; print(app.title)"
```

---

## Manual and Search Ingestion Routes (Phase 4 - Batch 03)

Phase 4 Batch 03 exposes the live ingestion routes for manual text, public URL parsing, and Tavily-backed public search while reusing the existing extraction and processing services:

- **Manual Text Parsing:** `POST /api/jobs/parse-text` creates one batch ID, runs the raw-text extraction entrypoint, processes the result through the SQLite-first job pipeline, and returns the standard ingestion response with persisted job rows and warnings.
- **Manual URL Parsing:** `POST /api/jobs/parse-url` accepts only `http` and `https` URLs, relies on the bounded URL extraction service for timeout, size, and low-content handling, and returns the same ingestion response shape.
- **Tavily Search Boundary:** `backend/app/services/search_service.py` wraps Tavily behind a mockable async client protocol, clamps requested results to `MAX_URLS_PER_BATCH`, reads `TAVILY_API_KEY` only from backend settings, and returns normalized public URL metadata.
- **Search Ingestion:** `POST /api/jobs/search` calls the Tavily service, processes each result URL through the parse-url extraction and Plan 3 processing path with `input_source="tavily"`, continues after individual URL failures, and returns one batch summary without adding queue or worker infrastructure.

From the `backend` directory, smoke-check the ingestion route surface:

```bash
python -m compileall -q app
python -c "from app.main import app; print([path for path in sorted(app.openapi()['paths']) if path.startswith('/api/jobs')])"
```

---

## Demo Loader, Fixtures, Seed Script, and Mock Load (Phase 4 - Batch 04)

Phase 4 Batch 04 adds local demo data support while keeping the same SQLite-first processing path used by live ingestion:

- **Shared Demo Loader:** `backend/app/services/demo_loader.py` validates local mock JSON, converts fixtures into complete `JobAgentState` values with `input_source="mock"` and `source_platform="mock"`, and owns safe reset behavior for mock-owned SQLite rows and matching Qdrant vectors.
- **Demo Fixtures:** `mock_data/demo_jobs.json` and `mock_data/messy_social_posts.json` provide 12 total demo inputs: 10 scorable structured jobs and 2 non-scorable social posts.
- **Seed Script:** `backend/scripts/seed_demo.py --reset` creates or reuses the deterministic `AI Engineer Intern` role profile, loads the fixtures through the shared adapter, and processes each state through the existing Plan 3 job processing service.
- **Mock Load API:** `POST /api/jobs/mock-load` accepts `MockLoadRequest`, optionally runs the same safe reset helper while preserving the requested role profile, loads both fixture files, and returns the standard `IngestionResponse`.

First-time demo seeding still requires local Qdrant and OpenAI embedding access for scorable jobs. After seed data exists, the demo relies on persisted SQLite rows and local Qdrant vectors rather than Tavily, LLM extraction, URL fetching, browser scraping, or manual paste.

From the `backend` directory, inspect the demo route and seed command:

```bash
python scripts/seed_demo.py --help
python -c "from app.main import app; print('/api/jobs/mock-load' in app.openapi()['paths'])"
```

Run a live reset seed only when local Qdrant is running and `OPENAI_API_KEY` is configured:

```bash
python scripts/seed_demo.py --reset
```

---

## Phase 4 Verification and Boundary Checks (Batch 05)

Phase 4 Batch 05 adds focused backend tests that protect the API contract, route behavior, ingestion flow, demo reset behavior, and phase boundary before the React phase consumes the API:

- `test_api_contract_export.py` fails when `shared/api-contract.json` is stale and verifies local CORS plus Qdrant startup delegation.
- `test_routes_role_profiles.py`, `test_routes_jobs.py`, and `test_routes_batches.py` cover role profile routes, review/dashboard/detail/status routes, ingestion/search routes, and batch summary aggregation with mocked external providers where needed.
- `test_seed_demo.py` validates actual demo fixtures, safe mock-data reset with application rows, mock-load role preservation, shared seed/mock-load adapter use, post-seed offline expectations, and absence of out-of-scope worker/browser infrastructure.

From the `backend` directory, run the focused Phase 4 verification target:

```bash
python -m pytest tests/test_api_contract_export.py tests/test_routes_role_profiles.py tests/test_routes_jobs.py tests/test_routes_batches.py tests/test_seed_demo.py
```

---

## Frontend Scaffold and API Contract Foundation (Phase 5 - Batch 01)

Phase 5 Batch 01 establishes the React + TypeScript frontend scaffold and the typed API contract layer:

- **Frontend Scaffold:** Built under `frontend/job-agent-ui` using Vite with React and TypeScript. Configured Vitest, jsdom, and testing library helpers for component and unit testing.
- **TypeScript API Types:** `frontend/job-agent-ui/src/types/api.ts` defines all types for jobs, role profiles, and ingestion responses, strictly mapping fields and nullable properties to the backend schemas.
- **Contract Drift Tests:** `frontend/job-agent-ui/src/test/apiContract.test.ts` validates that the frontend API types, constants, endpoints, and allowed status transitions match the backend-generated `shared/api-contract.json` contract.
- **FastAPI Client:** `frontend/job-agent-ui/src/api/client.ts` implements a typed Axios client for all 13 FastAPI endpoints, including custom API error class `ApiClientError` to normalize structured FastAPI validation error arrays.

From the `frontend/job-agent-ui` directory, verify and run the tests:

```bash
npm install
npm run typecheck
npm test -- --run
```

---

## App Shell, Role Profiles, Ingestion, and Active Batch State (Phase 5 - Batch 02)

Phase 5 Batch 02 implements the core application shell, role profile selection, ingestion forms, and profile-specific active batch isolation:

- **App Shell & Theme (Task 02A):** Creates `src/components/AppShell.tsx` and custom stylesheet `src/styles/app.css` with OLED Black, Glassmorphism, and Cyan highlights matching the Dark Elite Frosted design system. Configures client-side routing via React Router DOM for Review Queue and Tracked Jobs Dashboard.
- **Role Profile UI (Task 02B):** Builds `src/components/RoleProfilePanel.tsx` supporting role profile creation (role title, level, location, remote option, skills comma-separated, and resume text) and switching, connecting directly to FastAPI.
- **Ingestion Controls & Warnings (Task 02C):** Implements `src/components/IngestionPanel.tsx` containing search, URL, text, and mock-load ingestion controls. Features inline API disabled states, warning displays (such as low-content manual input prompts), and validation error surfacing.
- **Active Batch Isolation (Task 02D):** Implements `src/utils/activeBatchStorage.ts` to isolate active batch IDs per profile in localStorage using the key prefix `job-agent.activeBatchId.{role_profile_id}`. Prevents cross-profile batch leaks and avoids non-contract backend queries.
- **Verification and Testing:** Includes automated Vitest unit/component tests (`RoleProfilePanel.test.tsx`, `IngestionPanel.test.tsx`, and `activeBatch.test.tsx`) asserting mock client triggers, disabled states, contract compliance, and localStorage separation.

From the `frontend/job-agent-ui` directory, verify and run the tests:

```bash
npm run typecheck
npm test -- --run
npm run build
```

---

## Review Queue, Tracked Dashboard, Score Breakdown, and Status Workflows (Phase 5 - Batch 03)

Phase 5 Batch 03 implements the core human-in-the-loop review and application tracking UI:

- **Review Queue (Task 03B):** Implements `src/pages/ReviewPage.tsx` fetching pending jobs matching `status=pending_review` via the FastAPI review route. Displays card-based approve and reject mutation actions.
- **Tracked Jobs Dashboard (Task 03C):** Implements `src/pages/DashboardPage.tsx` using `status=tracked` query filtering to display saved, applied, interview, rejected, and offer jobs. Retains jobs in score order and prevents premature frontend status filtering.
- **Job Cards & Null-Safe Scores (Task 03A):** Implements `src/components/JobCard.tsx` and `src/components/ScoreBreakdown.tsx` to render title, company, location, source platform, and detailed score breakdown (similarity, skill overlap, location, level, and confidence). Integrates persisted job `error_reason` warnings. Renders non-scorable or unscored jobs safely as `Not scored` without recalculating scores in the browser.
- **Status Workflows & Allowed Transitions (Task 03D):** Implements `src/components/StatusSelect.tsx` to control manual status updates. Disables option changes in terminal states (`rejected`, `offer`) and limits choices to contract-approved transitions dynamically fetched from `shared/api-contract.json`.
- **Verification and Testing:** Includes Vitest component unit tests checking card styling, conditional button disables, contract transition validations, status-revert helpers, and loading/empty UI states.

From the `frontend/job-agent-ui` directory, verify and run the tests:

```bash
npm run typecheck
npm test -- --run
npm run build
```

---

## Scoring & Embedding Foundations (Phase 3 - Batch 01)

Phase 3 Batch 01 implements the deterministic scoring calculations, skill alias normalization, clean embedding text construction, and mockable embedding provider boundary:

- **Deterministic Scoring (Batch 01 - Task 01B):** Exposes pure mathematical formulas for calculating location match scores, adjacent level match scores, skill overlap percentages, and final weighted job match scores (with a JD confidence multiplier). Normalizes user and JD skills using pre-defined skill aliases before computing overlap.
- **Embedding Provider Boundary (Batch 01 - Task 01C):** Integrates with `langchain_openai.OpenAIEmbeddings` using backend settings, features validation of vector dimensions against configurations, implements fast-fail checking on blank inputs, and enforces lazy initialization of the client API connection.
- **Verification and Testing:** Includes unit tests `test_scoring_service.py` and `test_embedding_service.py` to validate scoring logic, skill normalization, and embedding client behavior under simulated network/API failures.

Smoke-check the new service implementations and run tests:

```bash
python -m compileall -q app
python -c "from app.services.scoring_service import calculate_final_scores; from app.services.embedding_service import embed_text; print('scoring and embedding services import successfully')"
pytest tests/test_scoring_service.py tests/test_embedding_service.py
```

---

## Deduplication & SQLite-First Persistence (Phase 3 - Batch 02)

Phase 3 Batch 02 implements the null-safe duplicate key checking and SQLite database persistence boundary before any embedding or vector database operations occur:

- **Null-Safe Deduplication Service (Batch 02 - Task 02A):** Normalizes company names and job titles (whitespace trimming, lowercase) and constructs a deterministic SHA-256 hex digest duplicate key only if both fields are non-blank. Maps existing duplicate job statuses to the duplicate policy using `TRACKED_JOB_STATUSES` from shared constants.
- **State to Persistence Mapping (Batch 02 - Task 02B):** Maps LangGraph extraction state and loaded role profiles to the `JobPost` database ORM payload. Enforces JSON serialization of skill arrays, maps input sources, derives similarity scoring eligibility based on JD status, and prepares clean initial records with null scoring fields and `pending_review` status.
- **SQLite-First Orchestration (Batch 02 - Task 02C):** Integrates the mapping, exact duplicate check (via raw content hash), and duplicate key policy into the `process_job_state` pipeline entrypoint. Safeguards operations using database transaction commits and rollbacks on constraint collisions (`IntegrityError`), ensuring duplicate records bypass Qdrant/embedding logic.
- **Verification and Testing:** Includes integration tests `test_job_processing_service.py` to cover all deduplication paths: new inserts, exact duplicates, key duplicates (skips vs ignored metadata insertions), and hash collisions.

Smoke-check the new service implementations and run tests:

```bash
python -m compileall -q app
python -c "from app.services.dedup_service import build_dedup_key; from app.services.job_processing_service import process_job_state; print('deduplication and persistence services import successfully')"
pytest tests/test_job_processing_service.py
```

---

## Qdrant Sync & Status Mutation Services (Phase 3 - Batch 03)

Phase 3 Batch 03 completes the SQLite-first job processing pipeline with Qdrant-derived scoring and backend-owned status mutation behavior:

- **Qdrant Derived Index Service (Batch 03 - Task 03A):** Adds `qdrant_service.py` to own local Qdrant collection initialization, approved payload indexes, role/status/job-specific filters, canonical UUID point IDs, scorable job upserts with write acknowledgement, current-job similarity queries with bounded retry, idempotent point deletion, and payload status updates.
- **Scorable Job Integration (Batch 03 - Task 03B):** Extends `process_job_state` so scorable jobs commit to SQLite before embedding or Qdrant calls, then use the Qdrant cosine score as `embedding_similarity` before updating deterministic score fields. Embedding or Qdrant failures keep the committed `pending_review` row visible with null score fields and a safe error reason.
- **Status and Application Sync (Batch 03 - Task 03C):** Adds importable `ALLOWED_STATUS_TRANSITIONS`, `InvalidStatusTransition`, `approve_job`, `reject_job`, and `update_job_status`. These service methods validate transitions before mutation, commit SQLite first, create or update exactly one `applications` row for tracked statuses, update Qdrant payloads for saved/applied/interview/rejected/offer, and delete Qdrant points only for review rejection to `ignored`.
- **Verification and Testing:** The existing `test_job_processing_service.py` now includes narrow mocked coverage for SQLite-before-embedding ordering, Qdrant score update behavior, current-job similarity misses, approve/reject sync, invalid transition pre-mutation behavior, and application-row semantics.

Smoke-check the service implementations and run tests:

```bash
python -m compileall -q app
python -c "from app.services.qdrant_service import QdrantService; from app.services.job_processing_service import ALLOWED_STATUS_TRANSITIONS, approve_job, reject_job, update_job_status; print('qdrant and status services import successfully')"
pytest tests/test_job_processing_service.py
```

---

## Phase 3 Verification & Handoff Boundary (Batch 04)

Phase 3 Batch 04 adds focused automated verification around the completed scoring, embedding, deduplication, SQLite persistence, Qdrant synchronization, and status mutation services. The tests use SQLite-backed fixtures plus fake or mocked provider/Qdrant boundaries, so the automated suite does not require live OpenAI credentials or a running Qdrant container.

- **Scoring and Embedding Verification (Task 04A):** Extends scoring and embedding tests for non-scorable JD status behavior, Qdrant score clamping, embedding dimension mismatch, and provider failure sanitization.
- **Deduplication and Persistence Verification (Task 04B):** Adds focused dedup policy tests and SQLite-first integration coverage for exact duplicates, dedup-key duplicates, null dedup keys, duplicate metadata rows, provider-call exclusion, commit ordering, and warning propagation.
- **Qdrant and Status Sync Verification (Task 04C):** Adds mocked Qdrant service tests for collection setup, payload indexes, canonical UUID point IDs, filters, write acknowledgement, current-job scoring, bounded retry behavior, and status payload/delete synchronization.
- **Phase Boundary Verification (Task 04D):** Confirms the focused Plan 3 tests, full backend test suite, compile/import smoke checks, and Phase 4 handoff service symbols pass without adding route handlers, Tavily orchestration, seed demo data, mock JSON, React UI, or schema/model/index changes.

From the `backend` directory, run the completed Phase 3 verification suite:

```bash
python -m compileall -q app
python -c "from app.services.qdrant_service import QdrantService; from app.services.job_processing_service import ALLOWED_STATUS_TRANSITIONS, JobProcessingResult, approve_job, reject_job, update_job_status, process_job_state; print('phase 4 handoff symbols ok')"
pytest tests/test_scoring_service.py tests/test_embedding_service.py tests/test_dedup_service.py tests/test_job_processing_service.py tests/test_job_persistence.py tests/test_qdrant_service.py
pytest
```
