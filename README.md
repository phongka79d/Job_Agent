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

The project layout including Batch03 database models, indexes, and session configuration is established as follows:

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
|   |   |   |-- config.py             # Root .env settings loader
|   |   |   |-- constants.py          # Shared status and source constants
|   |   |   `-- logging.py            # Basic backend logging configuration
|   |   |-- db/
|   |   |   |-- __init__.py
|   |   |   |-- migrations/
|   |   |   |   `-- .gitkeep
|   |   |   |-- models.py             # SQLite ORM models and indexes (Batch03)
|   |   |   `-- session.py            # Async database session and initialization (Batch03)
|   |   |-- services/
|   |   |   `-- __init__.py
|   |-- data/
|   |   `-- .gitkeep
|   |-- tests/
|   |   |-- __init__.py
|   |   `-- test_constants_contract.py # Shared constants contract test
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
