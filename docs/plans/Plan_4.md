# Phase 4 Plan: Integration & UI

## 1. Objective

Connect the completed Phase 1 foundation, Phase 2 extraction services, Phase 3 scoring/storage/Qdrant services, demo seed data, FastAPI route layer, and React frontend into a demo-ready Agentic Job Matching System MVP.

Phase 4 must produce a working local portfolio demo where a user can seed jobs, create role profiles, parse URL/text inputs, review pending jobs, approve/reject jobs, update application status, view ranked saved jobs, inspect score breakdowns, and see token/cost metrics.

Phase 4 integrates and exposes existing services. It must not change core architecture decisions from Phase 1, Phase 2, or Phase 3.

## 2. Source of Truth

Use `docs/plans/Master_Plan.md` as the architecture source of truth.

`Master_Plan.md` is the only source of truth. If this Phase 4 plan conflicts with `Master_Plan.md`, follow `Master_Plan.md`.

Master plan sections most relevant to Phase 4:

- Section 6: Demo Mode / Mock Seeding
- Section 7: Input Sources
- Section 8: JavaScript pages and cookie banners
- Section 15: Visual Score Breakdown in UI
- Section 16: Cost & Performance Metrics Panel
- Section 20: Human-in-the-Loop Rules
- Section 25: SQLite dashboard and review queue queries
- Section 26: SQLite to Qdrant status sync rules
- Section 27: API endpoints
- Sections 31-36: project layout, environment, Docker, demo script, final checklist

## 3. Prerequisites from Phase 1, Phase 2, and Phase 3

Assume Phase 1 provides:

- SQLite database setup through SQLAlchemy async sessions.
- Root `.env` loading.
- Core database tables, indexes, UUID rules, and status fields.
- Qdrant Local Docker Compose configuration.

Assume Phase 2 provides:

- URL and raw text extraction.
- `JobPostExtract`.
- `JobAgentState`.
- LangGraph extraction flow.
- Pydantic structured output and retry behavior.
- `mark_unclear` fallback state.

Assume Phase 3 provides:

- Scoring service.
- Storage service.
- Deduplication service.
- Qdrant vector operations.
- SQLite/Qdrant status sync service functions.
- Batch counters and stored token/cost fields.

Phase 4 may call or minimally adapt existing Phase 2/3 services through orchestration only. It must not rewrite extraction, scoring, deduplication, or Qdrant sync logic.

## 4. Phase 4 Scope

Phase 4 owns only:

- `backend/scripts/seed_demo.py`
- mock demo job data
- FastAPI route layer
- backend orchestration that calls existing Phase 2/3 services
- Tavily/public search API integration
- React + TypeScript + Vite UI
- dashboard page
- review queue page
- role profile page
- demo mode page
- score breakdown UI
- token/cost metrics UI
- manual URL input flow
- manual raw text input flow
- end-to-end live demo readiness

Preferred Phase 4 service ownership:

```text
backend/app/services/job_pipeline_service.py
```

This service orchestrates:

```text
Phase 2 extraction service
-> Phase 3 scoring/storage/sync services
-> API response DTO
```

## 5. Out of Scope

Phase 4 must not own or introduce:

- rewriting extraction architecture from Phase 2
- changing the Pydantic extraction schema from Phase 2
- changing extraction prompt architecture from Phase 2
- rewriting scoring formula from Phase 3
- changing the JD confidence multiplier from Phase 3
- changing deduplication policy from Phase 3
- changing Qdrant sync policy from Phase 3
- changing Qdrant point ID rules from Phase 3
- changing Qdrant reject/delete behavior from Phase 3
- changing database schema from Phase 1
- adding a second `.env`
- authentication
- auto-apply
- cover letter generation
- GraphRAG
- Neo4j
- Jina Reranker
- Celery/Redis
- authenticated LinkedIn/Facebook crawling
- frontend access to API keys or secrets

## 6. Target Directory Structure

Create or update Phase 4-owned files:

```text
backend/scripts/seed_demo.py
mock_data/demo_jobs.json
mock_data/messy_social_posts.json

backend/app/api/deps.py
backend/app/api/routes_role_profiles.py
backend/app/api/routes_jobs.py
backend/app/api/routes_batches.py
backend/app/main.py

backend/app/services/job_pipeline_service.py

backend/tests/test_api_role_profiles.py
backend/tests/test_api_jobs.py
backend/tests/test_api_batches.py
backend/tests/test_job_pipeline_service.py

frontend/job-agent-ui/src/main.tsx
frontend/job-agent-ui/src/App.tsx
frontend/job-agent-ui/src/config.ts
frontend/job-agent-ui/src/api/client.ts
frontend/job-agent-ui/src/api/jobs.ts
frontend/job-agent-ui/src/api/roleProfiles.ts
frontend/job-agent-ui/src/types/job.ts
frontend/job-agent-ui/src/types/roleProfile.ts

frontend/job-agent-ui/src/pages/DashboardPage.tsx
frontend/job-agent-ui/src/pages/ReviewQueuePage.tsx
frontend/job-agent-ui/src/pages/RoleProfilesPage.tsx
frontend/job-agent-ui/src/pages/DemoModePage.tsx

frontend/job-agent-ui/src/components/JobCard.tsx
frontend/job-agent-ui/src/components/ScoreBreakdown.tsx
frontend/job-agent-ui/src/components/MetricsPanel.tsx
frontend/job-agent-ui/src/components/ManualTextForm.tsx
frontend/job-agent-ui/src/components/ManualUrlForm.tsx
frontend/job-agent-ui/src/components/StatusSelect.tsx
frontend/job-agent-ui/src/components/LoadingState.tsx
frontend/job-agent-ui/src/components/ErrorAlert.tsx

frontend/job-agent-ui/src/__tests__/DashboardPage.test.tsx
frontend/job-agent-ui/src/__tests__/ReviewQueuePage.test.tsx
frontend/job-agent-ui/src/__tests__/ManualUrlForm.test.tsx
frontend/job-agent-ui/src/__tests__/ManualTextForm.test.tsx
frontend/job-agent-ui/src/__tests__/MetricsPanel.test.tsx
frontend/job-agent-ui/src/__tests__/ScoreBreakdown.test.tsx
```

Reuse existing Phase 2/3 services as dependencies, not Phase 4 core implementation targets:

```text
backend/app/services/extraction_service.py
backend/app/services/scoring_service.py
backend/app/services/qdrant_service.py
backend/app/services/job_storage_service.py
```

Phase 4 may only make minimal adapter fixes to those files if an existing public function cannot be called from the route/pipeline layer. It must not rewrite extraction, scoring, deduplication, or Qdrant sync behavior.

Do not create:

```text
frontend/job-agent-ui/.env.example
```

If the Vite app is missing, create it with:

```powershell
npm create vite@latest frontend/job-agent-ui -- --template react-ts
cd frontend/job-agent-ui
npm install
npm install axios react-router-dom lucide-react
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

## 7. Environment and Frontend Config Rules

The project uses a single root `.env` file as the only environment configuration source. Phase 4 must not introduce a second secret/config source inside the frontend directory.

No API keys or secrets are exposed to the frontend.

Frontend API base URL should default to `http://localhost:8000` in the frontend API client or be generated from the root `.env` as safe public config. Do not create a separate frontend `.env`, `frontend/.env.example`, or `frontend/job-agent-ui/.env.example` in Phase 4.

If a config file is needed, use a non-secret TypeScript config file:

```text
frontend/job-agent-ui/src/config.ts
```

Example:

```ts
export const API_BASE_URL = "http://localhost:8000";
```

Only safe public values may be generated into the frontend config. Never expose `OPENAI_API_KEY`, `TAVILY_API_KEY`, `QDRANT_API_KEY`, `DATABASE_URL`, `SQLITE_DB_PATH`, or database settings. Do not require Vite environment variables for the MVP.

## 8. Demo Data Plan

Create at least 12 jobs across two files.

`mock_data/demo_jobs.json` contains 10 structured jobs:

- 5 perfect matches:
  - AI Engineer Intern - RAG + LangChain + FastAPI + Qdrant
  - LLM Application Intern - OpenAI API + Vector DB
  - GenAI Backend Intern - FastAPI + SQLite + Qdrant
  - RAG Engineer Intern - Python + LangGraph
  - AI Platform Intern - Python + LangChain + Docker
- 3 partial matches:
  - Backend Intern - FastAPI + SQLite
  - Python Automation Intern - API integration
  - Data Engineering Intern - Python + SQL
- 2 unrelated jobs:
  - Data Analyst Intern - Excel + BI
  - Frontend Designer Intern - Figma + CSS

`mock_data/messy_social_posts.json` contains 2 messy posts:

- `Tuyen AI Intern, ib nhan JD`
- `Hiring LLM intern, comment for JD, remote possible`

Each job record should include title, company, location, work mode, level, employment type, responsibilities, requirements, skills, source platform, JD status, and demo category.

Seeded demo jobs must start as `pending_review`, not `saved`.

Do not seed demo jobs directly as `saved` just to make the dashboard non-empty. Jobs should start as `pending_review` to preserve the human-in-the-loop rule.

## 9. Seed Demo Script Plan

Create `backend/scripts/seed_demo.py`.

Shared loader requirement:

```text
Implement one shared demo loading function that both `seed_demo.py` and `/api/jobs/mock-load` call.
Do not create separate seed logic for the script and API route.
```

Command:

```powershell
cd backend
python scripts/seed_demo.py --reset
```

Behavior:

- Load the single root `.env`.
- If `--reset` is passed, clear demo role profiles/jobs and delete demo vectors from Qdrant.
- Create demo role profile:
  - `target_role = "AI Engineer Intern"`
  - `location = "Hanoi"`
  - `level = "intern"`
  - `skills = ["python", "rag", "langchain", "fastapi", "qdrant"]`
  - `accept_remote = true`
- Load `../mock_data/demo_jobs.json` and `../mock_data/messy_social_posts.json`.
- Reuse Phase 3 scoring/storage/sync services to insert jobs.
- Insert all demo jobs as `status = "pending_review"`.
- Upsert Qdrant vectors only for scorable jobs.
- Print a deterministic seed summary.

Expected output:

```text
Seed completed.
Role profile: AI Engineer Intern
Inserted jobs: 12
Scorable jobs: 8
Need-review/social jobs: 2
Unrelated jobs: 2
Qdrant vectors upserted: 8
```

Deterministic mock vector constraints:

- Deterministic mock vectors are allowed only inside `seed_demo.py` or demo-only test utilities.
- They must match `EMBEDDING_DIMENSION`.
- They must never be used in normal URL/text/search flows.
- Use the same real embedding service and Phase 3 scoring/storage flow by default.
- If demo mode needs deterministic offline behavior, isolate mock vectors behind an explicit demo-only flag or seed script path such as `--offline-demo-vectors`.
- Tests must prove deterministic mock vectors cannot be used by normal URL, text, or Tavily search flows.

## 10. FastAPI Integration Plan

Create `backend/app/api/deps.py`:

- `get_db_session`
- shared config dependency
- role/job ID validation helpers if useful

Update `backend/app/main.py`:

- create `FastAPI(title="Agentic Job Matching System MVP")`
- add CORS for `http://localhost:5173`
- include role profile, job, and batch routers under `/api`
- add `/health` returning backend, database, and Qdrant readiness where practical

Create `backend/app/services/job_pipeline_service.py`.

Required functions:

```python
async def parse_url_job(role_profile_id: str, url: str) -> JobPipelineResponse: ...
async def parse_text_job(role_profile_id: str, raw_text: str) -> JobPipelineResponse: ...
async def search_jobs(role_profile_id: str, query: str) -> BatchSummaryResponse: ...
async def load_mock_jobs(reset: bool) -> BatchSummaryResponse: ...
```

Rules:

- Route handlers stay thin and call `job_pipeline_service.py`.
- `job_pipeline_service.py` calls Phase 2 extraction services.
- `job_pipeline_service.py` calls Phase 3 public service or graph contracts for scoring, storage, dedup, and Qdrant sync.
- `job_pipeline_service.py` must not duplicate Phase 3 internals, scoring formulas, deduplication decisions, SQLite persistence rules, or Qdrant synchronization policy.
- One failed job returns a controlled warning/error payload and does not fail the whole batch.
- API responses must make warnings and partial failures visible to the frontend without crashing the user flow.

## 11. API Endpoint Plan

| Method | Endpoint | Behavior |
|---|---|---|
| `POST` | `/api/role-profiles` | Create role profile |
| `GET` | `/api/role-profiles` | List role profiles |
| `POST` | `/api/jobs/search` | Run Tavily/public search up to `MAX_URLS_PER_BATCH`; process results through pipeline |
| `POST` | `/api/jobs/parse-url` | Parse one public URL |
| `POST` | `/api/jobs/parse-text` | Parse one raw text input |
| `POST` | `/api/jobs/mock-load` | Load mock data using the demo loader |
| `GET` | `/api/jobs/review` | Return pending-review jobs |
| `POST` | `/api/jobs/{id}/approve` | Set status `saved`, update Qdrant payload |
| `POST` | `/api/jobs/{id}/reject` | Set status `ignored`, delete Qdrant vector |
| `PATCH` | `/api/jobs/{id}/status` | Manual status update |
| `GET` | `/api/jobs` | Return saved dashboard jobs |
| `GET` | `/api/jobs/{id}` | Return job detail |
| `GET` | `/api/batches/{batch_id}/summary` | Aggregate stored job metrics |

Query rules:

- Review queue: `status = 'pending_review' AND duplicate_of_job_id IS NULL`, sorted by `final_score IS NULL, final_score DESC, discovered_at DESC`.
- Dashboard: `status = 'saved' AND duplicate_of_job_id IS NULL`, sorted by `final_score IS NULL, final_score DESC`.
- Manual status values: `saved`, `applied`, `interview`, `rejected`, `offer`, `ignored`.
- API keys never appear in responses.
- SQLite remains the source of truth for job status.

## 12. API Request and Response Schemas

Define explicit DTOs for route inputs and frontend-safe outputs.

```python
from pydantic import BaseModel


class ParseUrlRequest(BaseModel):
    role_profile_id: str
    url: str


class ParseTextRequest(BaseModel):
    role_profile_id: str
    raw_text: str


class SearchJobsRequest(BaseModel):
    role_profile_id: str
    query: str


class SearchResultItem(BaseModel):
    title: str | None = None
    url: str
    source_platform: str = "tavily"
    snippet: str | None = None


class RoleProfileResponse(BaseModel):
    id: str
    target_role: str
    level: str | None = None
    location: str | None = None
    accept_remote: bool
    skills: list[str]
    resume_text: str | None = None
    created_at: str
    updated_at: str


class ScoreBreakdownResponse(BaseModel):
    embedding_similarity: float | None = None
    skill_overlap_score: float | None = None
    location_match_score: float | None = None
    level_match_score: float | None = None
    jd_confidence_multiplier: float | None = None
    base_score: float | None = None
    final_score: float | None = None
    final_score_percent: float | None = None


class JobListItemResponse(BaseModel):
    id: str
    batch_id: str
    role_profile_id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    work_mode: str
    level: str
    employment_type: str
    source_url: str | None = None
    source_platform: str | None = None
    parse_status: str
    jd_status: str
    extraction_status: str
    should_score_similarity: bool
    status: str
    duplicate_of_job_id: str | None = None
    discovered_at: str
    score_breakdown: ScoreBreakdownResponse
    warning: str | None = None
    sync_warning: str | None = None


class JobDetailResponse(JobListItemResponse):
    salary: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    skills: list[str]
    error_reason: str | None = None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    extraction_time_ms: int | None = None


class JobPipelineResponse(BaseModel):
    job_id: str | None
    batch_id: str
    status: str
    jd_status: str | None
    parse_status: str | None
    final_score_percent: float | None
    warning: str | None = None
    duplicate_of_job_id: str | None = None
    sync_warning: str | None = None
    error_reason: str | None = None


class DuplicateResultResponse(BaseModel):
    job_id: str | None
    batch_id: str
    status: str
    duplicate_of_job_id: str
    warning: str


class SyncWarningResponse(BaseModel):
    job_id: str
    status: str
    sync_warning: str | None = None


class BatchSummaryResponse(BaseModel):
    batch_id: str
    total_jobs: int
    inserted: int
    scorable: int
    non_scorable: int
    skipped_exact_duplicate: int
    duplicate_ignored: int
    qdrant_upserted: int
    qdrant_failed: int
    failed_extractions: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    average_extraction_time_ms: float | None
```

Role profile endpoints must return `RoleProfileResponse`. Review and dashboard endpoints must return `list[JobListItemResponse]`. Job detail must return `JobDetailResponse`. These DTOs expose stored Phase 3 fields only; the frontend must not recompute scoring.

Parse URL request:

```json
{
  "role_profile_id": "role-profile-uuid",
  "url": "https://example.com/job"
}
```

Parse text request:

```json
{
  "role_profile_id": "role-profile-uuid",
  "raw_text": "job description text"
}
```

Manual-input warning response:

```json
{
  "job_id": "job-uuid",
  "batch_id": "batch-uuid",
  "status": "pending_review",
  "jd_status": "unclear",
  "parse_status": "needs_manual_input",
  "final_score_percent": null,
  "warning": "We could not extract enough job content from this URL.\nThe page may require JavaScript rendering, login, or cookie acceptance.\nPlease paste the job description text manually.",
  "duplicate_of_job_id": null,
  "sync_warning": null,
  "error_reason": "Extracted content was too short or unreliable."
}
```

Duplicate response example:

```json
{
  "job_id": null,
  "batch_id": "batch-uuid",
  "status": "skipped_duplicate",
  "jd_status": null,
  "parse_status": "success",
  "final_score_percent": null,
  "warning": "This job appears to duplicate an existing job and was not added back to the review queue.",
  "duplicate_of_job_id": "existing-job-uuid",
  "sync_warning": null,
  "error_reason": null
}
```

Sync warning response example:

```json
{
  "job_id": "job-uuid",
  "batch_id": "batch-uuid",
  "status": "saved",
  "jd_status": "full_jd",
  "parse_status": "success",
  "final_score_percent": 88.4,
  "warning": null,
  "duplicate_of_job_id": null,
  "sync_warning": "SQLite status was updated, but Qdrant payload sync failed.",
  "error_reason": null
}
```

## 13. Tavily Search Integration Plan

Endpoint:

```text
POST /api/jobs/search
```

Rules:

- Use Tavily or similar public search API.
- Limit by `MAX_URLS_PER_BATCH`.
- Normalize each search result into URL/title/source metadata.
- Process each result independently.
- One failed result must not crash the whole search batch.
- If a page cannot be parsed, return and persist controlled fallback state.
- Do not use Celery or Redis in MVP.
- Do not implement authenticated LinkedIn/Facebook crawling.

Expected normalized result shape:

```python
class SearchResultItem(BaseModel):
    title: str | None
    url: str
    source_platform: str = "tavily"
    snippet: str | None = None
```

Per-result isolation:

```text
Each URL result should run through the same URL extraction -> extraction graph -> Phase 3 scoring/storage pipeline.
Failures are collected into batch summary counters instead of aborting the full batch.
```

Batch summary counters must include inserted jobs, scorable jobs, non-scorable jobs, skipped exact duplicates, duplicate ignored rows, Qdrant upserts, Qdrant failures, failed extractions, token totals, cost totals, and average extraction time.

## 14. Frontend Architecture Plan

Use React + TypeScript + Vite with Axios, React Router, and lucide-react.

Files:

- `src/config.ts`: safe public frontend config only.
- `api/client.ts`: Axios instance with base URL and JSON error normalization.
- `api/jobs.ts`: job API functions.
- `api/roleProfiles.ts`: role profile API functions.
- `types/job.ts`: job, score breakdown, metrics, warning, duplicate, sync warning, and status types.
- `types/roleProfile.ts`: role profile create/list types.
- `App.tsx`: route layout and navigation.

Use a compact operational UI: top navigation, dense job cards/tables, clear empty states, no marketing landing page, and no secret config in the browser.

Duplicate UI behavior:

```text
If the API response includes `duplicate_of_job_id`, show a non-blocking message:
"This job appears to duplicate an existing job and was not added back to the review queue."
```

Qdrant sync warning UI behavior:

```text
If the API response includes `sync_warning`, show a warning banner but keep the SQLite status as the source of truth.
```

## 15. React Page Plan

`DashboardPage.tsx`:

- show saved jobs ranked by final score
- show a clear empty state before any job is approved
- include `MetricsPanel`
- each job shows title, company, location, level, work mode, JD status, final score, status, score breakdown, and status dropdown
- dashboard data comes from `GET /api/jobs` and contains `saved` jobs only

`ReviewQueuePage.tsx`:

- show pending-review jobs ranked by score
- include manual URL and manual text forms
- job cards include approve/reject actions
- show non-scorable warnings and source URL
- show duplicate messages and sync warning banners
- review data comes from `GET /api/jobs/review` and contains `pending_review` jobs only

`RoleProfilesPage.tsx`:

- create and list role profiles
- form fields: target role, level, location, accept remote, skills comma input, resume text

`DemoModePage.tsx`:

- trigger `/api/jobs/mock-load`
- show seeded role profile and latest batch summary
- link to review queue first
- include a command fallback for `python scripts/seed_demo.py --reset`

## 16. UI Component Plan

`JobCard.tsx`:

- reusable for dashboard and review queue
- shows score badge only when scored
- shows approve/reject buttons only in review queue
- embeds `ScoreBreakdown` and `StatusSelect`

`ScoreBreakdown.tsx`:

- accordion or modal
- displays stored Phase 3 score components as percentages
- does not recompute scoring in the frontend
- shows a non-scorable message when score fields are null

`MetricsPanel.tsx`:

- shows parsed jobs, scorable jobs, failed extractions, duplicate counters, Qdrant counters, total input tokens, total output tokens, total tokens, estimated cost, and average extraction time
- uses stored token/cost fields and batch counters

`ManualUrlForm.tsx` and `ManualTextForm.tsx`:

- require selected role profile
- show loading state
- surface URL extraction warning when backend returns `needs_manual_input`
- surface duplicate messages and sync warnings

`StatusSelect.tsx`:

- allowed values: `saved`, `applied`, `interview`, `rejected`, `offer`, `ignored`
- calls status API and refreshes current page

`LoadingState.tsx` and `ErrorAlert.tsx`:

- consistent feedback for API loading and errors

## 17. Score Breakdown UI Plan

For scored jobs, show stored Phase 3 fields:

| Component | Value |
|---|---:|
| Semantic Similarity | `embedding_similarity * 100` |
| Skill Overlap | `skill_overlap_score * 100` |
| Location Match | `location_match_score * 100` |
| Level Match | `level_match_score * 100` |
| JD Confidence | `jd_confidence_multiplier * 100` |
| Final Score | `final_score_percent` |

For non-scorable jobs, show:

```text
This job was saved for review but was not scored because the JD is incomplete or unclear.
```

## 18. Cost and Performance Metrics UI Plan

Use `GET /api/batches/{batch_id}/summary` and simple backend SQL aggregation over stored `job_posts` fields.

Batch summary rule:

```text
Persisted job rows can reconstruct inserted, scorable, non_scorable, duplicate_ignored, failed_extractions, token totals, cost totals, and average extraction time.
Skipped rows, especially skipped_exact_duplicate, are not reconstructable from `job_posts` unless Phase 4 preserves the immediate Phase 3 pipeline summary in the API response or in memory for the current run.
Do not add a `search_runs` or analytics table unless `Master_Plan.md` changes.
```

Metrics:

- total jobs
- inserted jobs
- scorable jobs
- non-scorable jobs
- skipped exact duplicates
- duplicate ignored rows
- Qdrant upserted
- Qdrant failed
- failed extractions
- total input tokens
- total output tokens
- total tokens
- estimated cost
- average extraction time when available

No cron jobs or analytics tables.

## 19. Manual Input Flow Plan

Manual URL flow:

1. User selects role profile.
2. User enters URL.
3. Backend validates URL and calls the existing Phase 2 URL extraction flow using `httpx` + `trafilatura`.
4. If extraction succeeds, backend runs Phase 2 extraction graph, Phase 3 scoring/storage/dedup/Qdrant sync, and returns `JobPipelineResponse`.
5. If URL extraction returns `parse_status = "needs_manual_input"`, the backend should return a warning and persist a controlled `unclear` pending-review fallback record when the pipeline returns fallback state.

The fallback record must use:

- `jd_status = "unclear"`
- `should_score_similarity = false`
- `extraction_status = "failed"`
- `status = "pending_review"`
- score fields = null
- meaningful `error_reason`

UI warning:

```text
We could not extract enough job content from this URL.
The page may require JavaScript rendering, login, or cookie acceptance.
Please paste the job description text manually.
```

The warning is shown to the user, but the failed/unclear record remains visible in the review queue for transparency unless deduplication policy skips it.

Manual raw text flow:

1. User selects role profile.
2. User pastes text.
3. Backend runs Phase 2 extraction, then Phase 3 scoring/storage/dedup/Qdrant sync.
4. Result appears in the review queue.
5. Messy social posts should become `contact_for_jd`, `partial_jd`, or `unclear`.

## 20. Demo Mode Flow Plan

`POST /api/jobs/mock-load` accepts:

```json
{ "reset": true }
```

Behavior:

- clears demo data when requested
- seeds role profile and jobs
- inserts seeded jobs as `pending_review`
- upserts Qdrant vectors only for scorable jobs
- returns role profile, batch ID, inserted counts, and metrics summary

The UI calls this endpoint from `DemoModePage`. The script `seed_demo.py` remains the command-line fallback for live demos. Both entry points must call the same shared demo loader.

Demo jobs must not be made `saved` by the seed script. The dashboard should be empty until the user approves at least one job.

## 21. Error Handling and User Warnings

Backend returns consistent JSON errors:

```json
{
  "error": "invalid_role_profile",
  "message": "Role profile was not found."
}
```

Handle:

- backend unavailable: frontend `ErrorAlert`
- Qdrant unavailable: API returns partial success if SQLite saved but vector sync failed
- SQLite write failure: API returns failure and no Qdrant upsert
- invalid role/job ID: 404 or 422
- invalid URL: 422
- URL needs manual input: warning plus controlled `unclear` pending-review fallback record when fallback state exists
- extraction failed: controlled `unclear` pending-review job or user-facing failure message
- duplicate job: return `duplicate_of_job_id`, never re-add to pending review
- non-scorable JD: show saved-for-review warning
- approve/reject sync issue: SQLite status remains source of truth, response includes `sync_warning`
- empty review/dashboard: clear empty state
- seed data already exists: `reset=true` clears it, otherwise skip duplicates safely

Application table policy:

```text
For MVP, `/api/jobs/{id}/status` must update `job_posts.status` as the source of truth.
When status changes to `applied`, `interview`, `rejected`, or `offer`, Phase 4 may create or update an `applications` row using `job_post_id`.
If application-row writes are deferred, document that `applications` is reserved for later tracking and do not let that deferment block the demo.
```

Duplicate UI message:

```text
This job appears to duplicate an existing job and was not added back to the review queue.
```

Manual URL warning:

```text
We could not extract enough job content from this URL.
The page may require JavaScript rendering, login, or cookie acceptance.
Please paste the job description text manually.
```

## 22. End-to-End Demo Script

Run services:

```powershell
docker compose up -d qdrant
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Seed:

```powershell
cd backend
python scripts/seed_demo.py --reset
```

Start frontend:

```powershell
cd frontend/job-agent-ui
npm run dev
```

Demo path:

1. Start Qdrant Local.
2. Start FastAPI backend.
3. Run `seed_demo.py --reset`.
4. Start React frontend.
5. Open Review Queue first.
6. Show pending-review jobs ranked by score.
7. Open score breakdown for a strong job.
8. Approve a high-score job.
9. Navigate to Dashboard.
10. Show the approved job now appears in saved dashboard.
11. Reject a weak or duplicate job.
12. Confirm rejected job disappears from review queue and its Qdrant vector is deleted.
13. Show metrics panel.
14. Paste a messy social post and show it becomes `contact_for_jd`, `partial_jd`, or `unclear`.
15. Show manual URL fallback warning if extraction is unreliable.

## 23. Testing Plan

Backend test files:

```text
backend/tests/test_api_role_profiles.py
backend/tests/test_api_jobs.py
backend/tests/test_api_batches.py
backend/tests/test_job_pipeline_service.py
```

Backend test cases:

1. Create role profile.
2. List role profiles.
3. Parse raw text using Phase 2/3 pipeline services.
4. Parse URL success.
5. Parse URL returns `needs_manual_input` warning and fallback record.
6. Search endpoint normalizes Tavily results.
7. Search endpoint isolates per-result failures.
8. Review queue returns `pending_review` jobs only.
9. Dashboard returns `saved` jobs only.
10. Approve job calls sync service and updates SQLite/Qdrant.
11. Reject job calls sync service and deletes Qdrant vector.
12. Manual status update syncs SQLite and Qdrant.
13. Duplicate response includes `duplicate_of_job_id`.
14. Sync warning response includes `sync_warning`.
15. Batch summary returns inserted, scorable, non_scorable, skipped_exact_duplicate, duplicate_ignored, qdrant_upserted, qdrant_failed, token/cost metrics.
16. `seed_demo.py --reset` creates at least 12 pending-review demo jobs.
17. Demo seed upserts vectors only for scorable jobs.

Frontend test files:

```text
frontend/job-agent-ui/src/__tests__/DashboardPage.test.tsx
frontend/job-agent-ui/src/__tests__/ReviewQueuePage.test.tsx
frontend/job-agent-ui/src/__tests__/ManualUrlForm.test.tsx
frontend/job-agent-ui/src/__tests__/ManualTextForm.test.tsx
frontend/job-agent-ui/src/__tests__/MetricsPanel.test.tsx
frontend/job-agent-ui/src/__tests__/ScoreBreakdown.test.tsx
```

Frontend test cases:

1. Frontend does not require a separate `.env`.
2. Dashboard renders saved jobs.
3. Empty dashboard state is clear before approval.
4. Review queue renders pending jobs after seed.
5. Approve button moves job to dashboard.
6. Reject button removes job from review queue.
7. Status dropdown works.
8. Score breakdown opens and displays all score components.
9. Metrics panel displays totals.
10. Manual URL form shows warning on `needs_manual_input`.
11. Manual text form submits successfully.
12. Duplicate message is shown.
13. Sync warning banner is shown.
14. No secret environment values are exposed in frontend code.

End-to-end demo test cases:

1. Start Qdrant Local.
2. Start backend.
3. Run `seed_demo.py --reset`.
4. Start frontend.
5. Open review queue.
6. Approve high-score job.
7. Confirm dashboard shows approved job.
8. Reject weak job.
9. Confirm rejected job no longer appears in review queue.
10. Open score breakdown.
11. Confirm metrics panel.
12. Submit manual raw text.
13. Submit URL that triggers manual-input warning.

Run backend tests:

```powershell
cd backend
pytest -v
```

Run frontend tests:

```powershell
cd frontend/job-agent-ui
npm run test
npm run build
```

## 24. Verification Checklist

- [ ] Phase 4 does not create `frontend/job-agent-ui/.env.example`.
- [ ] The project keeps a single root `.env`.
- [ ] Frontend never receives API keys or secrets.
- [ ] Frontend API base URL uses a safe default or safe generated config only.
- [ ] Phase 4 reuses Phase 2 extraction services.
- [ ] Phase 4 reuses Phase 3 scoring, storage, dedup, and Qdrant sync services.
- [ ] `job_pipeline_service.py` calls Phase 3 public service or graph contracts instead of rewriting them.
- [ ] One shared demo loader is used by both `seed_demo.py` and `/api/jobs/mock-load`.
- [ ] `seed_demo.py --reset` loads at least 12 demo jobs.
- [ ] Seeded demo jobs start as `pending_review`, not `saved`.
- [ ] Demo can run without internet for mock data.
- [ ] SQLite contains demo role profile and job data.
- [ ] Qdrant contains vectors only for scorable jobs.
- [ ] Review queue shows `pending_review` jobs ranked by score.
- [ ] Dashboard shows `saved` jobs only after user approval.
- [ ] Approve updates SQLite and Qdrant payload to `saved`.
- [ ] Reject updates SQLite to `ignored` and deletes the Qdrant vector.
- [ ] Score breakdown is visible in UI and uses stored Phase 3 score fields.
- [ ] Metrics panel shows stored token/cost data and batch counters.
- [ ] Manual URL input handles low-content pages with the required warning.
- [ ] Manual raw text input works.
- [ ] Duplicate API responses are visible to the frontend.
- [ ] Qdrant sync warnings are visible to the frontend.
- [ ] Tavily results are normalized and processed independently.
- [ ] One failed search result does not crash the whole batch.
- [ ] Celery and Redis are not introduced.
- [ ] Deterministic mock vectors are demo-only, require an explicit demo-offline path, and match `EMBEDDING_DIMENSION`.
- [ ] Normal URL, text, and Tavily flows cannot use deterministic mock vectors.
- [ ] Job list, job detail, role profile, and score breakdown DTOs expose stored backend fields needed by the UI.
- [ ] API responses make warnings and partial failures visible without crashing the user flow.
- [ ] SQLite remains the source of truth for job status.
- [ ] Empty states are clear and user-friendly.
- [ ] MVP is ready for live portfolio demo.

## 25. Expected Final State

At the end of Phase 4:

- FastAPI exposes all required endpoints.
- Demo seed data loads into SQLite and Qdrant.
- Seeded jobs start in the review queue.
- Frontend displays pending review jobs and saved dashboard jobs.
- User can create role profiles.
- User can parse manual URLs and raw text.
- User can search public jobs through Tavily or a similar public search API.
- User can approve, reject, and manually update job status.
- Score breakdown is visible.
- Metrics panel shows pipeline performance and cost.
- Duplicate and sync warning responses are visible to the user.
- Demo mode is stable and does not depend on external job websites.
- The complete MVP is ready for a live portfolio walkthrough.

## 26. Final MVP Acceptance Criteria

- Phase 4 does not create `frontend/job-agent-ui/.env.example`.
- The project keeps a single root `.env`.
- Frontend never receives API keys or secrets.
- Frontend API base URL uses a safe default or safe generated config only.
- Phase 4 reuses Phase 2 extraction services.
- Phase 4 reuses Phase 3 scoring, storage, dedup, and Qdrant sync services.
- `job_pipeline_service.py` calls Phase 3 public service or graph contracts instead of rewriting them.
- One shared demo loader is used by both `seed_demo.py` and `/api/jobs/mock-load`.
- `needs_manual_input` returns a warning and persists a controlled `unclear` pending-review fallback record when fallback state exists.
- Review queue is the first main demo screen after seeding.
- Seeded demo jobs start as `pending_review`, not `saved`.
- Dashboard shows approved/saved jobs only after user approval.
- Duplicate API responses are visible to the frontend.
- Qdrant sync warnings are visible to the frontend.
- Tavily results are normalized and processed independently.
- One failed search result does not crash the whole batch.
- Celery and Redis are not introduced.
- Deterministic mock vectors are demo-only, require an explicit demo-offline path, and match `EMBEDDING_DIMENSION`.
- Normal URL, text, and Tavily flows cannot use deterministic mock vectors.
- Manual URL fallback warning is displayed clearly.
- Manual raw text flow works.
- Score breakdown UI uses stored Phase 3 score fields.
- Metrics panel uses stored token/cost fields and batch counters.
- Approve calls Phase 3 sync service and updates Qdrant payload to `saved`.
- Reject calls Phase 3 sync service and deletes Qdrant vector.
- SQLite remains the source of truth for job status.
