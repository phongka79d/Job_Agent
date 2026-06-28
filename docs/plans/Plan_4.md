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
- [ ] Plan 1 shared constants in `backend/app/core/constants.py` exist for status/source validation.
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
- Build API schemas from, or validate API schema literals against, the Plan 1 shared constants so route validation cannot drift from backend services.
- Call Plan 3 Qdrant collection/payload-index initialization during FastAPI startup without reimplementing Qdrant setup logic.
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
- Ensure `seed_demo.py --reset` clears only demo/mock-owned data, dependent mock-owned application rows, and matching Qdrant demo vectors.
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
|   |   |-- export_api_contract.py
|   |   `-- seed_demo.py
|   `-- tests/
|       |-- test_api_contract_export.py
|       |-- test_routes_jobs.py
|       |-- test_routes_role_profiles.py
|       |-- test_routes_batches.py
|       `-- test_seed_demo.py
|-- mock_data/
    |-- demo_jobs.json
    `-- messy_social_posts.json
`-- shared/
    `-- api-contract.json
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

`warnings` are ingestion-level messages, not persisted job-card fields. Job cards must display persisted `Job.error_reason`; ingestion result panels may display `warnings`.

### API Schema Ownership

Define all request and response Pydantic models in:

```text
backend/app/api/schemas.py
```

Route modules should import these schemas instead of defining conflicting local response shapes.
API schemas must import or test against Plan 1 constants for job statuses, application statuses, JD statuses, parse statuses, extraction statuses, source platforms, and input sources. Route modules must not define independent executable enum/string sets.

### API Contract Export

Plan 4 must create a frontend-consumable API contract artifact generated from backend constants, Plan 3 transition rules, and API schemas. Do not hand-write a separate frontend contract source of truth.

Script:

```text
backend/scripts/export_api_contract.py
```

Output artifact:

```text
shared/api-contract.json
```

The exported JSON must include at minimum this high-level shape:

```json
{
  "job_statuses": ["pending_review", "saved", "applied", "interview", "rejected", "offer", "ignored"],
  "tracked_job_statuses": ["saved", "applied", "interview", "rejected", "offer"],
  "application_statuses": ["applied", "interview", "rejected", "offer"],
  "jd_statuses": ["full_jd", "partial_jd", "contact_for_jd", "no_jd", "unclear"],
  "parse_statuses": ["success", "needs_manual_input", "failed"],
  "extraction_statuses": ["success", "retried", "failed"],
  "source_platforms": ["tavily", "manual_url", "manual_text", "mock", "job_board"],
  "input_sources": ["tavily", "manual_url", "manual_text", "mock"],
  "allowed_status_transitions": {
    "pending_review": ["saved", "ignored"],
    "saved": ["applied", "rejected"],
    "applied": ["interview", "rejected"],
    "interview": ["rejected", "offer"],
    "rejected": [],
    "offer": [],
    "ignored": []
  },
  "endpoints": {
    "createRoleProfile": {"method": "POST", "path": "/api/role-profiles"},
    "listRoleProfiles": {"method": "GET", "path": "/api/role-profiles"},
    "searchJobs": {"method": "POST", "path": "/api/jobs/search"},
    "parseJobUrl": {"method": "POST", "path": "/api/jobs/parse-url"},
    "parseJobText": {"method": "POST", "path": "/api/jobs/parse-text"},
    "loadMockJobs": {"method": "POST", "path": "/api/jobs/mock-load"},
    "getReviewJobs": {"method": "GET", "path": "/api/jobs/review"},
    "approveJob": {"method": "POST", "path": "/api/jobs/{id}/approve"},
    "rejectJob": {"method": "POST", "path": "/api/jobs/{id}/reject"},
    "updateJobStatus": {"method": "PATCH", "path": "/api/jobs/{id}/status"},
    "getJobs": {"method": "GET", "path": "/api/jobs"},
    "getJobDetail": {"method": "GET", "path": "/api/jobs/{id}"},
    "getBatchSummary": {"method": "GET", "path": "/api/batches/{batch_id}/summary"}
  },
  "schemas": {
    "JobResponse": {"type": "object"},
    "IngestionResponse": {"type": "object"},
    "BatchSummaryResponse": {"type": "object"}
  }
}
```

The `schemas` values above are placeholders for actual Pydantic-generated JSON Schema objects. The script must not emit placeholder strings or hand-maintained schema fragments.

Generation rules:

- Import status/source values from `backend/app/core/constants.py`.
- Import `ALLOWED_STATUS_TRANSITIONS` from Plan 3's status-transition service owner.
- Generate response schema metadata from `backend/app/api/schemas.py` Pydantic models using `model_json_schema()` or an equivalent Pydantic v2 JSON Schema API.
- Resolve the output path from the repository root, so running `python scripts/export_api_contract.py` from `backend/` writes `../shared/api-contract.json`.
- Write stable, sorted JSON so frontend tests can detect stale or accidental changes.
- Add a backend test or CI check that runs the export script and fails if `shared/api-contract.json` is missing or stale compared with the current backend constants/schemas.

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
If Plan 3 returns `job_ids`, the route layer must fetch those rows from SQLite and serialize them into the `jobs` array before responding. Route handlers must not recompute scores, dedup decisions, or Qdrant sync while doing this response shaping.

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
The master endpoint table describes `/api/jobs/search` as starting public web search. For the MVP, interpret that as starting and completing the search within the current HTTP request, possibly inside an async FastAPI handler. Do not introduce Celery, Redis, durable workers, cron jobs, background task tables, or persistent queue infrastructure.

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
1. If reset_existing_demo = true, call the shared demo reset helper from `demo_loader.py` before creating the new batch, passing preserve_role_profile_id = request.role_profile_id.
2. If reset_existing_demo = false, do not delete existing mock rows; rely on Plan 3 deduplication to skip or mark duplicates.
3. Create one batch_id.
4. Load `mock_data/demo_jobs.json` and `mock_data/messy_social_posts.json`.
5. Process all mock jobs through Plan 3 job processing services.
6. Return the standard ingestion response.
```

This endpoint must reuse `demo_loader.py`; it must not duplicate seed script logic.
The reset helper used by `reset_existing_demo = true` must be the same safe reset path used by `seed_demo.py --reset`: delete only mock-owned `applications`, mock Qdrant vectors, mock `job_posts`, and the deterministic demo role profile only when no non-mock jobs still reference it and it is not the `preserve_role_profile_id` for the current mock-load request.

### Mock Data Normalization Contract

Mock/demo JSON must be converted into the same `JobAgentState` shape consumed by Plan 3. `demo_loader.py` owns this adapter; routes and `seed_demo.py` must not hand-roll separate mock persistence payloads.

Each mock JSON item must include enough structured data to build a complete extraction state without calling Tavily, URL fetching, trafilatura, or the LLM:

```json
{
  "title": "AI Engineer Intern",
  "company": "ABC AI Lab",
  "location": "Ha Noi",
  "work_mode": "hybrid",
  "level": "intern",
  "employment_type": "internship",
  "salary": null,
  "responsibilities": "...",
  "requirements": "...",
  "skills": ["python", "rag", "langchain", "fastapi", "qdrant"],
  "raw_text": "Original mock JD or social post text",
  "source_url": null,
  "jd_status": "full_jd",
  "parse_status": "success",
  "extraction_status": "success",
  "extraction_notes": "demo fixture",
  "input_tokens": 0,
  "output_tokens": 0,
  "estimated_cost_usd": 0.0,
  "extraction_time_ms": 0
}
```

Adapter rules:

```text
1. Generate one batch_id per mock-load/seed run and pass it into every mock state.
2. Use the requested or generated role_profile_id for every mock state.
3. Set input_source = "mock" and extracted_job.source_platform = "mock".
4. Use raw_text as clean_text for demo fixtures after normalizing whitespace and applying MAX_CLEAN_TEXT_CHARS.
5. Compute raw_content_hash from the normalized clean_text.
6. Populate extracted_job with all JobPostExtract default fields, including unknown/default values where optional mock JSON fields are absent.
7. Set should_score_similarity = true only for full_jd and partial_jd.
8. Set embedding/score fields to null before calling Plan 3 processing.
9. Put messy social posts into contact_for_jd, no_jd, or partial_jd according to fixture content; do not mark inbox/DM-only posts as scorable.
10. Validate jd_status, parse_status, extraction_status, input_source, and source_platform against Plan 1 shared constants.
```

`seed_demo.py` and `/api/jobs/mock-load` must call this adapter, then call `job_processing_service.process_extraction_state(...)` for each produced state. They must not insert `job_posts` directly, recompute scores, bypass deduplication, or upsert Qdrant points outside Plan 3 services.

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

Routes must return HTTP 400 for invalid transitions surfaced by Plan 3 services.
Status transition validation itself is owned by Plan 3 `job_processing_service.py`. Route handlers must call the service method, catch `InvalidStatusTransition` or the equivalent service-domain error, and convert it to HTTP 400 with a clear response message.

Only `POST /api/jobs/{id}/reject` performs review rejection:

```text
pending_review -> ignored
```

Manual `PATCH /api/jobs/{id}/status` must not set `ignored`.

`POST /api/jobs/{id}/approve`

- Call `job_processing_service.approve_job(job_id)`.
- Return the updated job row after the service validates `pending_review -> saved`, updates SQLite, and updates Qdrant payload status to `saved` if the job has a vector.

`POST /api/jobs/{id}/reject`

- Call `job_processing_service.reject_job(job_id)`.
- Return the updated job row after the service validates `pending_review -> ignored`, updates SQLite, and deletes the Qdrant point if it exists.

`PATCH /api/jobs/{id}/status`

Request:

```json
{
  "status": "applied"
}
```

- Update SQLite status through Plan 3 service methods.
- The `PATCH /api/jobs/{id}/status` endpoint must call Plan 3 service methods so `job_posts.status` is updated and the `applications` row is created or updated when changing status to a tracked state (`applied`, `interview`, `rejected`, or `offer`).
- Use Plan 3 status sync behavior through service calls only:
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
The files must follow the Mock Data Normalization Contract above. Tests must load the actual JSON fixtures and validate that every item can be converted to a complete Plan 3-compatible `JobAgentState`.

### Demo Offline Expectations

Demo mode has two supported states:

```text
Seed generation mode:
- Requires local Qdrant running.
- Requires OpenAI embedding access unless the implementation explicitly enables a deterministic fake embedding mode for tests/offline rehearsal.
- Does not require Tavily or internet job search because fixtures are local JSON.
- Does not call the LLM, URL fetching, or trafilatura because mock fixtures already contain structured extraction fields.

Post-seed demo mode:
- Must work without Tavily, public internet search, browser scraping, manual copy-paste, or LLM extraction calls.
- Uses the already persisted SQLite rows and local Qdrant vectors created by seed generation.
- Still requires the local backend, local SQLite file, and local Qdrant service.
```

If a fully offline first-time seed is required, Plan 4 must add an explicit deterministic seed mode, such as `--offline-fixtures`, that uses local fake embeddings or precomputed fixture vectors with the configured `EMBEDDING_DIMENSION`. Do not imply first-time offline seeding works unless that deterministic path is implemented and tested.

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
- Load mock JSON fixtures through `demo_loader.py`.
- Convert each fixture into a Plan 3-compatible `JobAgentState`.
- Process each state through Plan 3 `job_processing_service.process_extraction_state(...)`.
- Let Plan 3 insert SQLite rows, build `embedding_text`, score scorable jobs, and upsert local Qdrant vectors.
- Print demo summary.

`--reset` must delete only demo/mock-owned data.
Do not use any non-existent columns (like `is_demo` or similar) to filter mock data. Filter SQLite `job_posts` and Qdrant vectors where `source_platform = 'mock'`.
Do not wipe manually entered or Tavily-created jobs.
Qdrant reset must delete only matching demo vectors.
Delete the demo role profile only if it matches the deterministic demo profile name, has no remaining non-mock jobs referencing it, and is not explicitly preserved by the caller. `seed_demo.py --reset` may omit `preserve_role_profile_id` because it recreates the deterministic demo role after reset. `/api/jobs/mock-load` must pass the request `role_profile_id` as `preserve_role_profile_id` so reset cannot delete the active profile before inserting the new mock batch.

Demo reset order:

```text
1. Collect mock job IDs from `job_posts` where `source_platform = 'mock'`.
2. Delete `applications` rows whose `job_post_id` is in that mock job ID set, unless Plan 1 explicitly implemented and verified `ON DELETE CASCADE`.
3. Delete matching mock Qdrant vectors.
4. Delete matching mock `job_posts`.
5. Delete the deterministic demo role profile only if no non-mock jobs still reference it and it is not `preserve_role_profile_id`.
```

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
- [ ] Ensure API schemas import or test against Plan 1 shared constants instead of maintaining divergent executable status/source enums.
- [ ] Define stable request/response schemas for all endpoints.
- [ ] Create `backend/scripts/export_api_contract.py`.
- [ ] Generate `shared/api-contract.json` from backend constants, Plan 3 allowed status transitions, endpoint metadata, and Pydantic API response schemas.
- [ ] Add a stale-contract test/check that fails when `shared/api-contract.json` does not match current backend constants/schemas.
- [ ] Implement `routes_role_profiles.py`.
- [ ] Implement `routes_jobs.py`.
- [ ] Implement `routes_batches.py`.
- [ ] Register all routers in `backend/app/main.py` under `/api`.
- [ ] Call the Plan 3 Qdrant initialization helper from FastAPI startup.
- [ ] Add local CORS middleware for `http://localhost:5173`.
- [ ] Implement `search_service.py` with Tavily integration and `MAX_URLS_PER_BATCH`.
- [ ] Ensure `/api/jobs/parse-text` reuses Plan 2 extraction and Plan 3 persistence pipeline.
- [ ] Ensure `/api/jobs/parse-url` reuses Plan 2 URL cleaning and Plan 3 persistence pipeline.
- [ ] Ensure `/api/jobs/search` uses Tavily then reuses the same URL parsing pipeline with `input_source = "tavily"`.
- [ ] Ensure `/api/jobs/search` remains synchronous and request-scoped for MVP, with no background queues or worker infrastructure.
- [ ] Ensure ingestion endpoints return the standard ingestion response.
- [ ] Ensure ingestion responses fetch full `Job` DTOs for Plan 3 `job_ids`.
- [ ] Ensure all route handlers call Plan 3 service methods instead of duplicating business logic.
- [ ] Ensure `/api/jobs/mock-load` loads mock files and reuses Plan 3 scoring/persistence/Qdrant behavior.
- [ ] Implement `demo_loader.py` mock JSON validation and conversion to complete Plan 3-compatible `JobAgentState` objects.
- [ ] Ensure mock-load and seed_demo call the same mock-to-state adapter before invoking Plan 3 processing.
- [ ] Ensure `/api/jobs/mock-load` with `reset_existing_demo = true` runs the same safe demo reset helper as `seed_demo.py --reset`.
- [ ] Ensure `/api/jobs/mock-load` passes `preserve_role_profile_id = request.role_profile_id` into the demo reset helper.
- [ ] Ensure `/api/jobs/mock-load` with `reset_existing_demo = false` does not delete existing mock data and relies on Plan 3 deduplication.
- [ ] Implement review queue and dashboard queries with duplicate exclusion.
- [ ] Add `status=tracked` support to `GET /api/jobs`.
- [ ] Implement approve, reject, and manual status update routes using Plan 3 status sync helpers.
- [ ] Convert Plan 3 invalid status transition service errors into HTTP 400 responses without duplicating transition logic.
- [ ] Ensure `PATCH /api/jobs/{id}/status` cannot set `ignored`.
- [ ] Implement batch summary aggregation from `job_posts`.
- [ ] Create `demo_loader.py`.
- [ ] Create `backend/scripts/seed_demo.py`.
- [ ] Ensure mock-load and seed_demo share `demo_loader.py`.
- [ ] Ensure `--reset` only clears demo/mock data.
- [ ] Document and test seeded-demo offline behavior: post-seed UI runs without Tavily/LLM/search access; first-time seed requires Qdrant and embeddings unless deterministic fake/precomputed embeddings are explicitly enabled.
- [ ] Ensure `--reset` deletes dependent `applications` rows for mock jobs before deleting mock `job_posts`, unless cascading deletes are explicitly implemented and verified.
- [ ] Create `mock_data/demo_jobs.json`.
- [ ] Create `mock_data/messy_social_posts.json`.
- [ ] Add route tests with mocked LLM and Qdrant.
- [ ] Add `backend/tests/test_api_contract_export.py`.
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
docker compose up -d qdrant
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

API contract export verification:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/export_api_contract.py
cd ..
Test-Path shared/api-contract.json
```

Expected:

```text
True
```

Stale-contract check:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_api_contract_export.py
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
- Search runs synchronously in the request and does not create queue, worker, cron, or background-job tables.
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
- Mock-load converts every fixture into a complete `JobAgentState` with `input_source = mock`, `source_platform = mock`, `raw_content_hash`, fallback score fields, and `JobPostExtract` default fields before Plan 3 processing.
- Mock-load with `reset_existing_demo = true` deletes only mock-owned data through the shared demo reset helper before loading new mock jobs.
- Mock-load with `reset_existing_demo = true` does not delete the request `role_profile_id`, even if that profile matches the deterministic demo profile name.
- Mock-load with `reset_existing_demo = false` does not delete existing mock rows and lets Plan 3 deduplication handle duplicates.
- seed_demo --reset does not delete non-mock jobs.
- seed_demo --reset succeeds after a mock job has been approved/applied and has an `applications` row.
- seed_demo --reset may delete and recreate the deterministic demo profile, but mock-load reset must preserve the caller's active profile.
- seed_demo and mock-load share the same mock-to-state adapter and neither path inserts directly into `job_posts` or calls Qdrant outside Plan 3 services.
- Actual mock JSON fixtures validate against the Mock Data Normalization Contract.
- Ingestion responses populate `jobs` by loading rows for Plan 3 `job_ids`.
- Ingestion `warnings` are returned as ingestion-level messages and persisted job cards use `error_reason`.
- Batch summary sums tokens, cost, failure count, and parsed jobs from `job_posts`.
- Batch summary returns 404 for unknown batch_id.
- API responses do not contain API keys or env secrets.
- FastAPI startup calls the Plan 3 Qdrant initialization helper and does not duplicate Qdrant collection or payload-index logic inside routes.
- `python scripts/export_api_contract.py` writes `shared/api-contract.json` from backend constants, Plan 3 transitions, endpoint metadata, and API schema JSON.
- The contract stale-check test fails if backend constants, transitions, or response schemas change without regenerating the artifact.
- Post-seed demo mode works without Tavily, LLM extraction, URL fetching, or manual paste; first-time seed requirements are explicit and tested.

Manual verification:

- Confirm API responses never include API keys.
- Confirm LinkedIn/Facebook authenticated scraping is absent.
- Confirm no Celery/Redis worker is introduced.
- Confirm no background search tables, queue configuration, cron setup, or worker process is introduced.
- Confirm bad extraction does not crash a batch.

## 10. Handoff Notes for Phase 5

Plan 5 consumes:

- Running FastAPI backend at `http://localhost:8000`.
- Role profile endpoints.
- Job parse, search, mock-load, review, dashboard, detail, approve, reject, status, and batch summary endpoints.
- Shared API response schemas from `backend/app/api/schemas.py`.
- Exported frontend contract artifact at `shared/api-contract.json`, generated by `backend/scripts/export_api_contract.py` from backend constants, Plan 3 allowed transitions, endpoint metadata, and API response schemas.
- Standard ingestion response shape with `batch_id`, counts, full `jobs`, and ingestion-level `warnings`.
- `GET /api/jobs?status=tracked` for saved/applied/interview/rejected/offer dashboard views.
- Demo fixture files that can be loaded without Tavily, browser scraping, or manual copy-paste. Scoring and Qdrant upsert still go through Plan 3's configured embedding and Qdrant services; route and seed tests must mock those services where external API access is not available.
- Clear demo offline contract: after seed data exists, the UI/backend demo must not depend on Tavily, public internet search, LLM extraction, URL fetching, or manual paste; first-time seeding requires local Qdrant and embedding access unless deterministic fake/precomputed embeddings are implemented.
- Demo fixtures that conform to the Mock Data Normalization Contract and are processed through the same Plan 3 pipeline as real extraction states.
- Shared demo reset behavior for both `/api/jobs/mock-load` with `reset_existing_demo = true` and `python scripts/seed_demo.py --reset`.
- Warning messages for URL pages that need manual text input.
- Persisted job-card errors through `Job.error_reason`; `warnings` are transient ingestion-result messages.
- Score fields and score component fields for UI display.

Plan 5 must:

- Build the React dashboard against these API contracts.
- Load or validate against `shared/api-contract.json` for status/source unions, endpoint shapes, key response schemas, and allowed status transitions.
- Show review queue, saved jobs, score breakdown, and metrics from the backend.
- Use approve/reject/status endpoints rather than mutating local state only.
- Keep API keys on the backend.
- Save the returned `activeBatchId` in localStorage/sessionStorage so that the metrics aggregation does not reset when page reloads or tabs toggle.
- Synchronize `activeBatchId` lifecycle with profile changes by loading that profile's stored localStorage/sessionStorage key or resetting the metrics view when no key exists. Plan 4 does not expose a "latest batch" endpoint in the MVP.
- Add focused frontend build, typecheck, and interaction verification steps without changing backend API contracts.

Hard rules for later phases:

- Frontend must not duplicate scoring formulas.
- Frontend must not call OpenAI, Tavily, or Qdrant directly.
- Frontend must treat backend API responses as the source of truth.
- Verify that no frontend `.env`, `frontend/.env.example`, or `frontend/job-agent-ui/.env.example` exists. Only load settings via root configuration scripts if required.
- Do not maintain frontend status/source unions or `StatusSelect` transition options without a contract test against `shared/api-contract.json`.
