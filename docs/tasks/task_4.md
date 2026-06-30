# Plan 4 - FastAPI Routes, Search, and Demo Seeding Execution Tasks

## Purpose

Expose the completed Phase 1 through Phase 3 backend pipeline through FastAPI routes, add a backend-owned API contract export, and add demo-mode mock loading and seeding. This phase turns the existing services into a complete backend-only MVP workflow that can run before the React frontend is implemented.

This task file is planning-only. It does not implement runtime code, product tests, migrations, frontend UI, or configuration changes.

## Authoritative Source

Source precedence for execution:

1. `docs/plans/Master_Plan.md` is the architecture and MVP source of truth.
2. `docs/plans/Plan_4.md` defines the approved Phase 4 boundary and detailed API, search, and demo-seeding contracts where it does not conflict with the master plan.
3. `README.md` records the current project state after Phase 3 and must be treated as the implementation baseline.

Comparison result:

- No blocking architecture conflict was found between the master plan and Plan 4.
- The master endpoint table says `/api/jobs/search` starts public web search, while Plan 4 requires MVP search to complete synchronously inside the request. This is aligned with the master plan's explicit out-of-scope rule against Celery, Redis, and distributed queues.
- The master demo pseudocode is illustrative. Plan 4 narrows the implementation so demo seeding and mock-load reuse the existing Phase 3 processing services instead of bypassing deduplication, scoring, SQLite-first persistence, or Qdrant sync.
- Plan 4's generated API contract is not spelled out in the master endpoint table, but it is consistent with the master directory structure containing `shared/api-contract.json` and with the Phase 5 handoff needs.
- The README confirms the current project has Phase 3 services, constants, database models, extraction entrypoints, Qdrant sync, and status mutation services. It also confirms API route modules, `search_service.py`, `demo_loader.py`, seed scripts, mock data, and `shared/api-contract.json` are not part of the current state and are the required Phase 4 work.
- Plan 4 explicitly forbids database schema, scoring formula, dedup policy, React UI, browser rendering, queue infrastructure, authentication, cover letters, and auto-apply changes.

## Source Section Index

- `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack` -> approved FastAPI, Tavily, seed script, mock data, SQLite, and Qdrant stack.
- `docs/plans/Master_Plan.md` > `## 3. MVP Scope` -> required role profile, search, URL, raw text, demo mode, review, and status workflows.
- `docs/plans/Master_Plan.md` > `## 4. Architecture` -> SQLite-first persistence and Qdrant-derived index rule.
- `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking` -> required `JobAgentState` fields for route-to-service handoff.
- `docs/plans/Master_Plan.md` > `## 5. Demo Mode / Mock Seeding` -> demo dataset, seed script, and expected output.
- `docs/plans/Master_Plan.md` > `## 6. Input Sources` -> approved input sources and crawler non-goal.
- `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners` -> URL parsing fallback and warning behavior.
- `docs/plans/Master_Plan.md` > `## 15. Cost & Performance Metrics Panel` -> batch summary metrics from stored fields.
- `docs/plans/Master_Plan.md` > `## 19. Human-in-the-Loop Rules` -> approve, reject, and manual status ownership.
- `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes` -> review and dashboard query requirements.
- `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema` -> Qdrant startup, payload indexes, and status sync behavior.
- `docs/plans/Master_Plan.md` > `## 26. API Endpoints` -> required API endpoint list.
- `docs/plans/Master_Plan.md` > `## 27. URL Parsing Security Note` -> MVP URL limits and production SSRF note.
- `docs/plans/Master_Plan.md` > `## 28. Input Size and Retry Limits` -> search, raw text, clean text, retry, timeout, and response-size limits.
- `docs/plans/Master_Plan.md` > `## 30. Project Directory Structure` -> approved Phase 4 file locations.
- `docs/plans/Master_Plan.md` > `## 31. Environment Setup` -> approved Tavily, httpx, trafilatura, FastAPI, and test dependencies.
- `docs/plans/Master_Plan.md` > `## 32. Single Root .env` -> backend-only secret settings and `TAVILY_API_KEY`.
- `docs/plans/Master_Plan.md` > `## 34. Demo Script Pseudocode` -> seed command shape and demo profile intent.
- `docs/plans/Master_Plan.md` > `## 35. Implementation Checklist` > `### Demo Readiness` / `### Search and Parsing` / `### Qdrant Local` -> Phase 4 MVP completion items.
- `docs/plans/Master_Plan.md` > `## 36. Final MVP Definition` -> backend capabilities required before final UI completion.
- `docs/plans/Plan_4.md` > `## 1. Objective` -> Phase 4 outcome.
- `docs/plans/Plan_4.md` > `## 3. Prerequisites from Prior Phases` -> required Phase 1 through Phase 3 foundation.
- `docs/plans/Plan_4.md` > `## 4. Scope` and `## 5. Out of Scope` -> exact phase boundary.
- `docs/plans/Plan_4.md` > `## 6. Target Directory Structure` -> route, service, script, fixture, test, and shared-contract file locations.
- `docs/plans/Plan_4.md` > `## 7. Technical Specifications` -> detailed API, CORS, service-boundary, search, demo, status, batch, and seed contracts.
- `docs/plans/Plan_4.md` > `## 8. Implementation Steps` -> required implementation inventory.
- `docs/plans/Plan_4.md` > `## 9. Verification & Testing Plan` -> automated and manual checks.
- `docs/plans/Plan_4.md` > `## 10. Handoff Notes for Phase 5` -> API and demo outputs consumed by React.
- `README.md` > `## Directory Structure` -> current Phase 3 file layout and missing Phase 4 modules.
- `README.md` > `## Setup and Running Instructions` -> established backend setup and verification workflow.
- `README.md` > `## Extraction Architecture & Workflows (Phase 2)` -> existing extraction service entrypoints and no-side-effect boundary.
- `README.md` > `## Scoring & Embedding Foundations (Phase 3 - Batch 01)` -> existing scoring and embedding services.
- `README.md` > `## Deduplication & SQLite-First Persistence (Phase 3 - Batch 02)` -> existing dedup and persistence pipeline.
- `README.md` > `## Qdrant Sync & Status Mutation Services (Phase 3 - Batch 03)` -> existing Qdrant and status mutation service contracts.
- `README.md` > `## Phase 3 Verification & Handoff Boundary (Batch 04)` -> confirmed Phase 4 handoff symbols and current backend state.

## Approved Architecture Summary

- FastAPI route handlers are HTTP adapters only. They own request validation, response formatting, dependency injection, and HTTP error conversion.
- Plan 2 extraction services own raw text and URL extraction. Route handlers must not duplicate parsing logic.
- Plan 3 processing services own scoring, deduplication, SQLite persistence, Qdrant upsert/sync, approve/reject/status transitions, and application-row updates. Route handlers must call these services instead of reimplementing business logic.
- API request and response schemas live in `backend/app/api/schemas.py` and must import or be tested against shared backend constants.
- The frontend-facing API contract is generated from backend constants, Plan 3 status transitions, endpoint metadata, and Pydantic JSON Schema. `shared/api-contract.json` must not be a hand-maintained second source of truth.
- Search is synchronous and request-scoped for MVP. No Celery, Redis, cron, durable worker, background queue, or search-run table may be added.
- Demo fixtures are local JSON and are converted by `demo_loader.py` into the same `JobAgentState` shape consumed by Plan 3.
- `/api/jobs/mock-load` and `backend/scripts/seed_demo.py` share the same demo adapter and safe reset helper.
- Demo reset deletes only mock-owned SQLite rows, dependent mock-owned application rows, matching mock Qdrant vectors, and the deterministic demo profile only when safe.
- Qdrant collection and payload-index initialization is called during FastAPI startup through the existing Phase 3 Qdrant service owner.
- CORS is local-development only for `http://localhost:5173` in this phase.

## Global Implementation Rules

- Before adding any helper, utility, adapter, serializer, or service method, search the codebase with `grep` for equivalent logic and reuse or safely extend the existing owner.
- Do not duplicate status/source constants, status transition logic, score formulas, dedup decisions, Qdrant operations, URL parsing, mock fixture conversion, or demo reset behavior.
- Keep modules focused. Route modules should stay as thin HTTP boundaries; shared conversion logic belongs in a small existing or clearly owned service only when repeated behavior justifies it.
- Do not change database schema, ORM models, migrations, scoring formulas, dedup policy, or Phase 3 status transition semantics in Plan 4. If a required field is missing, stop and report the mismatch.
- Do not implement React UI, frontend route screens, frontend `.env` files, or frontend status unions in this phase.
- Do not add authenticated LinkedIn/Facebook scraping, Playwright/browser rendering, cover letters, auto-apply, multi-user auth, organizations, or public config endpoints for secrets.
- Do not add Celery, Redis, durable queue tables, worker processes, cron jobs, or persistent background task infrastructure.
- Never log, print, commit, return, or expose API keys, `.env` values, or backend-only configuration values.
- Keep generated JSON stable and deterministic where required so stale-contract tests can detect drift.
- Automated tests must mock LLM, Tavily, OpenAI embedding, and Qdrant boundaries unless a validation is explicitly marked as manual/live.

## Execution Agent Coding Style Requirements

- Write clean, idiomatic, readable Python.
- Use descriptive names for modules, functions, variables, components, settings, schemas, services, and tests.
- Keep functions, route handlers, services, and modules focused on one clear responsibility.
- Prefer simple, explicit control flow over clever abstractions.
- Follow the established FastAPI, Pydantic v2, SQLAlchemy async, LangGraph, httpx, trafilatura, Tavily, and Qdrant client conventions already approved by the plans.
- Use clear typing where Python supports it.
- Avoid `Any`, broad exception handling, hidden global state, and hardcoded configuration values unless the source plan explicitly requires them.
- Add comments only for non-obvious decisions or behavior, such as the required URL parsing production SSRF note.
- Keep frontend code free of backend-only secrets and backend-only configuration names.
- Avoid adding formatters, linters, frameworks, or architecture changes outside the source plan unless already present or explicitly requested.

## Batch Map

| Batch | Outcome | Depends On |
|---|---|---|
| Batch01 | API schemas and generated API contract foundation | Phase 3 handoff |
| Batch02 | Core FastAPI routes, status routes, batch summary, CORS, and startup wiring | Batch01 |
| Batch03 | Manual text, manual URL, and Tavily search ingestion routes | Batch01, Batch02 |
| Batch04 | Demo loader, mock fixtures, seed script, and mock-load endpoint | Batch01, Batch02, Batch03 |
| Batch05 | Focused tests, stale-contract verification, demo tests, and phase-boundary validation | Batch01, Batch02, Batch03, Batch04 |

## Mandatory Batch01 - API Schema and Contract Foundation

### Goal

Create the backend API schema layer and generated frontend contract artifact without exposing new runtime behavior yet.

### Why this batch exists

Routes and the future React frontend need one backend-owned contract. Building schemas and export generation first prevents route modules, frontend code, and tests from inventing divergent payload shapes or status unions.

### Inputs / Dependencies

- Phase 3 handoff symbols from `README.md`.
- Existing constants in `backend/app/core/constants.py`.
- Existing status transitions in `backend/app/services/job_processing_service.py`.
- Existing Pydantic v2 and FastAPI dependencies.

### Tasks

- [x] (01A): Verify Phase 4 prerequisites and service ownership boundaries
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 3. Prerequisites from Prior Phases`
    - `docs/plans/Plan_4.md` > `## 5. Out of Scope`
    - `README.md` > `## Phase 3 Verification & Handoff Boundary (Batch 04)`
  - Source Requirements:
    - Plan 1 app, settings, database, models, and shared constants must exist.
    - Plan 2 extraction graph and URL/text parsing services must exist.
    - Plan 3 scoring, deduplication, persistence, Qdrant sync, and status mutation services must exist.
    - Phase 4 must not change database schema, scoring formulas, or dedup policy.
  - Details: Confirm the execution baseline before adding routes or demo code.
  - Dependencies: None.
  - User Action: None.
  - Agent Work: Inspect existing constants, settings, models, extraction services, processing services, Qdrant service, and app bootstrap.
  - Specific Steps:
    1. Search for existing API schemas, serializers, route helpers, and endpoint metadata before adding new ones.
    2. Verify `backend/app/core/constants.py` exposes the status and source constants needed by API schemas.
    3. Verify `backend/app/services/extraction_service.py` exposes raw-text and URL parsing entrypoints.
    4. Verify `backend/app/services/job_processing_service.py` exposes processing, approve, reject, update-status, result, and transition symbols.
    5. Verify `backend/app/services/qdrant_service.py` exposes an initialization helper or service method suitable for startup.
    6. Stop and report a phase-boundary mismatch if any required Phase 3 handoff symbol is absent.
  - Output: Confirmed prerequisite checklist or explicit blocker report.
  - Acceptance: Execution can proceed without schema, scoring, dedup, or service-boundary changes.
  - Validation: Import checks for constants, extraction services, processing services, and Qdrant initialization owner.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only if the user must approve a separate earlier-phase repair.
  - Files: Existing files only; no source edits expected for this task.

- [x] (01B): Create backend API request and response schemas
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Common API Response Shapes`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### API Schema Ownership`
    - `docs/plans/Master_Plan.md` > `## 22. Table: job_posts`
    - `docs/plans/Master_Plan.md` > `## 26. API Endpoints`
  - Source Requirements:
    - Define all request and response Pydantic models in `backend/app/api/schemas.py`.
    - Job responses must include all fields needed by Plan 5, including nullable score fields as `null`.
    - Ingestion responses must include batch counts, full `jobs`, and transient `warnings`.
    - Schemas must import or be tested against Plan 1 shared constants.
  - Details: Add a single schema owner for route payloads and generated JSON Schema.
  - Dependencies: (01A).
  - User Action: None.
  - Agent Work: Create API schemas for role profiles, ingestion requests/responses, jobs, status updates, and batch summaries.
  - Specific Steps:
    1. Search existing Pydantic models before adding schema classes.
    2. Define request models for role profile creation, search, parse URL, parse text, mock load, and status update.
    3. Define response models for role profiles, job rows, ingestion results, status mutations, and batch summaries.
    4. Use shared constants for allowed statuses and sources, or add focused tests that fail if schema literals drift.
    5. Include every persisted job-card field required by Plan 4 without adding non-master database fields.
    6. Keep `warnings` on ingestion responses only; persisted job cards expose `error_reason`.
  - Output: `backend/app/api/schemas.py`.
  - Acceptance: Pydantic models are importable, typed, and cover every required Phase 4 endpoint payload.
  - Validation: Import smoke check and schema drift tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/schemas.py`.

- [x] (01C): Generate the frontend API contract from backend owners
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### API Contract Export`
    - `docs/plans/Plan_4.md` > `## 10. Handoff Notes for Phase 5`
    - `docs/plans/Master_Plan.md` > `## 30. Project Directory Structure`
  - Source Requirements:
    - `backend/scripts/export_api_contract.py` must generate `shared/api-contract.json`.
    - Export status/source values from backend constants and allowed transitions from the Plan 3 service owner.
    - Export endpoint metadata and Pydantic-generated JSON Schema objects.
    - Write stable, sorted JSON from the repository root.
  - Details: Add a generated contract artifact so Phase 5 does not maintain duplicated frontend unions or endpoint metadata.
  - Dependencies: (01B).
  - User Action: None.
  - Agent Work: Implement the export script and generate the initial `shared/api-contract.json`.
  - Specific Steps:
    1. Search for existing contract scripts or shared artifacts before adding a new script.
    2. Import status/source constants from `backend/app/core/constants.py`.
    3. Import `ALLOWED_STATUS_TRANSITIONS` from `backend/app/services/job_processing_service.py`.
    4. Import API response schemas from `backend/app/api/schemas.py` and call the Pydantic v2 JSON Schema API.
    5. Include endpoint metadata for every Phase 4 endpoint.
    6. Resolve paths so running `python scripts/export_api_contract.py` from `backend/` writes `../shared/api-contract.json`.
    7. Write sorted, stable, indented JSON.
  - Output: `backend/scripts/export_api_contract.py`, `shared/api-contract.json`.
  - Acceptance: Running the export script produces the expected contract file from backend-owned sources.
  - Validation: `cd backend; python scripts/export_api_contract.py`; stale-contract test in Batch05.
  - Blocked Condition: None.
  - Files: `backend/scripts/export_api_contract.py`, `shared/api-contract.json`.

### Files or Modules Likely Created or Updated

- `backend/app/api/schemas.py`
- `backend/scripts/export_api_contract.py`
- `shared/api-contract.json`
- `backend/tests/test_api_contract_export.py` in Batch05

### Required Outputs / Artifacts

- Importable API schema module.
- Generated API contract script.
- Generated `shared/api-contract.json`.
- Prerequisite verification result.

### Acceptance Criteria

- API schemas have one backend owner and cover every required endpoint payload.
- Contract generation uses backend constants, Plan 3 transitions, endpoint metadata, and Pydantic JSON Schema.
- No hand-maintained frontend source of truth is introduced.

### Required Tests or Validations

- `cd backend; python scripts/export_api_contract.py`
- Batch05 stale-contract test.
- Import smoke checks for schemas and contract script.

### Explicit Non-Goals

- Do not implement route handlers in this batch.
- Do not add frontend code.
- Do not alter database models, scoring, deduplication, or status transition logic.

## Mandatory Batch02 - Core FastAPI Routes and App Wiring

### Goal

Expose role profile, review, dashboard, job detail, status mutation, and batch summary endpoints through FastAPI while preserving the Phase 3 service boundary.

### Why this batch exists

These routes provide the stable HTTP surface the frontend will consume. They must be thin adapters over existing database and processing services so business rules stay in the established owners.

### Inputs / Dependencies

- Batch01 API schemas.
- Existing Phase 1 database session/models.
- Existing Phase 3 status mutation and Qdrant initialization services.
- Existing FastAPI app bootstrap in `backend/app/main.py`.

### Tasks

- [ ] (02A): Implement role profile create and list routes
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Role Profile Routes`
    - `docs/plans/Master_Plan.md` > `## 3. MVP Scope`
    - `docs/plans/Master_Plan.md` > `## 21. Table: role_profiles`
    - `README.md` > `## Directory Structure`
  - Source Requirements:
    - Implement `POST /api/role-profiles`.
    - Implement `GET /api/role-profiles`.
    - Create responses must include generated UUID `id`.
    - List responses must be sorted by `created_at DESC` or a consistent equivalent.
  - Details: Add the role profile route module using existing models/session patterns.
  - Dependencies: (01B).
  - User Action: None.
  - Agent Work: Create `backend/app/api/routes_role_profiles.py` and use shared schemas.
  - Specific Steps:
    1. Search for existing role profile persistence helpers before writing route-local database code.
    2. Add an API router for role profile endpoints.
    3. Validate request payloads with `RoleProfileCreateRequest`.
    4. Persist role profiles using the established async SQLAlchemy session dependency pattern.
    5. Serialize responses through `RoleProfileResponse`.
    6. Return list results in a deterministic newest-first order.
  - Output: Role profile route module.
  - Acceptance: Role profiles can be created and listed through the documented API shapes.
  - Validation: Focused route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/routes_role_profiles.py`, possibly `backend/app/api/__init__.py`.

- [ ] (02B): Implement review, dashboard, and job detail routes
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Review and Dashboard Queries`
    - `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes`
    - `docs/plans/Master_Plan.md` > `## 26. API Endpoints`
  - Source Requirements:
    - Implement `GET /api/jobs/review`.
    - Implement `GET /api/jobs`.
    - Implement `GET /api/jobs/{id}`.
    - Exclude duplicate rows where `duplicate_of_job_id IS NULL`.
    - Support `status=tracked` as saved/applied/interview/rejected/offer.
  - Details: Add read-only job query endpoints using stored SQLite fields only.
  - Dependencies: (01B), (02A).
  - User Action: None.
  - Agent Work: Create or extend `backend/app/api/routes_jobs.py`.
  - Specific Steps:
    1. Search for existing job query helpers before adding route-local query code.
    2. Implement review queue filtering by `role_profile_id`, `pending_review`, duplicate exclusion, and score/discovery ordering.
    3. Implement dashboard filtering by `role_profile_id`, requested status, tracked-status expansion, duplicate exclusion, and score ordering.
    4. Enforce default and max limits from Plan 4.
    5. Implement job detail lookup by `id` and return HTTP 404 when absent.
    6. Serialize all rows through the shared job response schema without omitting nullable score fields.
  - Output: Review, dashboard, and detail endpoints.
  - Acceptance: Query endpoints return persisted job fields and do not recompute scores or duplicate decisions.
  - Validation: Focused route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/routes_jobs.py`.

- [ ] (02C): Implement approve, reject, and manual status routes
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Human-in-the-Loop Status Routes`
    - `docs/plans/Master_Plan.md` > `## 19. Human-in-the-Loop Rules`
    - `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema` > `### SQLite -> Qdrant Status Sync Rules`
    - `README.md` > `## Qdrant Sync & Status Mutation Services (Phase 3 - Batch 03)`
  - Source Requirements:
    - Implement `POST /api/jobs/{id}/approve`.
    - Implement `POST /api/jobs/{id}/reject`.
    - Implement `PATCH /api/jobs/{id}/status`.
    - Call Plan 3 service methods for all status mutations.
    - Convert invalid transition service errors to HTTP 400.
    - Manual status update must not set `ignored`.
  - Details: Expose human-in-the-loop actions without duplicating transition or Qdrant sync logic.
  - Dependencies: (01B), (02B).
  - User Action: None.
  - Agent Work: Extend `backend/app/api/routes_jobs.py` with status mutation endpoints.
  - Specific Steps:
    1. Search for existing status route or error conversion patterns before adding handlers.
    2. Call `approve_job(job_id)` for approve and return the updated job row.
    3. Call `reject_job(job_id)` for review rejection and return the updated job row.
    4. Reject `ignored` in manual status requests before calling the service.
    5. Call `update_job_status(job_id, status)` for tracked manual status changes.
    6. Catch `InvalidStatusTransition` or the established service-domain equivalent and convert it to HTTP 400.
    7. Do not update SQLite, applications, or Qdrant directly in route handlers.
  - Output: Status mutation endpoints.
  - Acceptance: HTTP routes preserve Plan 3 status semantics and Qdrant sync ownership.
  - Validation: Focused route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/routes_jobs.py`.

- [ ] (02D): Implement batch summary route
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Batch Summary`
    - `docs/plans/Master_Plan.md` > `## 15. Cost & Performance Metrics Panel`
    - `docs/plans/Master_Plan.md` > `## 26. API Endpoints`
  - Source Requirements:
    - Implement `GET /api/batches/{batch_id}/summary`.
    - Compute metrics from stored `job_posts` fields.
    - Return HTTP 404 when no rows exist for `batch_id`.
    - Avoid analytics tables and cron jobs.
  - Details: Add simple SQL aggregation for Phase 5 metrics.
  - Dependencies: (01B).
  - User Action: None.
  - Agent Work: Create `backend/app/api/routes_batches.py`.
  - Specific Steps:
    1. Search for existing batch summary or aggregation helpers before adding query code.
    2. Count total parsed jobs for the batch.
    3. Count scorable jobs using `should_score_similarity = true`.
    4. Count failed extractions using `extraction_status = "failed"`.
    5. Sum input/output tokens and estimated cost treating null as zero.
    6. Compute total tokens and average non-null extraction time.
    7. Return HTTP 404 when the batch has no job rows.
  - Output: Batch summary endpoint.
  - Acceptance: Metrics match stored per-job fields and require no new tables.
  - Validation: Focused route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/routes_batches.py`.

- [ ] (02E): Register routers, local CORS, and Qdrant startup initialization
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 4. Scope`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### CORS`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Service Boundary`
    - `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema`
  - Source Requirements:
    - Register route modules under `/api`.
    - Add local CORS middleware for `http://localhost:5173`.
    - Keep `allow_credentials = false`, `allow_methods = ["*"]`, and `allow_headers = ["*"]`.
    - Call Plan 3 Qdrant collection and payload-index initialization during startup.
    - Do not expose API keys or `.env` values.
  - Details: Wire the API surface into the existing FastAPI app without reimplementing Qdrant setup logic.
  - Dependencies: (02A), (02B), (02C), (02D).
  - User Action: None.
  - Agent Work: Update `backend/app/main.py` and package exports as needed.
  - Specific Steps:
    1. Search existing app startup and middleware patterns before editing `main.py`.
    2. Import and include role profile, jobs, and batches routers under `/api`.
    3. Add CORS middleware with only the approved local frontend origin.
    4. Call the existing Qdrant service initialization helper during startup.
    5. Keep database startup behavior already present in the app.
    6. Verify no route returns secrets or backend-only configuration.
  - Output: FastAPI app with registered Phase 4 API routes, CORS, and Qdrant startup init.
  - Acceptance: App imports successfully and exposes the registered routers without duplicating Qdrant setup.
  - Validation: Import smoke check and route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/main.py`, `backend/app/api/__init__.py`.

### Files or Modules Likely Created or Updated

- `backend/app/api/routes_role_profiles.py`
- `backend/app/api/routes_jobs.py`
- `backend/app/api/routes_batches.py`
- `backend/app/api/__init__.py`
- `backend/app/main.py`

### Required Outputs / Artifacts

- Role profile endpoints.
- Review, dashboard, detail, approve, reject, and status endpoints.
- Batch summary endpoint.
- Registered FastAPI routers under `/api`.
- Local CORS and startup Qdrant initialization.

### Acceptance Criteria

- Route handlers are thin HTTP adapters over existing services and database queries.
- Status transitions and Qdrant sync remain owned by Plan 3 services.
- Batch summary uses stored job fields and no analytics table.
- No secrets are exposed through API responses.

### Required Tests or Validations

- `cd backend; python -c "from app.main import app; print(app.title)"`
- Batch05 route tests for all core endpoints.
- Manual smoke test with `uvicorn app.main:app --reload --port 8000`.

### Explicit Non-Goals

- Do not implement ingestion endpoints in this batch except shared schema dependencies.
- Do not implement demo seeding or mock-load in this batch.
- Do not add frontend code or frontend contracts beyond the generated artifact from Batch01.

## Mandatory Batch03 - Manual and Search Ingestion Routes

### Goal

Expose manual raw text, manual public URL, and Tavily public search ingestion through FastAPI while reusing Plan 2 extraction and Plan 3 processing.

### Why this batch exists

These endpoints complete the live backend workflow for real and fallback inputs. They must preserve the existing extraction and persistence pipeline instead of adding route-local scoring, deduplication, or parsing branches.

### Inputs / Dependencies

- Batch01 API schemas and contract metadata.
- Batch02 route module and app wiring.
- Existing Plan 2 extraction service.
- Existing Plan 3 job processing service.
- Existing settings for Tavily and input limits.

### Tasks

- [ ] (03A): Implement standard ingestion response shaping and parse-text endpoint
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Parse Routes`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Common API Response Shapes`
    - `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking`
    - `README.md` > `## Extraction Architecture & Workflows (Phase 2)`
  - Source Requirements:
    - Implement `POST /api/jobs/parse-text`.
    - Create one batch ID per ingestion request.
    - Run Plan 2 extraction with `input_source = manual_text`.
    - Run Plan 3 processing and return the standard ingestion response.
    - If Plan 3 returns job IDs, fetch rows from SQLite and serialize them into `jobs`.
  - Details: Add a shared response-shaping path only if repeated ingestion endpoints need it.
  - Dependencies: (01B), (02B), (02E).
  - User Action: None.
  - Agent Work: Extend `backend/app/api/routes_jobs.py` with parse-text behavior.
  - Specific Steps:
    1. Search for existing processing result and job serialization helpers before adding a new adapter.
    2. Validate request payload through the shared parse-text schema.
    3. Generate a new UUID batch ID for the request.
    4. Call the existing raw-text extraction entrypoint with `role_profile_id`, `batch_id`, and `input_source = "manual_text"`.
    5. Pass the resulting state to the existing Plan 3 processing service.
    6. Build the standard ingestion response from service counts, service warnings, Qdrant sync state, and fetched job rows.
    7. Keep route logic free of score math, dedup decisions, and Qdrant operations.
  - Output: Parse-text endpoint and reusable ingestion response shaping if justified by duplication.
  - Acceptance: Raw text ingestion inserts visible pending-review jobs through the established pipeline.
  - Validation: Focused ingestion route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/routes_jobs.py`.

- [ ] (03B): Implement parse-url endpoint with MVP URL safety limits
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Parse Routes`
    - `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners`
    - `docs/plans/Master_Plan.md` > `## 27. URL Parsing Security Note`
    - `docs/plans/Master_Plan.md` > `## 28. Input Size and Retry Limits`
  - Source Requirements:
    - Implement `POST /api/jobs/parse-url`.
    - Validate only `http` and `https` URLs.
    - Respect request timeout and response-size limits through the existing URL extraction service.
    - Return a warning when parsing needs manual input.
    - Include the required production SSRF mitigation note in code.
  - Details: Expose controlled URL parsing without adding browser rendering or enterprise SSRF implementation.
  - Dependencies: (03A).
  - User Action: None.
  - Agent Work: Extend `backend/app/api/routes_jobs.py` with parse-url behavior.
  - Specific Steps:
    1. Search for existing URL validators and extraction entrypoints before adding new validation.
    2. Validate URL scheme at the API boundary.
    3. Add the required production note near the URL parsing route or validator.
    4. Generate one batch ID for the request.
    5. Call the existing URL extraction entrypoint with `input_source = "manual_url"`.
    6. Pass the resulting state to Plan 3 processing.
    7. Return standard ingestion counts, fetched jobs, and ingestion-level warnings.
    8. Do not add Playwright or custom HTML parsing beyond the existing trafilatura path.
  - Output: Parse-url endpoint.
  - Acceptance: URL ingestion handles low-content pages with safe warnings and persists appropriate records through Plan 3.
  - Validation: Focused ingestion route tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/api/routes_jobs.py`.

- [ ] (03C): Implement Tavily search service
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 4. Scope`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Search Route`
    - `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack`
    - `docs/plans/Master_Plan.md` > `## 6. Input Sources`
    - `docs/plans/Master_Plan.md` > `## 32. Single Root .env`
  - Source Requirements:
    - Add `backend/app/services/search_service.py` with Tavily integration.
    - Enforce `MAX_URLS_PER_BATCH`.
    - Use backend-only `TAVILY_API_KEY`.
    - Do not add authenticated LinkedIn/Facebook crawling.
  - Details: Isolate Tavily API calls behind a small mockable service boundary.
  - Dependencies: (01A).
  - User Action: Add a real `TAVILY_API_KEY` to the uncommitted root `.env` only for optional live search validation.
  - Agent Work: Create `backend/app/services/search_service.py`.
  - Specific Steps:
    1. Search for existing search or Tavily helpers before adding a service.
    2. Read Tavily credentials and limits from backend settings only.
    3. Clamp requested `max_urls` to `MAX_URLS_PER_BATCH`.
    4. Return normalized result URLs and safe metadata needed by the route.
    5. Raise or return safe service errors that routes can convert to HTTP 502.
    6. Keep the service free of persistence, extraction, score, dedup, or Qdrant logic.
  - Output: Mockable Tavily search service.
  - Acceptance: Search service can be mocked in tests and never exposes the Tavily key.
  - Validation: Focused search service and route tests in Batch05.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for explicitly requested live Tavily validation when a valid key is absent.
  - Files: `backend/app/services/search_service.py`.

- [ ] (03D): Implement search endpoint using parse-url pipeline
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Search Route`
    - `docs/plans/Master_Plan.md` > `## 3. MVP Scope`
    - `docs/plans/Master_Plan.md` > `## 26. API Endpoints`
  - Source Requirements:
    - Implement `POST /api/jobs/search`.
    - Create one batch ID per search request.
    - Call Tavily with max URLs clamped to `MAX_URLS_PER_BATCH`.
    - Reuse URL parsing and Plan 3 processing for each result URL.
    - Continue after individual URL parse failures.
    - Return HTTP 502 when Tavily fails before useful processing.
    - Do not add background queues or worker infrastructure.
  - Details: Implement MVP synchronous public web search as an HTTP request-scoped orchestration path.
  - Dependencies: (03B), (03C).
  - User Action: None for mocked automated validation; live validation requires `TAVILY_API_KEY`.
  - Agent Work: Extend `backend/app/api/routes_jobs.py` with search behavior.
  - Specific Steps:
    1. Validate request payload through the shared search schema.
    2. Generate one batch ID for the whole search request.
    3. Call `search_service.py` for public URLs.
    4. For each returned URL, call the same extraction and processing path used by parse-url with `input_source = "tavily"`.
    5. Accumulate inserted/skipped/Qdrant counts and warnings into the standard ingestion response.
    6. Continue processing remaining URLs if one URL fails after Tavily returns results.
    7. Convert Tavily service failure to HTTP 502 with a safe message when no partial processing has occurred.
    8. Do not add Celery, Redis, queues, workers, cron, or background search tables.
  - Output: Search endpoint.
  - Acceptance: Search returns one batch summary and job list for processed URLs without queue infrastructure.
  - Validation: Focused ingestion/search route tests in Batch05.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for explicitly requested live Tavily validation when a valid key is absent.
  - Files: `backend/app/api/routes_jobs.py`.

### Files or Modules Likely Created or Updated

- `backend/app/api/routes_jobs.py`
- `backend/app/services/search_service.py`
- `backend/app/core/config.py` only if required settings already planned in `.env.example` are missing and can be added without secret values
- `backend/tests/test_routes_jobs.py` in Batch05

### Required Outputs / Artifacts

- Parse-text endpoint.
- Parse-url endpoint.
- Tavily search service.
- Search endpoint.
- Standard ingestion response path.

### Acceptance Criteria

- All ingestion routes use Plan 2 extraction and Plan 3 processing.
- Ingestion warnings are transient response fields and persisted job errors come from `Job.error_reason`.
- Search is synchronous and request-scoped.
- API keys remain backend-only.

### Required Tests or Validations

- Route tests with mocked LLM/extraction, Tavily, Qdrant, and processing services.
- HTTP 502 test for Tavily failure.
- Tests for `MAX_URLS_PER_BATCH` clamping and continuing after one URL failure.

### Explicit Non-Goals

- Do not add authenticated crawling.
- Do not add browser rendering.
- Do not add queues or durable search-run infrastructure.
- Do not recompute scores or dedup decisions in routes.

## Mandatory Batch04 - Demo Loader, Fixtures, Seed Script, and Mock Load

### Goal

Add local demo fixtures and shared demo loading behavior so the backend can be seeded or mock-loaded through the same Plan 3 processing pipeline.

### Why this batch exists

The portfolio demo must not depend entirely on live internet search, JavaScript-heavy pages, or manual copy-paste. Local fixtures make the demo reliable while preserving the real scoring, persistence, deduplication, and Qdrant paths.

### Inputs / Dependencies

- Batch01 schemas.
- Batch03 standard ingestion response path.
- Existing Phase 3 processing service.
- Master-plan demo dataset composition.
- Existing SQLite and Qdrant local setup.

### Tasks

- [ ] (04A): Implement demo loader adapter and safe reset helper
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Mock Data Normalization Contract`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Mock Load Endpoint`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### seed_demo.py`
    - `docs/plans/Master_Plan.md` > `## 5. Demo Mode / Mock Seeding`
  - Source Requirements:
    - `demo_loader.py` owns mock JSON validation and conversion to complete Plan 3-compatible `JobAgentState` objects.
    - Mock conversion must set `input_source = "mock"` and `source_platform = "mock"`.
    - Mock conversion must normalize clean text, compute `raw_content_hash`, validate statuses/sources, and set score fields to null before Plan 3 processing.
    - Shared reset must delete only mock-owned data and matching Qdrant vectors.
  - Details: Create the single adapter and reset owner used by both seed script and mock-load route.
  - Dependencies: (01A), (03A).
  - User Action: None.
  - Agent Work: Create `backend/app/services/demo_loader.py`.
  - Specific Steps:
    1. Search for existing demo, fixture, reset, and state-conversion helpers before adding the module.
    2. Load and validate JSON fixture items against the mock data normalization contract.
    3. Convert every fixture to a complete `JobAgentState` with one supplied batch ID and role profile ID.
    4. Normalize whitespace and cap clean text with `MAX_CLEAN_TEXT_CHARS`.
    5. Compute `raw_content_hash` from normalized clean text.
    6. Validate `jd_status`, `parse_status`, `extraction_status`, `input_source`, and `source_platform` against shared constants.
    7. Implement a safe reset helper that deletes mock-owned application rows, matching Qdrant vectors, mock `job_posts`, and the deterministic demo role profile only when allowed.
    8. Do not insert `job_posts`, recompute scores, or call Qdrant upsert outside Plan 3 services.
  - Output: Shared demo loader and reset service.
  - Acceptance: Seed script and mock-load can share one fixture-to-state and reset path.
  - Validation: Demo loader and reset tests in Batch05.
  - Blocked Condition: None.
  - Files: `backend/app/services/demo_loader.py`.

- [ ] (04B): Create demo and messy social post JSON fixtures
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Demo Dataset`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Mock Data Normalization Contract`
    - `docs/plans/Master_Plan.md` > `## 5. Demo Mode / Mock Seeding`
  - Source Requirements:
    - Create 12 total demo inputs across `mock_data/demo_jobs.json` and `mock_data/messy_social_posts.json`.
    - Include 5 perfect matches, 3 partial matches, 2 unrelated jobs, and 2 messy social posts.
    - Include or closely mirror the required examples.
    - Use ASCII-safe locations such as `Ha Noi` unless the repo already standardizes Vietnamese Unicode.
  - Details: Add fixture data that exercises scoring and non-scorable social-post handling without external calls.
  - Dependencies: (04A).
  - User Action: None.
  - Agent Work: Create the two mock JSON files.
  - Specific Steps:
    1. Search for existing mock data before adding new fixture files.
    2. Create `mock_data/demo_jobs.json` with 10 structured job fixtures.
    3. Create `mock_data/messy_social_posts.json` with 2 social-post fixtures.
    4. Ensure each item contains enough structured fields to build a complete `JobAgentState`.
    5. Mark only `full_jd` and `partial_jd` fixtures as scorable.
    6. Put inbox/DM-only social posts into `contact_for_jd`, `no_jd`, or `partial_jd` as supported by fixture content.
    7. Keep fixture values deterministic and free of secrets.
  - Output: Demo fixture JSON files.
  - Acceptance: Fixtures validate through `demo_loader.py` and produce 12 states with 10 scorable jobs.
  - Validation: Fixture validation tests in Batch05.
  - Blocked Condition: None.
  - Files: `mock_data/demo_jobs.json`, `mock_data/messy_social_posts.json`.

- [ ] (04C): Implement seed demo script
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### seed_demo.py`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Demo Offline Expectations`
    - `docs/plans/Master_Plan.md` > `## 34. Demo Script Pseudocode`
  - Source Requirements:
    - Implement `backend/scripts/seed_demo.py`.
    - `python scripts/seed_demo.py --reset` clears only demo/mock-owned data.
    - Create a demo role profile.
    - Load fixtures through `demo_loader.py`.
    - Process each state through `job_processing_service.process_extraction_state(...)` or the established equivalent.
    - Print the expected demo summary.
    - First-time seed requires Qdrant and embeddings unless an explicit deterministic offline mode is implemented.
  - Details: Add the command-line demo setup path without bypassing the real backend pipeline.
  - Dependencies: (04A), (04B).
  - User Action: Run local Qdrant and provide OpenAI embedding access for live seed generation unless deterministic offline seed mode is explicitly implemented.
  - Agent Work: Create `backend/scripts/seed_demo.py`.
  - Specific Steps:
    1. Search for existing seed scripts before adding a new one.
    2. Parse `--reset`.
    3. On reset, call the shared demo reset helper without deleting non-mock jobs.
    4. Create or reuse the deterministic demo role profile.
    5. Generate one batch ID for the seed run.
    6. Load fixtures through `demo_loader.py`.
    7. Process every state through the Plan 3 job processing service.
    8. Print inserted jobs, scorable jobs, need-review/social jobs, and local Qdrant upsert count.
    9. Document in script help or safe output that post-seed demo mode does not require Tavily/LLM extraction/URL fetching, while first-time seed requires Qdrant and embeddings unless deterministic offline seeding is implemented.
  - Output: Seed demo script.
  - Acceptance: `python scripts/seed_demo.py --reset` seeds the expected 12 jobs without deleting non-mock data.
  - Validation: Seed tests with temporary SQLite and mocked Qdrant/embedding in Batch05; optional manual live seed.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for live first-time seeding when Qdrant or embedding credentials are missing.
  - Files: `backend/scripts/seed_demo.py`.

- [ ] (04D): Implement mock-load endpoint using shared demo loader
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Mock Load Endpoint`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Mock Data Normalization Contract`
    - `docs/plans/Master_Plan.md` > `## 26. API Endpoints`
  - Source Requirements:
    - Implement `POST /api/jobs/mock-load`.
    - If `reset_existing_demo = true`, call the shared demo reset helper before creating the new batch.
    - Preserve the request `role_profile_id` during mock-load reset.
    - If reset is false, do not delete existing mock rows and rely on Plan 3 deduplication.
    - Return the standard ingestion response.
  - Details: Add the API demo loading path with the same adapter and reset behavior as the seed script.
  - Dependencies: (03A), (04A), (04B).
  - User Action: None for mocked automated validation; live mock-load needs local Qdrant and embedding access for scorable jobs.
  - Agent Work: Extend `backend/app/api/routes_jobs.py` with mock-load behavior.
  - Specific Steps:
    1. Validate request payload through the shared mock-load schema.
    2. If reset is requested, call the shared reset helper with `preserve_role_profile_id = request.role_profile_id`.
    3. Generate one batch ID after reset.
    4. Load both fixture files through `demo_loader.py`.
    5. Process each state through the Plan 3 processing service.
    6. Accumulate counts and warnings into the standard ingestion response.
    7. Fetch inserted job rows and serialize them through `JobResponse`.
    8. Do not duplicate seed script logic, insert directly into `job_posts`, or call Qdrant outside Plan 3 services.
  - Output: Mock-load endpoint.
  - Acceptance: Mock-load and seed script share the same fixture adapter and reset behavior.
  - Validation: Mock-load route tests in Batch05.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for live mock-load when Qdrant or embedding credentials are missing.
  - Files: `backend/app/api/routes_jobs.py`.

### Files or Modules Likely Created or Updated

- `backend/app/services/demo_loader.py`
- `backend/scripts/seed_demo.py`
- `mock_data/demo_jobs.json`
- `mock_data/messy_social_posts.json`
- `backend/app/api/routes_jobs.py`

### Required Outputs / Artifacts

- Shared mock-to-state adapter.
- Shared safe demo reset helper.
- Two fixture files with 12 total inputs.
- Seed demo script.
- Mock-load endpoint.

### Acceptance Criteria

- Demo fixture processing uses the same Plan 3 pipeline as real extraction states.
- Reset deletes only mock-owned data and preserves the active mock-load role profile.
- Seed and mock-load do not bypass deduplication, scoring, SQLite-first persistence, or Qdrant sync.
- Offline expectations are explicit and tested.

### Required Tests or Validations

- Fixture validation tests.
- Seed tests with temporary SQLite and mocked Qdrant/embedding.
- Mock-load route tests.
- Optional manual `docker compose up -d qdrant; cd backend; python scripts/seed_demo.py --reset`.

### Explicit Non-Goals

- Do not create deterministic offline seed mode unless explicitly chosen as extra scope.
- Do not add an `is_demo` column or any schema change.
- Do not wipe non-mock jobs or manually entered data.
- Do not call LLM extraction, Tavily, URL fetching, or trafilatura for mock fixtures.

## Mandatory Batch05 - Verification and Phase Boundary Validation

### Goal

Add focused automated tests and final checks that prove Phase 4 behavior is complete, contract-aligned, and free of out-of-scope infrastructure.

### Why this batch exists

Phase 4 is an integration layer over existing services. Tests must catch contract drift, route-level business logic duplication, unsafe reset behavior, stale generated artifacts, and accidental scope creep before the React phase consumes the API.

### Inputs / Dependencies

- Completed Batches 01 through 04.
- Existing backend pytest setup and fake provider fixtures.
- Existing Phase 3 service tests.

### Tasks

- [ ] (05A): Add API contract export and app wiring tests
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### API Contract Export`
    - `docs/plans/Plan_4.md` > `## 9. Verification & Testing Plan`
  - Source Requirements:
    - Add a backend test or CI check that fails when `shared/api-contract.json` is missing or stale.
    - Verify contract values come from backend constants, transitions, endpoint metadata, and schema JSON.
    - Verify CORS allows `http://localhost:5173`.
    - Verify FastAPI startup calls the Plan 3 Qdrant initialization helper without duplicating setup.
  - Details: Protect the frontend contract and app bootstrap from drift.
  - Dependencies: (01C), (02E).
  - User Action: None.
  - Agent Work: Add focused contract and app wiring tests.
  - Specific Steps:
    1. Create `backend/tests/test_api_contract_export.py`.
    2. Run the export script in a temporary or controlled context and compare generated content to `shared/api-contract.json`.
    3. Assert constants, transitions, endpoint metadata, and schema objects are present.
    4. Test CORS behavior for the approved local origin.
    5. Mock Qdrant initialization and verify startup delegates to the existing service owner.
  - Output: Contract and app wiring tests.
  - Acceptance: Tests fail on stale contract output, missing endpoint metadata, missing schema JSON, or incorrect CORS/startup wiring.
  - Validation: `cd backend; pytest tests/test_api_contract_export.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_api_contract_export.py`, possibly existing route test files.

- [ ] (05B): Add core route tests for profiles, queries, status, and batch summary
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Role Profile Routes`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Review and Dashboard Queries`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Human-in-the-Loop Status Routes`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Batch Summary`
  - Source Requirements:
    - Role profile create returns a UUID.
    - Review queue and dashboard exclude duplicates and sort by score.
    - `GET /api/jobs?status=tracked` returns saved/applied/interview/rejected/offer jobs.
    - Approve, reject, and manual status update call Plan 3 status sync helpers.
    - Invalid transitions return HTTP 400.
    - Batch summary aggregates stored fields and returns 404 for unknown batches.
  - Details: Verify core route behavior with SQLite fixtures and mocked service boundaries where needed.
  - Dependencies: (02A), (02B), (02C), (02D).
  - User Action: None.
  - Agent Work: Add or extend route test modules.
  - Specific Steps:
    1. Add tests for role profile creation and list ordering.
    2. Add tests for review queue duplicate exclusion and ordering.
    3. Add tests for dashboard saved and tracked status filters.
    4. Add tests for job detail 200/404 behavior.
    5. Add tests for approve, reject, manual status update, and invalid transitions.
    6. Add tests that manual status update rejects `ignored`.
    7. Add tests for batch summary aggregation and 404 behavior.
  - Output: Core route test coverage.
  - Acceptance: Tests prove route handlers preserve query and status contracts.
  - Validation: `cd backend; pytest tests/test_routes_role_profiles.py tests/test_routes_jobs.py tests/test_routes_batches.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_routes_role_profiles.py`, `backend/tests/test_routes_jobs.py`, `backend/tests/test_routes_batches.py`.

- [ ] (05C): Add ingestion and search route tests with mocked providers
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Parse Routes`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Search Route`
    - `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners`
  - Source Requirements:
    - Parse text inserts a `pending_review` job and returns the standard ingestion response.
    - Parse URL with low content returns a manual input warning.
    - Search respects `MAX_URLS_PER_BATCH`.
    - Search continues after one URL parse failure.
    - Tavily failure returns HTTP 502 without crashing.
    - Ingestion responses load full jobs for Plan 3 `job_ids`.
  - Details: Verify ingestion orchestration without live LLM, Tavily, OpenAI, internet, or Qdrant.
  - Dependencies: (03A), (03B), (03C), (03D).
  - User Action: None.
  - Agent Work: Add ingestion and search tests using fakes/mocks.
  - Specific Steps:
    1. Mock extraction service outputs for parse-text and parse-url.
    2. Mock Plan 3 processing results and persisted job rows.
    3. Assert standard ingestion response counts, `jobs`, and `warnings`.
    4. Test URL warning behavior for `needs_manual_input`.
    5. Mock Tavily results and assert max URL clamping.
    6. Simulate one URL failure after Tavily success and assert remaining URLs continue.
    7. Simulate Tavily failure before processing and assert HTTP 502.
    8. Assert no queue, worker, cron, or background-job table is introduced.
  - Output: Ingestion and search route tests.
  - Acceptance: Tests prove ingestion routes use existing services and handle provider failures safely.
  - Validation: `cd backend; pytest tests/test_routes_jobs.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_routes_jobs.py`.

- [ ] (05D): Add demo loader, seed, mock-load, and final phase-boundary verification
  - Source of Truth:
    - `docs/plans/Plan_4.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Demo Dataset`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### Demo Offline Expectations`
    - `docs/plans/Plan_4.md` > `## 7. Technical Specifications` > `### seed_demo.py`
  - Source Requirements:
    - Actual mock JSON fixtures validate against the mock data normalization contract.
    - Seed reset does not delete non-mock jobs.
    - Seed reset succeeds after mock jobs have application rows.
    - Mock-load reset preserves the caller's active role profile.
    - Seed and mock-load share the same adapter and neither inserts directly into `job_posts` nor calls Qdrant outside Plan 3 services.
    - Post-seed demo mode does not depend on Tavily, LLM extraction, URL fetching, or manual paste.
  - Details: Complete demo reliability tests and phase-boundary checks.
  - Dependencies: (04A), (04B), (04C), (04D).
  - User Action: None for mocked automated validation; optional live seed requires local Qdrant and embedding credentials.
  - Agent Work: Add seed/demo tests and run final verification commands.
  - Specific Steps:
    1. Add `backend/tests/test_seed_demo.py`.
    2. Load actual fixture JSON and validate every item through `demo_loader.py`.
    3. Assert the dataset has 12 items, 10 scorable jobs, and 2 need-review/social jobs.
    4. Test safe reset deletes mock-owned application rows and mock jobs while preserving non-mock rows.
    5. Test mock-load reset passes and preserves `preserve_role_profile_id`.
    6. Test seed and mock-load both call the shared adapter and Plan 3 processing path.
    7. Verify first-time seed requirements and post-seed offline expectations are explicit.
    8. Run compile, import, route, contract, seed, and full backend pytest checks.
    9. Audit that no React UI, Celery/Redis, browser rendering, schema changes, or secret exposure was introduced.
  - Output: Demo tests and final verification results.
  - Acceptance: Phase 4 passes focused and full backend verification without scope creep.
  - Validation: `cd backend; python -m compileall -q app`; `cd backend; pytest`; optional manual seed command.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for optional live seed validation when Qdrant or embedding credentials are missing.
  - Files: `backend/tests/test_seed_demo.py`, existing test modules as needed.

### Files or Modules Likely Created or Updated

- `backend/tests/test_api_contract_export.py`
- `backend/tests/test_routes_role_profiles.py`
- `backend/tests/test_routes_jobs.py`
- `backend/tests/test_routes_batches.py`
- `backend/tests/test_seed_demo.py`

### Required Outputs / Artifacts

- Stale-contract test.
- Core route tests.
- Ingestion and search tests.
- Demo loader and seed tests.
- Final verification output.

### Acceptance Criteria

- Focused tests cover every Phase 4 endpoint and demo path.
- Full backend test suite passes with mocked external providers.
- Generated contract is current.
- No out-of-scope infrastructure or frontend work is introduced.

### Required Tests or Validations

- `cd backend; python -m compileall -q app`
- `cd backend; python scripts/export_api_contract.py`
- `cd backend; pytest tests/test_api_contract_export.py`
- `cd backend; pytest tests/test_routes_role_profiles.py tests/test_routes_jobs.py tests/test_routes_batches.py tests/test_seed_demo.py`
- `cd backend; pytest`
- Optional manual: `docker compose up -d qdrant; cd backend; python scripts/seed_demo.py --reset`

### Explicit Non-Goals

- Do not rely on live OpenAI, Tavily, public internet, or Qdrant for automated acceptance.
- Do not update React UI.
- Do not relax validation by converting source requirements into manual-only checks.

## Optional Future Tracks

- Deterministic first-time offline seeding with fake or precomputed embeddings is not part of the mandatory MVP batch chain. This track would be valid only if explicitly requested and must use the configured `EMBEDDING_DIMENSION`.
- Enterprise SSRF mitigation for URL parsing is not part of the mandatory MVP batch chain. The mandatory MVP only validates `http`/`https`, applies timeout/size limits, and includes the production note required by the source.
- Authenticated job-board or social-site crawling is not part of the mandatory MVP batch chain.

## Dependency Chain

- Batch01 -> Batch02
- Batch02 -> Batch03
- Batch03 -> Batch04
- Batch04 -> Batch05

Optional future tracks are outside the mandatory chain.

## Global Verification Checklist

- [ ] `backend/app/api/schemas.py` owns all API request and response schemas.
- [ ] API schemas use or are tested against backend constants for statuses and sources.
- [ ] `shared/api-contract.json` is generated from backend-owned sources and is not stale.
- [ ] All routes are registered under `/api`.
- [ ] CORS allows only `http://localhost:5173` for local development.
- [ ] FastAPI startup delegates Qdrant collection and payload-index initialization to the existing Plan 3 service owner.
- [ ] Route handlers do not duplicate scoring, deduplication, persistence, status transition, or Qdrant sync logic.
- [ ] Parse-text, parse-url, search, seed, and mock-load paths all process jobs through Plan 3 services.
- [ ] Ingestion responses include full `jobs` loaded from SQLite and transient `warnings`.
- [ ] Persisted job card errors come from `error_reason`, not ingestion `warnings`.
- [ ] Demo reset deletes only mock-owned data and preserves non-mock user data.
- [ ] Mock fixtures total 12 inputs with 10 scorable jobs and 2 need-review/social jobs.
- [ ] Batch summary metrics are computed from stored `job_posts` fields.
- [ ] No API response exposes API keys, `.env` values, or backend-only secrets.
- [ ] No React UI, frontend env file, Celery, Redis, Playwright, crawler, cover-letter, auto-apply, multi-user auth, schema migration, scoring change, or dedup policy change was introduced.
- [ ] Implementation code is clean, idiomatic, typed where appropriate, and easy to understand.

## Progress Tracker

### Batches

- [x] Batch01 - API Schema and Contract Foundation
- [ ] Batch02 - Core FastAPI Routes and App Wiring
- [ ] Batch03 - Manual and Search Ingestion Routes
- [ ] Batch04 - Demo Loader, Fixtures, Seed Script, and Mock Load
- [ ] Batch05 - Verification and Phase Boundary Validation

### Task IDs

#### Batch01

- [x] (01A): Verify Phase 4 prerequisites and service ownership boundaries
- [x] (01B): Create backend API request and response schemas
- [x] (01C): Generate the frontend API contract from backend owners

#### Batch02

- [ ] (02A): Implement role profile create and list routes
- [ ] (02B): Implement review, dashboard, and job detail routes
- [ ] (02C): Implement approve, reject, and manual status routes
- [ ] (02D): Implement batch summary route
- [ ] (02E): Register routers, local CORS, and Qdrant startup initialization

#### Batch03

- [ ] (03A): Implement standard ingestion response shaping and parse-text endpoint
- [ ] (03B): Implement parse-url endpoint with MVP URL safety limits
- [ ] (03C): Implement Tavily search service
- [ ] (03D): Implement search endpoint using parse-url pipeline

#### Batch04

- [ ] (04A): Implement demo loader adapter and safe reset helper
- [ ] (04B): Create demo and messy social post JSON fixtures
- [ ] (04C): Implement seed demo script
- [ ] (04D): Implement mock-load endpoint using shared demo loader

#### Batch05

- [ ] (05A): Add API contract export and app wiring tests
- [ ] (05B): Add core route tests for profiles, queries, status, and batch summary
- [ ] (05C): Add ingestion and search route tests with mocked providers
- [ ] (05D): Add demo loader, seed, mock-load, and final phase-boundary verification

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
- reason: missing API key, missing provider project, missing manual setup, or other safe summary

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
