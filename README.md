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

The project layout including Batch04 app bootstrap, database models, indexes, and session configuration is established as follows:

```text
Job_Agent/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   `-- __init__.py
|   |   |-- agents/
|   |   |   |-- __init__.py
|   |   |   |-- prompts.py            # Extraction and validation-repair prompts
|   |   |   `-- schemas.py            # Extraction state, output schema, and fallback helpers
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
|   |   |-- main.py                   # Minimal FastAPI app bootstrap with DB startup initialization
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- cost_service.py       # Provider-neutral token, cost, and timing normalization
|   |   |   `-- extraction_service.py # Bounded raw-text and URL parser preparation
|   |-- data/
|   |   `-- .gitkeep
|   |-- tests/
|   |   |-- __init__.py
|   |   |-- test_constants_contract.py        # Shared constants contract test
|   |   |-- test_manual_text_preparation.py   # Manual raw-text parser preparation tests
|   |   `-- test_url_cleaning.py             # Mocked URL extraction and fallback tests
|   |-- requirements.txt          # Backend runtime dependencies
|   |-- requirements-dev.txt      # Backend test dependencies
|   |-- .dockerignore             # Docker ignore configuration
|   `-- Dockerfile                # Backend-only Docker build configuration
|-- docker-compose.yml            # Local Qdrant container orchestration
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

### 6. FastAPI App Bootstrap
From the `backend` directory, verify that the minimal FastAPI app imports and can run local startup database initialization:
```bash
python -c "from app.main import app; print(app.title)"
uvicorn app.main:app --reload --port 8000
```

## Extraction Contracts

Phase 2 Batch01 and Batch02 provide the shared extraction foundation and
parser-only input preparation without performing persistence, scoring, vector
operations, LangGraph orchestration, or LLM calls:

- `JobAgentState` carries required identifiers, parsing and extraction status,
  score placeholders, warnings, errors, and observability fields.
- `JobPostExtract` validates the structured job payload and shared source/JD
  status values.
- Source mapping and fallback helpers preserve `batch_id`, `role_profile_id`,
  and `input_source`, and produce complete `unclear` records when extraction
  fails after parsing.
- Provider-neutral extraction and repair prompts require grounded output and
  apply the five approved JD classifications.
- Usage helpers normalize optional token metadata, calculate cost only from
  explicit pricing, and measure attempted extraction with a monotonic clock.
- Manual raw text is bounded by `MAX_RAW_TEXT_CHARS`, cleaned while preserving
  meaningful line structure, truncated to `MAX_CLEAN_TEXT_CHARS`, and hashed
  from final clean content.
- Public URL preparation accepts only `http` and `https`, uses configured
  timeout and response-size limits, extracts readable content with
  `trafilatura`, and applies the same clean/truncate/hash pipeline.
- Low-content, login-gated, JavaScript-only, blocked, or cookie-gated URL
  content returns a terminal parser fallback with
  `parse_status = "needs_manual_input"`, `jd_status = "unclear"`,
  `extraction_status = None`, score placeholders set to `None`, and the stable
  manual paste warning.

From the `backend` directory, smoke-check these modules with:

```bash
python -m compileall -q app/agents app/services
python -c "from app.agents.schemas import JobAgentState, JobPostExtract; from app.agents.prompts import build_extraction_prompt; from app.services.cost_service import normalize_usage; print('extraction contracts import successfully')"
pytest tests/test_manual_text_preparation.py tests/test_url_cleaning.py
```
