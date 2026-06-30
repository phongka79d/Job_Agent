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
|   |   |   |-- routes_jobs.py       # Review, dashboard, detail, and status endpoints (Phase 4 Batch 02)
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
|   |   |   |-- extraction_service.py # Bounded raw-text/URL prep and graph entrypoints (Batch02/Batch03)
|   |   |   |-- job_processing_service.py # SQLite-first processing, Qdrant scoring, and status mutation service (Phase 3 Batch 03)
|   |   |   |-- llm_client.py         # Mockable OpenAI structured extraction client boundary (Batch03)
|   |   |   |-- qdrant_service.py     # Local Qdrant collection, payload, filters, and point operations (Phase 3 Batch 03)
|   |   |   `-- scoring_service.py    # Deterministic scoring and clean text builders (Phase 3 Batch 01)
|   |-- data/
|   |   `-- .gitkeep
|   |-- scripts/
|   |   `-- export_api_contract.py   # Generates the frontend API contract from backend owners
|   |-- tests/
|   |   |-- __init__.py
|   |   |-- conftest.py                    # Shared SQLite and fake provider fixtures (Phase 3 Batch 04)
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
|   |   |-- test_scoring_service.py          # Unit tests for deterministic scoring and normalization (Phase 3 Batch 01)
|   |   `-- test_url_cleaning.py             # Mocked URL extraction and fallback tests (Batch02)
|   |-- requirements.txt          # Backend runtime dependencies
|   |-- requirements-dev.txt      # Backend test dependencies
|   |-- .dockerignore             # Docker ignore configuration
|   `-- Dockerfile                # Backend-only Docker build configuration
|-- docker-compose.yml            # Local Qdrant container orchestration
|-- shared/
|   `-- api-contract.json          # Generated API contract for frontend consumers
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
