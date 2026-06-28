# Plan 4 - FastAPI Routes, Search, and Demo Seeding

## 1. Objective

Expose the completed backend pipeline through FastAPI routes and add demo-mode seeding. This phase wires role profiles, manual text parsing, manual URL parsing, Tavily search, mock loading, review queue, dashboard queries, status updates, and batch summaries to the services built in Plans 1 through 3.

After this phase, the backend can run the complete MVP workflow without the React frontend.

## 2. Source of Truth

- `Master_Plan.md` section 3, "MVP Scope"
- `Master_Plan.md` section 4, "Architecture"
- `Master_Plan.md` section 5, "Demo Mode / Mock Seeding"
- `Master_Plan.md` section 6, "Input Sources"
- `Master_Plan.md` section 7, "Handling JavaScript Pages and Cookie Banners"
- `Master_Plan.md` section 19, "Human-in-the-Loop Rules"
- `Master_Plan.md` section 24, "SQLite Indexes"
- `Master_Plan.md` section 26, "API Endpoints"
- `Master_Plan.md` section 27, "URL Parsing Security Note"
- `Master_Plan.md` section 28, "Input Size and Retry Limits"
- `Master_Plan.md` section 34, "Demo Script Pseudocode"
- `Master_Plan.md` section 35, "Implementation Checklist: Demo Readiness, Search and Parsing, Database, Qdrant Local"

## 3. Prerequisites from Prior Phases

- [ ] Plan 1 backend app, settings, database, and models exist.
- [ ] Plan 2 extraction graph and URL/text parsing services exist.
- [ ] Plan 3 scoring, deduplication, persistence, and Qdrant sync services exist.
- [ ] Local Qdrant can be started with `docker compose up -d qdrant`.
- [ ] Status mutation helpers keep SQLite and Qdrant in sync.

## 4. Scope

- Add FastAPI route modules:
  - `routes_role_profiles.py`
  - `routes_jobs.py`
  - `routes_batches.py`
- Wire route modules into `backend/app/main.py`.
- Add FastAPI CORS middleware for the local React dev origin `http://localhost:5173`.
- Keep CORS local-development only in this phase.
- Add request and response schemas for backend API payloads.
- Implement role profile create and list endpoints.
- Implement manual raw text parsing endpoint.
- Implement manual public URL parsing endpoint.
- Implement Tavily public job search endpoint.
- Implement mock load endpoint.
- Implement review queue endpoint.
- Implement dashboard jobs endpoint.
- Implement job detail endpoint.
- Implement approve endpoint.
- Implement reject endpoint.
- Implement manual status update endpoint.
- Implement batch summary endpoint for metrics.
- Add `search_service.py` with Tavily integration and configured batch limits.
- Add `demo_loader.py` and `backend/scripts/seed_demo.py`.
- Add `mock_data/demo_jobs.json` and `mock_data/messy_social_posts.json`.
- Ensure demo seeding creates 12 jobs with the required composition.
- Ensure `seed_demo.py --reset` clears only demo/mock-owned data and matching Qdrant demo vectors.
- Add route tests with mocked LLM, Tavily, and Qdrant where needed.

## 5. Out of Scope

- Do not implement React UI.
- Do not change database schema, scoring formulas, or dedup policy.
- Do not add authenticated LinkedIn or Facebook scraping.
- Do not add Playwright/browser rendering.
- Do not add distributed background queues such as Celery or Redis.
- Do not add multi-user authentication or organizations.
- Do not generate cover letters.
- Do not auto-apply to jobs.
- Do not expose API keys to route responses.

## 6. Target Directory Structure

```text
Job_Agent/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- routes_batches.py
|   |   |   |-- routes_jobs.py
|   |   |   |-- routes_role_profiles.py
|   |   |   `-- schemas.py
|   |   |-- services/
|   |   |   |-- demo_loader.py
|   |   |   |-- search_service.py
|   |   |   |-- extraction_service.py
|   |   |   |-- job_processing_service.py
|   |   |   |-- scoring_service.py
|   |   |   |-- qdrant_service.py
|   |   |   |-- dedup_service.py
|   |   |   `-- cost_service.py
|   |   `-- main.py
|   |-- scripts/
|   |   `-- seed_demo.py
|   `-- tests/
|       |-- test_routes_jobs.py
|       |-- test_routes_role_profiles.py
|       |-- test_routes_batches.py
|       `-- test_seed_demo.py
`-- mock_data/
    |-- demo_jobs.json
    `-- messy_social_posts.json
```

## 7. Technical Specifications

### API Endpoints

Implement the endpoint contract from the master plan:

```text
POST  /api/role-profiles
GET   /api/role-profiles
POST  /api/jobs/search
POST  /api/jobs/parse-url
POST  /api/jobs/parse-text
POST  /api/jobs/mock-load
GET   /api/jobs/review
POST  /api/jobs/{id}/approve
POST  /api/jobs/{id}/reject
PATCH /api/jobs/{id}/status
GET   /api/jobs
GET   /api/jobs/{id}
GET   /api/batches/{batch_id}/summary
```

### Common API Response Shapes

Job response fields must include all fields needed by Plan 5:

```json
{
  "id": "uuid",
  "batch_id": "uuid",
  "role_profile_id": "uuid",
  "title": "AI Engineer Intern",
  "company": "ABC AI Lab",
  "location": "Ha Noi",
  "work_mode": "remote",
  "level": "intern",
  "employment_type": "internship",
  "salary": null,
  "responsibilities": "...",
  "requirements": "...",
  "skills": ["python", "rag"],
  "source_url": null,
  "source_platform": "mock",
  "parse_status": "success",
  "jd_status": "full_jd",
  "extraction_status": "success",
  "error_reason": null,
  "should_score_similarity": true,
  "embedding_similarity": 0.85,
  "skill_overlap_score": 0.9,
  "location_match_score": 1.0,
  "level_match_score": 1.0,
  "base_score": 0.88,
  "jd_confidence_multiplier": 1.0,
  "final_score": 0.88,
  "final_score_percent": 88.0,
  "status": "pending_review",
  "input_tokens": 1000,
  "output_tokens": 300,
  "estimated_cost_usd": 0.003,
  "extraction_time_ms": 1200,
  "discovered_at": "iso datetime",
  "created_at": "iso datetime",
  "updated_at": "iso datetime"
}
```

For nullable score fields, return `null`; do not omit them.
Ingestion endpoints must return transient warning messages through the standard `warnings` array. Persisted job responses should expose stored fields from `job_posts`, including `error_reason`, without adding non-Master columns.

### API Schema Ownership

Define all request and response Pydantic models in:

```text
backend/app/api/schemas.py
```

Route modules should import these schemas instead of defining conflicting local response shapes.

### CORS

Configure FastAPI CORS for local frontend development:

```text
allow_origins = ["http://localhost:5173"]
allow_credentials = false
allow_methods = ["*"]
allow_headers = ["*"]
```

Do not expose API keys, `.env` values, or backend secrets through any config endpoint.

### Service Boundary

Route handlers must not implement scoring, deduplication, persistence, embedding, or Qdrant sync directly.

They must call Plan 3 service methods:

```text
job_processing_service.process_extraction_state(...)
job_processing_service.approve_job(...)
job_processing_service.reject_job(...)
job_processing_service.update_job_status(...)
```

Routes own only HTTP validation, request parsing, response formatting, and dependency injection.

### Role Profile Routes

`POST /api/role-profiles`

Required request fields:

```json
{
  "target_role": "AI Engineer Intern",
  "level": "intern",
  "location": "Ha Noi",
  "accept_remote": true,
  "skills": ["python", "rag", "langchain", "fastapi", "qdrant"],
  "resume_text": "..."
}
```

Response must include the generated UUID `id`.

`GET /api/role-profiles`

Return existing profiles sorted by `created_at DESC` or a consistent equivalent.

### Parse Routes

`POST /api/jobs/parse-text`

Request:

```json
{
  "role_profile_id": "uuid",
  "raw_text": "job description text",
  "source_url": null
}
```

Flow:

```text
create batch_id
run Plan 2 extraction with input_source = manual_text
run Plan 3 score/dedup/persist/Qdrant pipeline
return batch_id, inserted count, skipped duplicate count, and created jobs
```

`POST /api/jobs/parse-url`

Request:

```json
{
  "role_profile_id": "uuid",
  "source_url": "https://example.com/job"
}
```

Flow:

```text
validate http/https URL
respect request timeout and response size limit
run URL fetch/clean/extract
save parsed result as pending_review or needs_manual_input result
return warning if parse_status = needs_manual_input
```

All ingestion endpoints must return:

```json
{
  "batch_id": "uuid",
  "inserted_jobs": 1,
  "skipped_exact_duplicates": 0,
  "skipped_dedup_key_duplicates": 0,
  "inserted_duplicate_metadata": 0,
  "qdrant_upserted": 1,
  "qdrant_synced": true,
  "jobs": [],
  "warnings": []
}
```

This response should be produced from Plan 3 `job_processing_service.py`.

URL route must include this production note in code:

```text
Production note: Implement SSRF mitigation for URL parsing endpoints.
Block localhost, private IPs, link-local metadata IPs, unsafe redirects, and internal network targets.
```

### Search Route

`POST /api/jobs/search`

Request:

```json
{
  "role_profile_id": "uuid",
  "query": "AI Engineer Intern LangChain FastAPI Qdrant",
  "max_urls": 10
}
```

Rules:

- Use Tavily or equivalent public web search API.
- Enforce `MAX_URLS_PER_BATCH`.
- For each result URL, reuse the same parsing and persistence path as `/api/jobs/parse-url`.
- Do not add authenticated LinkedIn/Facebook crawling.
- If a search result cannot be parsed reliably, return a warning and save an unclear or needs-manual-input record as appropriate.

MVP search behavior is synchronous and request-scoped.

Do not add Celery, Redis, durable queues, workers, or cron jobs.

Flow:

```text
1. Create one batch_id.
2. Call Tavily with max_urls clamped to MAX_URLS_PER_BATCH.
3. For each returned URL, reuse the parse-url extraction and Plan 3 processing pipeline.
4. Continue processing other URLs if one URL fails.
5. Return batch_id, counts, created jobs, and warnings.
```

If Tavily fails, return HTTP 502 with a clear message and do not create partial fake jobs unless some URLs were already processed.

### Mock Load Endpoint

`POST /api/jobs/mock-load`

Request:

```json
{
  "role_profile_id": "uuid",
  "reset_existing_demo": false
}
```

Behavior:

```text
1. Create one batch_id.
2. Load `mock_data/demo_jobs.json` and `mock_data/messy_social_posts.json`.
3. Process all mock jobs through Plan 3 job processing services.
4. Return the standard ingestion response.
```

This endpoint must reuse `demo_loader.py`; it must not duplicate seed script logic.

### Review and Dashboard Queries

Review queue query:

```sql
SELECT *
FROM job_posts
WHERE role_profile_id = ?
  AND status = 'pending_review'
  AND duplicate_of_job_id IS NULL
ORDER BY final_score IS NULL, final_score DESC, discovered_at DESC
LIMIT 50;
```

Dashboard query:

```sql
SELECT *
FROM job_posts
WHERE role_profile_id = ?
  AND status = 'saved'
  AND duplicate_of_job_id IS NULL
ORDER BY final_score IS NULL, final_score DESC
LIMIT 50;
```

`GET /api/jobs/review`

Query params:

```text
role_profile_id
limit optional default 50 max 100
```

`GET /api/jobs`

Query params:

```text
role_profile_id
status optional default saved
Allowed values:
- pending_review
- saved
- applied
- interview
- rejected
- offer
- ignored
- tracked
limit optional default 50 max 100
```

When `status = tracked`, return:

```text
saved, applied, interview, rejected, offer
```

Use this for the Plan 5 saved/tracked dashboard so jobs do not disappear after manual status updates.

### Human-in-the-Loop Status Routes

Allowed transitions:

```text
pending_review -> saved
pending_review -> ignored
saved -> applied
saved -> rejected
applied -> interview
applied -> rejected
interview -> rejected
interview -> offer
```

Route handlers must reject invalid transitions with HTTP 400.

Only `POST /api/jobs/{id}/reject` performs review rejection:

```text
pending_review -> ignored
```

Manual `PATCH /api/jobs/{id}/status` must not set `ignored`.

`POST /api/jobs/{id}/approve`

- Set SQLite status to `saved`.
- Update Qdrant payload status to `saved` if the job has a vector.

`POST /api/jobs/{id}/reject`

- Set SQLite status to `ignored`.
- Delete the Qdrant point if it exists.

`PATCH /api/jobs/{id}/status`

Request:

```json
{
  "status": "applied"
}
```

- Update SQLite status through Plan 3 service methods.
- The `PATCH /api/jobs/{id}/status` endpoint must call Plan 3 service methods so `job_posts.status` is updated and the `applications` row is created or updated when changing status to a tracked state (`applied`, `interview`, `rejected`, or `offer`).
- Use Plan 3 status sync behavior:
  - approve -> update Qdrant payload status to saved
  - review reject -> delete Qdrant point
  - manual applied/interview/rejected/offer -> update Qdrant payload status
- Do not duplicate Qdrant logic inside route handlers.

### Batch Summary

`GET /api/batches/{batch_id}/summary`

Return metrics computed from stored per-job fields:

```json
{
  "batch_id": "uuid",
  "total_parsed_jobs": 12,
  "scorable_jobs": 10,
  "failed_extractions": 1,
  "total_input_tokens": 10000,
  "total_output_tokens": 8420,
  "total_tokens": 18420,
  "estimated_cost_usd": 0.043,
  "average_extraction_time_ms": 1200
}
```

If no rows exist for `batch_id`, return HTTP 404.

Aggregation rules:

- `total_parsed_jobs` = count rows for `batch_id`
- `scorable_jobs` = count where `should_score_similarity = true`
- `failed_extractions` = count where `extraction_status = "failed"`
- `total_input_tokens` = sum `input_tokens` treating null as 0
- `total_output_tokens` = sum `output_tokens` treating null as 0
- `total_tokens` = `total_input_tokens + total_output_tokens`
- `estimated_cost_usd` = sum `estimated_cost_usd` treating null as 0
- `average_extraction_time_ms` = average non-null `extraction_time_ms`, or null

Avoid analytics tables and cron jobs.

### Demo Dataset

`mock_data/demo_jobs.json` plus `mock_data/messy_social_posts.json` must include 12 total demo inputs:

```text
5 perfect matches
3 partial matches
2 unrelated jobs
2 messy social posts
```

Required examples to include or closely mirror:

```text
AI Engineer Intern - RAG + LangChain + FastAPI + Qdrant
LLM Application Intern - Python + OpenAI API + Vector DB
Backend Intern - FastAPI + SQLite, partial AI relevance
Data Analyst Intern - mostly unrelated
Social post requiring inbox/DM for JD
```

Use ASCII-safe location strings in JSON such as `Ha Noi` unless the repository already standardizes Vietnamese Unicode.

### seed_demo.py

Command:

```powershell
cd backend
python scripts/seed_demo.py --reset
```

Responsibilities:

- Clear existing demo data if `--reset` is passed.
- Clear Qdrant demo vectors.
- Create a demo role profile.
- Insert demo jobs into SQLite.
- For scorable jobs, build `embedding_text`.
- Upsert vectors into local Qdrant.
- Print demo summary.

`--reset` must delete only demo/mock-owned data.
Do not use any non-existent columns (like `is_demo` or similar) to filter mock data. Filter SQLite `job_posts` and Qdrant vectors where `source_platform = 'mock'`.
Do not wipe manually entered or Tavily-created jobs.
Qdrant reset must delete only matching demo vectors.
Delete the demo role profile only if it matches the deterministic demo profile name and has no remaining non-mock jobs referencing it.

Expected output:

```text
Seed completed.
Role profile: AI Engineer Intern
Inserted jobs: 12
Scorable jobs: 10
Need-review/social jobs: 2
Local Qdrant vectors upserted: 10
```



## 8. Implementation Steps

- [ ] Create API request and response schemas in `backend/app/api/schemas.py`.
- [ ] Add `backend/app/api/schemas.py`.
- [ ] Define stable request/response schemas for all endpoints.
- [ ] Implement `routes_role_profiles.py`.
- [ ] Implement `routes_jobs.py`.
- [ ] Implement `routes_batches.py`.
- [ ] Register all routers in `backend/app/main.py` under `/api`.
- [ ] Add local CORS middleware for `http://localhost:5173`.
- [ ] Implement `search_service.py` with Tavily integration and `MAX_URLS_PER_BATCH`.
- [ ] Ensure `/api/jobs/parse-text` reuses Plan 2 extraction and Plan 3 persistence pipeline.
- [ ] Ensure `/api/jobs/parse-url` reuses Plan 2 URL cleaning and Plan 3 persistence pipeline.
- [ ] Ensure `/api/jobs/search` uses Tavily then reuses the same URL parsing pipeline.
- [ ] Ensure ingestion endpoints return the standard ingestion response.
- [ ] Ensure all route handlers call Plan 3 service methods instead of duplicating business logic.
- [ ] Ensure `/api/jobs/mock-load` loads mock files and reuses Plan 3 scoring/persistence/Qdrant behavior.
- [ ] Implement review queue and dashboard queries with duplicate exclusion.
- [ ] Add `status=tracked` support to `GET /api/jobs`.
- [ ] Implement approve, reject, and manual status update routes using Plan 3 status sync helpers.
- [ ] Ensure `PATCH /api/jobs/{id}/status` cannot set `ignored`.
- [ ] Implement batch summary aggregation from `job_posts`.
- [ ] Create `demo_loader.py`.
- [ ] Create `backend/scripts/seed_demo.py`.
- [ ] Ensure mock-load and seed_demo share `demo_loader.py`.
- [ ] Ensure `--reset` only clears demo/mock data.
- [ ] Create `mock_data/demo_jobs.json`.
- [ ] Create `mock_data/messy_social_posts.json`.
- [ ] Add route tests with mocked LLM and Qdrant.
- [ ] Add seed demo tests with temporary SQLite database and mocked Qdrant.

## 9. Verification & Testing Plan

Automated tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Route smoke test:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Manual API verification:

```powershell
curl http://localhost:8000/api/role-profiles
```

Seed verification:

```powershell
docker compose up -d qdrant
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/seed_demo.py --reset
```

Expected seed output:

```text
Seed completed.
Role profile: AI Engineer Intern
Inserted jobs: 12
Scorable jobs: 10
Need-review/social jobs: 2
Local Qdrant vectors upserted: 10
```

Expected route test cases:

- CORS allows `http://localhost:5173`.
- Role profile create returns UUID.
- Parse text inserts a `pending_review` job.
- Parse-text returns standard ingestion response.
- Parse URL with low content returns a manual input warning.
- Search endpoint respects `MAX_URLS_PER_BATCH`.
- Search continues after one URL parse failure.
- Tavily failure returns HTTP 502 without crashing.
- Review queue excludes duplicates.
- Dashboard jobs endpoint excludes duplicates and returns saved jobs sorted by score.
- `GET /api/jobs?status=tracked` returns saved/applied/interview/rejected/offer jobs.
- Approve updates SQLite and Qdrant payload status.
- Reject sets `ignored` and deletes the Qdrant point.
- Manual status update changes SQLite and syncs Qdrant.
- `PATCH /api/jobs/{id}/status` rejects `ignored`.
- Invalid status transitions return HTTP 400.
- Mock-load reuses demo_loader and returns batch_id.
- seed_demo --reset does not delete non-mock jobs.
- Batch summary sums tokens, cost, failure count, and parsed jobs from `job_posts`.
- Batch summary returns 404 for unknown batch_id.
- API responses do not contain API keys or env secrets.

Manual verification:

- Confirm API responses never include API keys.
- Confirm LinkedIn/Facebook authenticated scraping is absent.
- Confirm no Celery/Redis worker is introduced.
- Confirm bad extraction does not crash a batch.

## 10. Handoff Notes for Phase 5

Plan 5 consumes:

- Running FastAPI backend at `http://localhost:8000`.
- Role profile endpoints.
- Job parse, search, mock-load, review, dashboard, detail, approve, reject, status, and batch summary endpoints.
- Shared API response schemas from `backend/app/api/schemas.py`.
- Standard ingestion response shape with `batch_id`, counts, `jobs`, and `warnings`.
- `GET /api/jobs?status=tracked` for saved/applied/interview/rejected/offer dashboard views.
- Demo data that can be seeded without internet.
- Warning messages for URL pages that need manual text input.
- Score fields and score component fields for UI display.

Plan 5 must:

- Build the React dashboard against these API contracts.
- Show review queue, saved jobs, score breakdown, and metrics from the backend.
- Use approve/reject/status endpoints rather than mutating local state only.
- Keep API keys on the backend.
- Save the returned `activeBatchId` in localStorage/sessionStorage so that the metrics aggregation does not reset when page reloads or tabs toggle.
- Synchronize `activeBatchId` lifecycle with profile changes: reset it or fetch the latest batch when profiles switch.
- Add focused frontend build, typecheck, and interaction verification steps without changing backend API contracts.

Hard rules for later phases:

- Frontend must not duplicate scoring formulas.
- Frontend must not call OpenAI, Tavily, or Qdrant directly.
- Frontend must treat backend API responses as the source of truth.
- Verify that no frontend `.env`, `frontend/.env.example`, or `frontend/job-agent-ui/.env.example` exists. Only load settings via root configuration scripts if required.
