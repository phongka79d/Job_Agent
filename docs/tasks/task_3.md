# Plan 3 - Scoring, Deduplication, Persistence, and Qdrant Sync Execution Tasks

## Purpose

Implement the backend processing phase after extraction: normalize skills, build clean embedding text, calculate deterministic score components, persist parsed jobs to SQLite, apply exact and key-based deduplication, synchronize scorable jobs with local Qdrant, and expose backend service methods for review/status transitions.

This task file stops at backend services and tests. It does not add FastAPI routes, Tavily search, demo seeding, mock data, React UI, or database schema changes.

## Authoritative Source

Source precedence for execution:

1. `docs/plans/Master_Plan.md` is the architecture and MVP source of truth.
2. `docs/plans/Plan_3.md` defines the approved Phase 3 boundary and detailed scoring, deduplication, persistence, Qdrant, and status-sync contracts where it does not conflict with the master plan.
3. `README.md` records the current project state and established Phase 1/2 file layout; it does not override either plan.

Comparison result:

- No architecture, scope, or validation conflict was found between the master plan and Plan 3.
- Plan 3 follows the master plan's SQLite-first durability rule and clarifies that Qdrant is a derived index, not the source of truth.
- The README confirms Phase 1 database models/settings/constants and Phase 2 extraction entrypoints already exist. Plan 3 must reuse those modules instead of redefining status, source, configuration, or extraction contracts.
- No existing `docs/tasks/task_3.md` was present before this task file was created.
- Plan 3 explicitly forbids database schema changes in this phase. If execution finds the Phase 1 ORM schema missing a required master-plan field or index, Phase 3 verification must fail and report a Phase 1 revision or migration need instead of altering the schema.

## Source Section Index

- `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack` -> approved backend, LangChain, SQLite, Qdrant, and test dependencies.
- `docs/plans/Master_Plan.md` > `## 4. Architecture` -> SQLite-first persistence and Qdrant-derived scoring flow.
- `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking` -> required handoff fields from extraction.
- `docs/plans/Master_Plan.md` > `## 8. JD Status Rules` -> scorable and non-scorable JD status behavior.
- `docs/plans/Master_Plan.md` > `## 9. Scoring Formula` -> base score and final score formulas.
- `docs/plans/Master_Plan.md` > `## 10. JD Confidence Multiplier` -> multiplier by JD status.
- `docs/plans/Master_Plan.md` > `## 11. Simplified Location and Level Scoring` -> three-tier location and level scores.
- `docs/plans/Master_Plan.md` > `## 12. Skill Overlap Normalization` -> normalized overlap formula.
- `docs/plans/Master_Plan.md` > `## 13. Skill Alias Normalization` -> alias table and normalization rule.
- `docs/plans/Master_Plan.md` > `## 16. Simplified Deduplication Strategy` -> raw hash, dedup key, and duplicate status policy.
- `docs/plans/Master_Plan.md` > `## 17. Smart Embedding Strategy` -> clean job embedding text and dynamic role query text.
- `docs/plans/Master_Plan.md` > `## 20. SQLite Database Design` -> SQLite storage rules and no extra tables.
- `docs/plans/Master_Plan.md` > `## 22. Table: job_posts` -> required persisted job fields.
- `docs/plans/Master_Plan.md` > `## 23. Table: applications` -> application tracking fields.
- `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes` -> required query and dedup indexes.
- `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema` -> Qdrant collection, payload, filters, point IDs, and status sync.
- `docs/plans/Master_Plan.md` > `## 31. Environment Setup` -> approved runtime and test dependencies.
- `docs/plans/Master_Plan.md` > `## 32. Single Root .env` -> embedding, Qdrant, and backend-only secret settings.
- `docs/plans/Master_Plan.md` > `## 35. Implementation Checklist` > `### Scoring` / `### Database` / `### Qdrant Local` -> MVP completion requirements used by this phase.
- `docs/plans/Plan_3.md` > `## 1. Objective` -> Phase 3 outcome.
- `docs/plans/Plan_3.md` > `## 3. Prerequisites from Prior Phases` -> required Phase 1/2 foundation.
- `docs/plans/Plan_3.md` > `## 4. Scope` and `## 5. Out of Scope` -> phase boundary.
- `docs/plans/Plan_3.md` > `## 6. Target Directory Structure` -> Phase 3 file locations and ownership.
- `docs/plans/Plan_3.md` > `## 7. Technical Specifications` -> detailed scoring, embedding, dedup, persistence, Qdrant, status, and application-row behavior.
- `docs/plans/Plan_3.md` > `## 8. Implementation Steps` -> required implementation inventory.
- `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` -> automated and manual checks.
- `docs/plans/Plan_3.md` > `## 10. Handoff Notes for Phase 4` -> output guarantees for the next phase.
- `README.md` > `## Directory Structure` -> current Phase 1/2 modules and test layout.
- `README.md` > `## Setup and Running Instructions` -> established backend verification workflow.
- `README.md` > `## Extraction Architecture & Workflows (Phase 2)` -> extraction service handoff and no-side-effect boundary.

## Approved Architecture Summary

- Plan 2 extraction returns a complete `JobAgentState`; Plan 3 consumes that state and writes durable rows to SQLite.
- SQLite is the source of truth for job status, job review visibility, duplicate metadata, applications, and score fields.
- Qdrant is a derived local vector index used to obtain the semantic similarity score for scorable jobs and to support later filtered vector queries.
- Only `full_jd` and `partial_jd` jobs are embedded and scored. `contact_for_jd`, `no_jd`, and `unclear` jobs remain visible as `pending_review` with null score fields and no Qdrant point.
- Deduplication uses only `raw_content_hash` first and a null-safe `dedup_key` second. Vector similarity deduplication is not part of MVP.
- New non-duplicate parsed jobs are inserted into SQLite as `pending_review` before OpenAI embedding or Qdrant operations are attempted.
- The canonical Qdrant point ID is `job_posts.id`, a standard UUID string generated by the ORM.
- Status mutation service methods own transition validation, application-row creation/update, and Qdrant payload/delete sync. Later API routes must call these methods rather than duplicating business rules.

## Global Implementation Rules

- Reuse `backend/app/core/constants.py` for executable job status, application status, JD status, input source, and source platform validation.
- Reuse `backend/app/core/config.py` for `OPENAI_EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `OPENAI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY`.
- Reuse Plan 2 `JobAgentState`, `JobPostExtract`, extraction outputs, `raw_content_hash`, and warnings; do not redefine extraction contracts.
- Search the codebase with `rg` or `grep` before adding helpers; reuse or safely extend existing utilities instead of duplicating logic.
- Do not change Phase 1 ORM schema or indexes in Plan 3. Verify the schema first and fail/report if it is incomplete.
- Keep database writes local to backend services. Do not add route handlers, frontend code, seed scripts, mock data, or Tavily search orchestration.
- Keep `scoring_service.py` deterministic and free of database, OpenAI, or Qdrant side effects.
- Keep `embedding_service.py` responsible for embedding provider calls and vector dimension validation only.
- Keep `dedup_service.py` responsible for duplicate keys and duplicate action decisions only.
- Keep `qdrant_service.py` responsible for collection initialization, indexes, filters, upsert/query/delete, and payload updates only.
- Keep `job_processing_service.py` responsible for Plan 2 state conversion, SQLite persistence, pipeline ordering, status mutations, application rows, warning propagation, and coordination with other services.
- Never log, print, commit, or expose secrets. `.env.example` may contain placeholder names only.
- Do not use local cosine fallback when Qdrant upsert/query fails. Persist the SQLite row and keep score fields null with a safe `error_reason`.
- Automated tests must use fakes/mocks for OpenAI and Qdrant by default. Live provider or local Qdrant checks are optional/manual unless explicitly requested.

## Execution Agent Coding Style Requirements

- Write clean, idiomatic, readable Python.
- Use descriptive names for modules, functions, variables, settings, protocols, result objects, and tests.
- Keep functions, services, and modules focused on one clear responsibility.
- Prefer simple, explicit control flow over clever abstractions.
- Follow the established FastAPI, Pydantic v2, SQLAlchemy async, LangChain OpenAI, and Qdrant client conventions already approved by the plans.
- Use clear typing where Python supports it.
- Avoid `Any`, broad exception handling, hidden global state, and hardcoded configuration values unless the source plan explicitly requires them.
- Add comments only for non-obvious decisions or failure-handling behavior.
- Keep frontend code free of backend-only secrets and backend-only configuration names.
- Avoid adding formatters, linters, frameworks, or architecture changes outside the source plan unless already present or explicitly requested.

## Batch Map

| Batch | Outcome | Depends On |
|---|---|---|
| Batch01 | Deterministic scoring, clean text builders, and embedding provider boundary | Phase 1/2 foundation |
| Batch02 | Deduplication and SQLite-first job persistence pipeline | Batch01 |
| Batch03 | Qdrant derived-index service, scorable-job integration, and status/application sync | Batch01, Batch02 |
| Batch04 | Focused tests, integration tests, and phase-boundary verification | Batch01, Batch02, Batch03 |

## Mandatory Batch01 - Scoring and Embedding Foundations

### Goal

Create deterministic scoring utilities and the embedding provider boundary needed by the persistence pipeline without touching SQLite or Qdrant.

### Why this batch exists

Scoring formulas, skill normalization, and clean embedding text are pure business rules. Implementing them first keeps later persistence and Qdrant work small, testable, and free of duplicated score math.

### Inputs / Dependencies

- Phase 1 settings and constants.
- Phase 2 extraction schema fields.
- Existing `langchain-openai` dependency.

### Tasks

- [x] (01A): Verify Phase 3 prerequisites and schema compatibility
  - Source of Truth:
    - `docs/plans/Plan_3.md` > `## 3. Prerequisites from Prior Phases`
    - `docs/plans/Plan_3.md` > `## 5. Out of Scope`
    - `docs/plans/Master_Plan.md` > `## 20. SQLite Database Design`
    - `docs/plans/Master_Plan.md` > `## 22. Table: job_posts`
    - `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes`
    - `README.md` > `## Directory Structure`
  - Source Requirements:
    - Plan 1 models, settings, constants, async session, and Qdrant compose support must already exist.
    - Plan 2 extraction must return `JobAgentState` with `batch_id`, `role_profile_id`, and `input_source`.
    - Phase 3 must not alter the database schema; missing fields or indexes require a reported Phase 1 revision.
  - Details: Confirm the current backend foundation before implementing Phase 3 services.
  - Dependencies: None.
  - User Action: None.
  - Agent Work: Inspect existing constants, settings, models, session setup, extraction schema, and extraction service entrypoints.
  - Specific Steps:
    1. Verify `backend/app/core/constants.py` exposes `JOB_STATUSES`, `TRACKED_JOB_STATUSES`, `APPLICATION_STATUSES`, `JD_STATUSES`, `SOURCE_PLATFORMS`, and `INPUT_SOURCES`.
    2. Verify `backend/app/core/config.py` exposes Qdrant and embedding settings.
    3. Verify `backend/app/db/models.py` contains the master-plan `role_profiles`, `job_posts`, `applications`, and required indexes.
    4. Verify Plan 2 state and public extraction entrypoints preserve `batch_id`, `role_profile_id`, `input_source`, `raw_content_hash`, `extracted_job`, and `user_warning`.
    5. Stop Phase 3 implementation and report an explicit revision/migration need if required schema fields or indexes are missing.
  - Output: Confirmed Phase 3 prerequisite checklist or a safe blocker report.
  - Acceptance: Execution agent can state whether Phase 3 can proceed without schema changes.
  - Validation: Import checks for constants, settings, models, and extraction entrypoints.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only if required local project files are absent or the user must approve a separate schema revision.
  - Files: Existing files only; no source edits expected for this task.

- [x] (01B): Implement deterministic scoring and clean text builders
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 8. JD Status Rules`
    - `docs/plans/Master_Plan.md` > `## 9. Scoring Formula`
    - `docs/plans/Master_Plan.md` > `## 10. JD Confidence Multiplier`
    - `docs/plans/Master_Plan.md` > `## 11. Simplified Location and Level Scoring`
    - `docs/plans/Master_Plan.md` > `## 12. Skill Overlap Normalization`
    - `docs/plans/Master_Plan.md` > `## 13. Skill Alias Normalization`
    - `docs/plans/Master_Plan.md` > `## 17. Smart Embedding Strategy`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Scorable JD Rules` / `### Scoring Formula` / `### Embedding Text`
  - Source Requirements:
    - Score only `full_jd` and `partial_jd`.
    - Normalize all score components to `[0, 1]`.
    - Apply the approved JD confidence multiplier.
    - Normalize skills through the approved alias table.
    - Build job embedding text only from clean extracted fields.
    - Build role query text dynamically and do not store it in the database.
  - Details: Add pure functions for score math, status eligibility, skill normalization, and text construction.
  - Dependencies: (01A).
  - User Action: None.
  - Agent Work: Create `backend/app/services/scoring_service.py` with deterministic functions only.
  - Specific Steps:
    1. Import shared constants for JD status validation instead of defining executable status sets.
    2. Add the approved `SKILL_ALIASES` mapping and `normalize_skill`.
    3. Add skill set normalization and `calculate_skill_overlap_score`.
    4. Add three-tier location and level scoring, including the approved adjacent-level pairs.
    5. Add JD confidence multiplier logic returning `None` for non-scorable statuses.
    6. Add base score, final score, final percent, and score-clamping helpers.
    7. Add `build_embedding_text(job)` using title, level, location, work mode, responsibilities, requirements, skills, and tech stack only when present.
    8. Add `build_role_query_text(role_profile)` using target role, level, location, remote preference, skills, and resume/profile text.
    9. Keep the module free of database sessions, network calls, provider calls, Qdrant calls, or route dependencies.
  - Output: Deterministic scoring and embedding text utility module.
  - Acceptance: All functions are importable, deterministic, typed, and independent of external services.
  - Validation: Focused scoring tests created in Batch04.
  - Blocked Condition: None.
  - Files: `backend/app/services/scoring_service.py`.

- [x] (01C): Implement embedding provider service and vector validation
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 17. Smart Embedding Strategy`
    - `docs/plans/Master_Plan.md` > `## 31. Environment Setup`
    - `docs/plans/Master_Plan.md` > `## 32. Single Root .env`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Embedding and Semantic Similarity`
  - Source Requirements:
    - Use `langchain_openai.OpenAIEmbeddings`.
    - Read `OPENAI_EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, and `OPENAI_API_KEY` from settings.
    - Validate returned vector length against `settings.EMBEDDING_DIMENSION`.
    - Do not embed non-scorable jobs, raw HTML, raw scraped text, or full messy JD text.
  - Details: Isolate provider calls behind a small async boundary that tests can fake.
  - Dependencies: (01A), (01B).
  - User Action: Add a real `OPENAI_API_KEY` to the uncommitted root `.env` only for optional live-provider validation.
  - Agent Work: Create `backend/app/services/embedding_service.py` with async embedding generation and dimension validation.
  - Specific Steps:
    1. Configure `OpenAIEmbeddings` from backend settings only.
    2. Implement `async def embed_text(text: str) -> list[float]`.
    3. Reject or fail safely for blank text before provider calls.
    4. Validate vector length exactly equals `settings.EMBEDDING_DIMENSION`.
    5. Raise a typed service error or return a safe failure path that `job_processing_service.py` can convert into null score fields and `error_reason`.
    6. Avoid constructing required live provider clients during test module import.
    7. Do not log API keys, request bodies containing secrets, or full provider responses.
  - Output: Mockable embedding provider boundary.
  - Acceptance: Tests can substitute fake embeddings; production code reads backend-only settings and validates dimensions.
  - Validation: Focused embedding tests created in Batch04.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for an explicitly requested live-provider validation when a valid API key is absent; mocked automated acceptance remains available.
  - Files: `backend/app/services/embedding_service.py`.

### Files or Modules Likely Created or Updated

- `backend/app/services/scoring_service.py`
- `backend/app/services/embedding_service.py`
- `backend/app/services/__init__.py` only if intentional public exports are needed
- Batch04 test files for scoring and embedding

### Required Outputs / Artifacts

- Deterministic scoring module.
- Clean job embedding text builder.
- Dynamic role query text builder.
- Mockable embedding provider module.
- Explicit prerequisite verification result.

### Acceptance Criteria

- Pure scoring behavior matches the master plan.
- Provider embedding behavior is isolated and dimension-checked.
- No database, Qdrant, route, frontend, or schema work is introduced in this batch.

### Required Tests or Validations

- Import checks for new service modules.
- Unit tests for all deterministic scoring functions.
- Unit tests for embedding vector success, blank text, provider failure, and dimension mismatch using fakes/mocks.

### Explicit Non-Goals

- SQLite writes.
- Qdrant operations.
- Deduplication.
- Status mutation.
- API routes or frontend behavior.

## Mandatory Batch02 - Deduplication and SQLite-First Persistence

### Goal

Persist Plan 2 extraction results to SQLite with exact deduplication, null-safe key deduplication, duplicate metadata behavior, and durable pending-review rows before any embedding or Qdrant operation.

### Why this batch exists

The system must never lose parsed jobs because embedding or Qdrant fails. Durable SQLite persistence and duplicate decisions are the root of the processing pipeline.

### Inputs / Dependencies

- Batch01 scoring/text helpers.
- Phase 1 ORM models and async session.
- Phase 2 `JobAgentState` and `JobPostExtract` output shape.
- Shared constants from `backend/app/core/constants.py`.

### Tasks

- [x] (02A): Implement null-safe deduplication service
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 16. Simplified Deduplication Strategy`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Deduplication`
  - Source Requirements:
    - Use `raw_content_hash` exact duplicate detection first.
    - Generate `dedup_key` only when normalized company and title are both present.
    - Use `TRACKED_JOB_STATUSES` from shared constants for duplicate action policy.
    - Do not use vector similarity for deduplication.
  - Details: Add small duplicate-key and duplicate-action helpers, leaving database queries to the processing service or a narrow repository helper.
  - Dependencies: (01A).
  - User Action: None.
  - Agent Work: Create `backend/app/services/dedup_service.py`.
  - Specific Steps:
    1. Add company/title normalization helpers with whitespace trimming and case normalization.
    2. Implement null-safe `build_dedup_key(company, title)` that returns `None` when either value is missing or blank.
    3. Use a deterministic standard hash for non-null dedup keys.
    4. Implement `decide_duplicate_action(existing_job_status: str)`.
    5. Import `TRACKED_JOB_STATUSES` from shared constants rather than duplicating tracked status values.
    6. Keep the service free of Qdrant, embedding, route, and frontend dependencies.
  - Output: Focused deduplication utility module.
  - Acceptance: Duplicate decisions match the approved policy and missing company/title never collide through a shared empty key.
  - Validation: Dedup service tests created in Batch04.
  - Blocked Condition: None.
  - Files: `backend/app/services/dedup_service.py`.

- [x] (02B): Implement extraction-state to job persistence mapping
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking`
    - `docs/plans/Master_Plan.md` > `## 8. JD Status Rules`
    - `docs/plans/Master_Plan.md` > `## 20. SQLite Database Design`
    - `docs/plans/Master_Plan.md` > `## 22. Table: job_posts`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Persistence` / `### Processing Pipeline Order`
    - `README.md` > `## Extraction Architecture & Workflows (Phase 2)`
  - Source Requirements:
    - Validate required state keys: `batch_id`, `role_profile_id`, and `input_source`.
    - Convert `extracted_job` plus extraction metadata into a `job_posts` row.
    - All non-skipped, non-duplicate-metadata parsed jobs save as `pending_review`.
    - Non-scorable jobs persist with all score fields null and no embedding text unless the source already provided a safe null placeholder.
    - Map `JobAgentState.user_warning` to `JobProcessingResult.warnings`.
  - Details: Build the row-payload conversion layer without calling OpenAI or Qdrant.
  - Dependencies: (01B), (02A).
  - User Action: None.
  - Agent Work: Create the mapping helpers inside `backend/app/services/job_processing_service.py` or a private backend repository/helper module.
  - Specific Steps:
    1. Validate `batch_id`, `role_profile_id`, `input_source`, and `extracted_job` are present where required.
    2. Load the `RoleProfile` from SQLite by `role_profile_id`.
    3. Convert extracted job fields into `JobPost` fields, preserving source URL, source platform, parse status, extraction status, cost, token, timing, and error fields.
    4. Serialize skills consistently with the existing Phase 1 JSON-text convention.
    5. Derive `should_score_similarity` from JD status and approved scorable rules rather than trusting inconsistent input blindly.
    6. Build `embedding_text` deterministically before insert only for scorable non-duplicate jobs.
    7. Keep all score fields null at initial insert.
    8. Append `user_warning` to the processing result warnings without logging secrets.
  - Output: Safe conversion from Plan 2 extraction state to SQLite job payload.
  - Acceptance: Mapping can produce complete pending-review rows for scorable, non-scorable, and unclear extraction results.
  - Validation: Persistence mapping tests created in Batch04.
  - Blocked Condition: None unless the role profile referenced by input state does not exist in the test/runtime database; report a safe validation error.
  - Files: `backend/app/services/job_processing_service.py` and optionally one narrow private helper under `backend/app/db/` or `backend/app/services/`.

- [x] (02C): Implement SQLite-first processing result and duplicate persistence behavior
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4. Architecture`
    - `docs/plans/Master_Plan.md` > `## 16. Simplified Deduplication Strategy`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Processing Pipeline Order` / `### Processing Result` / `### Qdrant Failure Handling`
  - Source Requirements:
    - Dedup decision happens before insertion.
    - Exact duplicate by `raw_content_hash` skips insert.
    - Existing tracked duplicate can insert only ignored duplicate metadata.
    - Duplicate skipped jobs and duplicate metadata rows do not call embedding or Qdrant.
    - New non-duplicate rows commit to SQLite before embedding or Qdrant calls.
    - Integrity collisions on `raw_content_hash` roll back and return skipped exact duplicate without Qdrant calls.
  - Details: Implement the durable processing skeleton and result object before Qdrant integration.
  - Dependencies: (02A), (02B).
  - User Action: None.
  - Agent Work: Add `JobProcessingResult` and the SQLite-first insertion/dedup flow in `job_processing_service.py`.
  - Specific Steps:
    1. Define `JobProcessingResult` with inserted, skipped, duplicate metadata, Qdrant, job ID, and warning fields from Plan 3.
    2. Query for exact duplicates by `raw_content_hash` first.
    3. Query by dedup key only when a non-null key exists.
    4. Skip duplicates according to the approved duplicate policy.
    5. Insert duplicate metadata rows as `status = "ignored"`, `duplicate_of_job_id = existing_job.id`, `should_score_similarity = false`, and all score fields null.
    6. Insert non-duplicate jobs as `status = "pending_review"` with initial score fields null.
    7. Commit new rows before returning their canonical UUIDs to later embedding/Qdrant logic.
    8. Catch `IntegrityError` from raw hash collisions, roll back, fetch the existing row, and return a skipped exact duplicate result.
    9. Ensure skipped duplicates never trigger embedding or Qdrant work.
  - Output: Durable deduplication and SQLite insertion pipeline with a processing result.
  - Acceptance: The service can insert new pending-review rows, skip exact/key duplicates, and insert ignored duplicate metadata rows without Qdrant.
  - Validation: SQLite-backed processing and dedup tests created in Batch04.
  - Blocked Condition: None.
  - Files: `backend/app/services/job_processing_service.py` and optional narrow repository helper.

### Files or Modules Likely Created or Updated

- `backend/app/services/dedup_service.py`
- `backend/app/services/job_processing_service.py`
- Optional narrow backend repository/helper under `backend/app/db/` or `backend/app/services/`
- Batch04 dedup and persistence tests

### Required Outputs / Artifacts

- Null-safe dedup key builder.
- Duplicate action policy.
- SQLite-first job persistence flow.
- `JobProcessingResult`.
- Warning propagation from extraction state to processing result.

### Acceptance Criteria

- New parsed jobs are durable in SQLite before external provider or Qdrant work.
- Duplicates do not re-enter `pending_review`.
- Duplicate metadata rows are ignored, unscored, and linked to the original job.
- Phase 3 does not modify database schema.

### Required Tests or Validations

- Dedup unit tests.
- SQLite integration tests for inserts, skipped duplicates, duplicate metadata, and raw hash integrity collisions.
- Import checks for `job_processing_service.py`.

### Explicit Non-Goals

- Qdrant collection creation or vector sync.
- OpenAI embedding calls during duplicate paths.
- API routes.
- Dashboard queries or frontend changes.
- Database migrations or model/index changes.

## Mandatory Batch03 - Qdrant Sync and Status Mutation Services

### Goal

Add Qdrant collection/index/filter/upsert/query/delete/payload behavior, integrate scorable job embedding and Qdrant-derived similarity into the SQLite-first pipeline, and implement backend-owned status mutations with application-row semantics.

### Why this batch exists

Qdrant is a derived index and must stay synchronized with SQLite without becoming the source of truth. Status changes also have cross-cutting effects on application tracking and Qdrant payloads, so the backend needs one service-owned implementation before routes are added in Plan 4.

### Inputs / Dependencies

- Batch01 scoring and embedding services.
- Batch02 deduplication and SQLite persistence service.
- Phase 1 Qdrant configuration and Docker Compose support.
- Shared constants and ORM models.

### Tasks

- [x] (03A): Implement Qdrant collection, payload, and filter service
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema`
    - `docs/plans/Master_Plan.md` > `## 32. Single Root .env`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Qdrant Collection` / `### Query Isolation` / `### Qdrant Failure Handling`
  - Source Requirements:
    - Collection name is `job_posts`.
    - Distance is cosine.
    - Vector size comes from `EMBEDDING_DIMENSION`.
    - Point ID is `job_posts.id` as a standard UUID string.
    - Payload indexes are `role_profile_id`, `status`, `jd_status`, `batch_id`, and `source_platform`.
    - Filter builders isolate queries by role profile and status, and job-specific scoring filters include the current job ID.
    - Collection initialization must be idempotent and exposed for Plan 4 startup.
  - Details: Add Qdrant client operations behind one service so route modules never own collection/index logic.
  - Dependencies: (01A), (01B).
  - User Action: Run `docker compose up -d qdrant` only for optional local/manual Qdrant verification.
  - Agent Work: Create `backend/app/services/qdrant_service.py`.
  - Specific Steps:
    1. Configure the Qdrant client from backend settings.
    2. Implement idempotent `ensure_collection()` that creates the collection with cosine distance and configured dimension if missing.
    3. Implement idempotent payload index creation for the approved fields.
    4. Build payload serialization for `JobPost` rows using only lightweight filter fields.
    5. Implement pending-review and saved-job filter builders.
    6. Implement a job-specific scoring filter that includes `role_profile_id`, `status = pending_review`, and `job_id = current_job_id`.
    7. Implement upsert for scorable jobs only, using `wait=True` or the client/library equivalent when available.
    8. Implement Qdrant similarity query and score extraction for the current job only.
    9. Implement idempotent delete and payload status update helpers.
    10. Log safe Qdrant error summaries without secrets or full payload dumps.
  - Output: Focused Qdrant service module.
  - Acceptance: Qdrant operations are importable, fakeable in tests, idempotent where required, and use approved collection/payload/filter contracts.
  - Validation: Mocked Qdrant service tests created in Batch04.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for optional manual Qdrant verification if Docker/Qdrant is not running; mocked automated acceptance remains available.
  - Files: `backend/app/services/qdrant_service.py`.

- [x] (03B): Integrate scorable job embedding, Qdrant scoring, and SQLite score update
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4. Architecture`
    - `docs/plans/Master_Plan.md` > `## 8. JD Status Rules`
    - `docs/plans/Master_Plan.md` > `## 9. Scoring Formula`
    - `docs/plans/Master_Plan.md` > `## 17. Smart Embedding Strategy`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Embedding and Semantic Similarity` / `### Qdrant Write/Read Consistency Guard` / `### Processing Pipeline Order`
  - Source Requirements:
    - Insert and commit the SQLite row before OpenAI embedding or Qdrant calls.
    - Generate role query embedding and job embedding only after SQLite commit.
    - Upsert scorable job vectors using the SQLite job ID as Qdrant point ID.
    - Query Qdrant for the current job with role profile, pending-review status, and job ID filters.
    - Use Qdrant cosine score as `embedding_similarity`, clamped to `[0, 1]`.
    - Retry current-job scoring query with a small bounded retry policy when the just-upserted point is not visible.
    - If embedding or Qdrant fails, keep the SQLite row committed as `pending_review` with null score fields and a safe `error_reason`.
    - Do not use local cosine fallback.
  - Details: Complete the scorable branch of the processing pipeline while preserving SQLite durability.
  - Dependencies: (01B), (01C), (02C), (03A).
  - User Action: Real `OPENAI_API_KEY` and running Qdrant are required only for optional live/manual end-to-end verification.
  - Agent Work: Update `job_processing_service.py` to coordinate scoring, embedding, Qdrant, and score updates.
  - Specific Steps:
    1. Leave non-scorable jobs committed with null score fields and no provider/Qdrant calls.
    2. For scorable jobs, use the persisted `embedding_text` or rebuild the same deterministic text after commit.
    3. Build role query text dynamically from the loaded role profile.
    4. Generate role and job embeddings through `embedding_service.py`.
    5. Upsert the job vector through `qdrant_service.py` with write acknowledgement.
    6. Query Qdrant for the current job only, using bounded retries and short backoff.
    7. Treat "current job not returned" as Qdrant sync failure, not score `0.0`.
    8. Calculate skill, location, level, base, final, and percent scores only after Qdrant similarity is available.
    9. Update the same SQLite row with score fields and `qdrant_synced` result information.
    10. On embedding/Qdrant failure, set or append a safe `error_reason`, keep scores null, preserve `embedding_text` when available, and return `qdrant_synced = false`.
  - Output: End-to-end scorable job processing branch.
  - Acceptance: Scorable jobs can be inserted first, embedded, upserted, scored from Qdrant, and updated in SQLite; all failure paths keep the row visible.
  - Validation: Mocked embedding/Qdrant integration tests created in Batch04.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for optional live-provider/manual-Qdrant validation when credentials or local Qdrant are absent; mocked automated acceptance remains available.
  - Files: `backend/app/services/job_processing_service.py`.

- [x] (03C): Implement status transitions, application rows, and Qdrant status sync
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 19. Human-in-the-Loop Rules`
    - `docs/plans/Master_Plan.md` > `## 23. Table: applications`
    - `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema` > `### SQLite -> Qdrant Status Sync Rules`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Service-Owned Status Transitions` / `### Applications Row Semantics` / `### Qdrant Status Sync`
  - Source Requirements:
    - Build `ALLOWED_STATUS_TRANSITIONS` from shared constants and make it importable for Plan 4 API contract export.
    - `approve_job(job_id)` validates `pending_review -> saved`, updates SQLite, then updates Qdrant payload.
    - `reject_job(job_id)` validates `pending_review -> ignored`, updates SQLite, then deletes the Qdrant point idempotently.
    - `update_job_status(job_id, status)` validates tracked transitions and updates Qdrant payload.
    - `PATCH /api/jobs/{id}/status` in Plan 4 must never pass `ignored`; only `reject_job` sets review jobs to `ignored`.
    - Tracked statuses create or update exactly one `applications` row with the approved `applied_at` semantics.
    - Manual tracked `rejected` updates Qdrant payload instead of deleting; only review rejection to `ignored` deletes.
  - Details: Make `job_processing_service.py` the single backend owner of job status mutations before API routes exist.
  - Dependencies: (02C), (03A).
  - User Action: None.
  - Agent Work: Add transition map, domain error, and service methods to `job_processing_service.py`.
  - Specific Steps:
    1. Define `InvalidStatusTransition` or an equivalent domain error.
    2. Define `ALLOWED_STATUS_TRANSITIONS` and validate it against `JOB_STATUSES` and `APPLICATION_STATUSES`.
    3. Implement current-status loading and transition validation before mutation.
    4. Implement `approve_job(job_id)` with SQLite `saved` update followed by Qdrant payload status update.
    5. Implement `reject_job(job_id)` with SQLite `ignored` update followed by idempotent Qdrant point delete.
    6. Implement `update_job_status(job_id, status)` for `applied`, `interview`, `rejected`, and `offer`.
    7. Create one `applications` row for `applied` when absent and set `applied_at = now`.
    8. Update existing application status for `interview`, `rejected`, or `offer` while preserving `applied_at`.
    9. For `saved -> rejected` with no application row, create one with `status = rejected` and `applied_at = null`.
    10. Ensure no application rows are created for `pending_review`, `saved`, or `ignored`.
    11. Ensure no more than one application row exists per `job_post_id` through service logic and tests.
  - Output: Status mutation service API ready for Plan 4 routes.
  - Acceptance: Invalid transitions fail before SQLite or Qdrant mutation, valid transitions update SQLite/applications and synchronize Qdrant as specified.
  - Validation: Status transition, application-row, and Qdrant sync tests created in Batch04.
  - Blocked Condition: None.
  - Files: `backend/app/services/job_processing_service.py`, optional narrow helper module if needed for transition constants.

### Files or Modules Likely Created or Updated

- `backend/app/services/qdrant_service.py`
- `backend/app/services/job_processing_service.py`
- Optional narrow transition/helper module under `backend/app/services/`
- Batch04 Qdrant and status sync tests

### Required Outputs / Artifacts

- Idempotent Qdrant collection initialization.
- Qdrant payload indexes and filter builders.
- Qdrant upsert/query/delete/payload update helpers.
- Scorable job pipeline integration.
- Status transition map and domain error.
- `approve_job`, `reject_job`, and `update_job_status` service methods.
- Application-row tracking behavior.

### Acceptance Criteria

- SQLite remains the source of truth through all Qdrant failures.
- Scorable jobs use Qdrant query score for semantic similarity.
- Qdrant filters prevent other jobs from providing the current job's score.
- Status mutation behavior is centralized and ready for Plan 4 route consumption.

### Required Tests or Validations

- Mocked Qdrant collection/index/filter/upsert/query/delete/payload tests.
- Mocked embedding/Qdrant pipeline tests.
- SQLite status transition and application-row tests.
- Import test proving the transition map is available for Plan 4 API contract export.

### Explicit Non-Goals

- FastAPI routes.
- API contract export script implementation.
- Frontend status controls.
- Demo seed data.
- Live Qdrant as a required automated test dependency.

## Mandatory Batch04 - Verification and Phase Boundary Tests

### Goal

Prove Plan 3 behavior with deterministic tests and smoke checks, then confirm no Plan 4/5 scope entered the implementation.

### Why this batch exists

Plan 4 will depend on these backend services directly. Verification must catch score drift, duplicate policy drift, durability regressions, Qdrant filter mistakes, invalid transition behavior, and accidental API/frontend expansion before handoff.

### Inputs / Dependencies

- Completed Batch01 through Batch03 implementation.
- Existing `pytest` and `pytest-asyncio` development dependencies.
- Mockable embedding and Qdrant boundaries.
- Established `backend/tests/` layout.

### Tasks

- [x] (04A): Verify scoring and embedding foundations
  - Source of Truth:
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` > `Expected scoring test cases`
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` > `Expected embedding/scoring pipeline tests`
    - `docs/plans/Master_Plan.md` > `## 9. Scoring Formula`
    - `docs/plans/Master_Plan.md` > `## 13. Skill Alias Normalization`
  - Source Requirements:
    - Verify JD confidence, base score, final score, skill overlap, alias normalization, location match, and level match.
    - Verify embedding dimension mismatch and provider failure paths are safe.
    - Verify Qdrant score normalization clamps to `[0, 1]`.
  - Details: Add focused unit tests that do not use a live provider.
  - Dependencies: Batch01.
  - User Action: None.
  - Agent Work: Add tests for deterministic scoring and embedding boundary behavior.
  - Specific Steps:
    1. Test `full_jd` with base score `0.80` returns final score `0.80`.
    2. Test `partial_jd` with base score `0.80` returns final score `0.68`.
    3. Test non-scorable statuses return null score behavior where applicable.
    4. Test empty job required skills returns skill overlap `0.0`.
    5. Test "Retrieval-Augmented Generation" maps to `rag`.
    6. Test exact, partial/remote, and mismatch location scores.
    7. Test adjacent and mismatch level scores, including `intern` versus `fresher`.
    8. Test embedding vector dimension success and mismatch with fake embeddings.
    9. Test provider failure is converted into the expected service failure path without secrets.
    10. Test Qdrant similarity score clamping helper.
  - Output: Scoring and embedding test coverage.
  - Acceptance: Tests fail on formula, alias, normalization, or embedding validation drift.
  - Validation: `pytest tests/test_scoring_service.py tests/test_embedding_service.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_scoring_service.py`, `backend/tests/test_embedding_service.py`.

- [x] (04B): Verify deduplication and SQLite persistence behavior
  - Source of Truth:
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` > `Expected dedup test cases`
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` > `Expected persistence/Qdrant tests`
    - `docs/plans/Master_Plan.md` > `## 16. Simplified Deduplication Strategy`
    - `docs/plans/Master_Plan.md` > `## 24. SQLite Indexes`
  - Source Requirements:
    - Verify exact duplicates skip insert.
    - Verify dedup-key policy for pending, tracked, and ignored existing jobs.
    - Verify missing company/title produces `dedup_key = None`.
    - Verify SQLite commit happens before embedding and Qdrant calls.
    - Verify duplicate metadata rows are ignored and do not upsert Qdrant.
  - Details: Use SQLite-backed tests and fakes for external services.
  - Dependencies: Batch02, Batch03 where Qdrant call exclusion is asserted.
  - User Action: None.
  - Agent Work: Add integration tests for dedup and persistence pipeline behavior.
  - Specific Steps:
    1. Test duplicate `raw_content_hash` skips insert and returns existing ID/count.
    2. Test existing `pending_review` dedup-key duplicate skips insert.
    3. Test existing tracked duplicate inserts only ignored duplicate metadata when policy chooses metadata insertion.
    4. Test existing `ignored` duplicate skips insert.
    5. Test missing company or title produces `dedup_key = None` and does not collide with other unclear jobs.
    6. Test non-duplicate scorable job commits a row before fake embedding or fake Qdrant is called.
    7. Test non-scorable job commits with null score fields and no embedding/Qdrant calls.
    8. Test embedding failure after commit leaves the row `pending_review` with null score fields and safe `error_reason`.
    9. Test `IntegrityError` from raw hash collision rolls back and returns skipped exact duplicate without Qdrant calls.
    10. Test `JobProcessingResult.warnings` includes `JobAgentState.user_warning` when present.
  - Output: Deduplication and persistence test coverage.
  - Acceptance: Tests fail on duplicate policy drift, SQLite-first ordering drift, or accidental provider calls in skipped paths.
  - Validation: `pytest tests/test_dedup_service.py tests/test_job_persistence.py tests/test_job_processing_service.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_dedup_service.py`, `backend/tests/test_job_persistence.py`, `backend/tests/test_job_processing_service.py`.

- [x] (04C): Verify Qdrant service, scorable pipeline, and status sync behavior
  - Source of Truth:
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` > `Expected Qdrant test cases`
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan` > `Expected persistence/Qdrant tests`
    - `docs/plans/Master_Plan.md` > `## 25. Qdrant Local Collection Schema`
    - `docs/plans/Plan_3.md` > `## 7. Technical Specifications` > `### Service-Owned Status Transitions` / `### Applications Row Semantics`
  - Source Requirements:
    - Verify canonical UUID point IDs, payload indexes, filters, write acknowledgement, and current-job-only similarity.
    - Verify Qdrant failures keep SQLite rows and produce null scores.
    - Verify invalid transitions fail before mutation.
    - Verify application-row semantics and Qdrant status sync.
  - Details: Use mocked Qdrant clients and SQLite integration tests; live Qdrant is optional/manual.
  - Dependencies: Batch03.
  - User Action: None for automated tests.
  - Agent Work: Add Qdrant, scorable pipeline, transition, and application-row tests.
  - Specific Steps:
    1. Test `ensure_collection()` creates missing collection with cosine distance and configured dimension.
    2. Test payload indexes are requested for `role_profile_id`, `status`, `jd_status`, `batch_id`, and `source_platform`.
    3. Test scorable upsert uses canonical UUID `job_posts.id`.
    4. Test upsert requests write acknowledgement.
    5. Test pending-review filter includes `role_profile_id` and `status`.
    6. Test job-specific scoring filter includes the current `job_id`.
    7. Test Qdrant query score is used for `embedding_similarity`.
    8. Test current job not returned after bounded retries leaves score fields null and `qdrant_synced = false`.
    9. Test Qdrant upsert/query failure keeps the committed SQLite row.
    10. Test approve updates SQLite to `saved` and Qdrant payload to `saved`.
    11. Test review reject updates SQLite to `ignored` and deletes Qdrant point idempotently.
    12. Test manual `rejected` updates Qdrant payload instead of deleting.
    13. Test invalid transitions raise the domain error before SQLite or Qdrant mutation.
    14. Test `saved -> rejected` creates one application row with `applied_at = null` when absent.
    15. Test `applied -> interview/rejected` updates the existing application row and preserves `applied_at`.
  - Output: Qdrant, scorable pipeline, and status sync test coverage.
  - Acceptance: Tests fail on stale Qdrant filters, non-durable failure handling, invalid transition mutation, or application-row drift.
  - Validation: `pytest tests/test_qdrant_service.py tests/test_job_processing_service.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_qdrant_service.py`, `backend/tests/test_job_processing_service.py`.

- [x] (04D): Run full Phase 3 verification and confirm handoff boundary
  - Source of Truth:
    - `docs/plans/Plan_3.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Plan_3.md` > `## 10. Handoff Notes for Phase 4`
    - `README.md` > `## Setup and Running Instructions`
  - Source Requirements:
    - Run focused Plan 3 tests and full backend tests.
    - Confirm Plan 3 adds no route handlers, Tavily orchestration, seed demo data, mock JSON, React UI, or schema changes.
    - Confirm Plan 4 can consume processing services, Qdrant initialization, status methods, warnings, and transition map.
  - Details: Perform final evidence-based verification and record any environment limitation safely.
  - Dependencies: (04A), (04B), (04C).
  - User Action: Optional only: provide real provider credentials and run local Qdrant for manual live smoke checks.
  - Agent Work: Run commands, inspect failures, and document Phase 4 handoff.
  - Specific Steps:
    1. Run focused Plan 3 test files.
    2. Run the full backend test suite.
    3. Run `python -m compileall -q app` from `backend`.
    4. Run import smoke checks for `scoring_service`, `embedding_service`, `dedup_service`, `qdrant_service`, and `job_processing_service`.
    5. Confirm new code did not add API route handlers, frontend code, Tavily search implementation, seed data, mock JSON, or model/schema/index changes.
    6. Optionally run local manual Qdrant smoke checks only if Docker/Qdrant and credentials are available.
    7. Record command results and any blocked optional validations in the execution report.
  - Output: Verification evidence and Phase 4-ready handoff confirmation.
  - Acceptance: Focused tests and full backend tests pass, compile/import smoke checks pass, and no out-of-scope files or schema changes are present.
  - Validation: From `backend`: `pytest tests/test_scoring_service.py tests/test_embedding_service.py tests/test_dedup_service.py tests/test_job_processing_service.py tests/test_job_persistence.py tests/test_qdrant_service.py`, then `pytest`.
  - Blocked Condition: None for mocked automated verification; `BLOCKED_BY_USER_ACTION` only for optional live provider/local Qdrant validation when credentials or local services are absent.
  - Files: Test files and execution report/progress artifacts only; no new runtime scope.

### Files or Modules Likely Created or Updated

- `backend/tests/test_scoring_service.py`
- `backend/tests/test_embedding_service.py`
- `backend/tests/test_dedup_service.py`
- `backend/tests/test_job_processing_service.py`
- `backend/tests/test_job_persistence.py`
- `backend/tests/test_qdrant_service.py`
- Task progress and execution report artifacts used by the execution workflow

### Required Outputs / Artifacts

- Deterministic scoring tests.
- Embedding service tests.
- Dedup service tests.
- SQLite persistence and processing tests.
- Mocked Qdrant service tests.
- Status transition and application-row tests.
- Full backend regression evidence.
- Explicit Phase 4 handoff confirmation.

### Acceptance Criteria

- Every Plan 3 scoring, dedup, persistence, Qdrant, and status-sync rule has automated coverage.
- Tests use mocks/fakes and do not require live network, OpenAI credentials, or a running Qdrant container.
- Full backend regression suite passes.
- No Plan 4 or Plan 5 behavior is implemented.

### Required Tests or Validations

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_scoring_service.py
pytest tests/test_embedding_service.py
pytest tests/test_dedup_service.py
pytest tests/test_job_processing_service.py
pytest tests/test_job_persistence.py
pytest tests/test_qdrant_service.py
pytest
python -m compileall -q app
```

### Explicit Non-Goals

- Live-provider testing as a mandatory gate.
- Live Qdrant testing as a mandatory gate.
- API endpoint implementation.
- API contract export implementation.
- Seed demo implementation.
- React UI testing.

## Optional Future Tracks

No optional implementation track belongs to Plan 3.

The following work is explicitly outside the mandatory Phase 3 batch chain and must remain in later approved phases:

- FastAPI route handlers for parsing, review, approval, rejection, dashboard, and batch summaries.
- Tavily search orchestration.
- `seed_demo.py` and mock demo data.
- API contract export implementation, except exposing/importing the transition map for Plan 4.
- React dashboard, review queue, score breakdown, metrics panel, and status controls.
- Vector similarity deduplication.
- Schema migrations or database model changes.
- Reprocessing jobs whose Qdrant score failed after initial insertion.

This track is not part of the mandatory MVP batch chain.

## Dependency Chain

- Phase 1/2 foundation -> Batch01
- Batch01 -> Batch02
- Batch01 + Batch02 -> Batch03
- Batch01 + Batch02 + Batch03 -> Batch04

Future-phase tracks are outside this mandatory chain.

## Global Verification Checklist

- [ ] Phase 3 prerequisite modules and schema/index fields are verified before implementation.
- [ ] Runtime statuses and sources use Phase 1 shared constants.
- [ ] Scoring functions are deterministic and normalized to `[0, 1]`.
- [ ] Only `full_jd` and `partial_jd` are embedded and scored.
- [ ] Non-scorable jobs persist as `pending_review` with null score fields and no Qdrant point.
- [ ] Job embedding text uses only clean extracted fields.
- [ ] Role query text is generated dynamically and not stored.
- [ ] Embedding vectors are validated against `EMBEDDING_DIMENSION`.
- [ ] Dedup checks `raw_content_hash` before `dedup_key`.
- [ ] Missing company/title never creates a shared empty dedup key.
- [ ] Duplicates of saved/applied/interview/rejected/offer jobs do not re-enter `pending_review`.
- [ ] New non-duplicate jobs commit to SQLite before OpenAI or Qdrant calls.
- [ ] Embedding or Qdrant failures keep committed SQLite rows visible with null score fields and safe `error_reason`.
- [ ] Qdrant collection initialization and payload indexes are idempotent.
- [ ] Qdrant point IDs use canonical `job_posts.id` UUID strings.
- [ ] Qdrant scoring query filters include active `role_profile_id`, `pending_review`, and current `job_id`.
- [ ] Qdrant write/read visibility failure uses bounded retry and never borrows another job's score.
- [ ] `approve_job`, `reject_job`, and `update_job_status` are the only backend status mutation entrypoints intended for routes.
- [ ] Application-row creation/update follows the approved `applied_at` semantics.
- [ ] Manual tracked `rejected` updates Qdrant payload; review rejection to `ignored` deletes the point.
- [ ] Focused Plan 3 tests and full backend tests pass.
- [ ] Implementation code is clean, idiomatic, typed where appropriate, and easy to understand.
- [ ] No schema changes, routes, Tavily search, demo seed data, mock data, React UI, or vector deduplication were added.

## Progress Tracker

### Batches

- [ ] Batch01 - Scoring and Embedding Foundations
- [ ] Batch02 - Deduplication and SQLite-First Persistence
- [ ] Batch03 - Qdrant Sync and Status Mutation Services
- [ ] Batch04 - Verification and Phase Boundary Tests

### Task IDs

#### Batch01

- [x] (01A): Verify Phase 3 prerequisites and schema compatibility
- [x] (01B): Implement deterministic scoring and clean text builders
- [x] (01C): Implement embedding provider service and vector validation

#### Batch02

- [x] (02A): Implement null-safe deduplication service
- [x] (02B): Implement extraction-state to job persistence mapping
- [x] (02C): Implement SQLite-first processing result and duplicate persistence behavior

#### Batch03

- [x] (03A): Implement Qdrant collection, payload, and filter service
- [x] (03B): Integrate scorable job embedding, Qdrant scoring, and SQLite score update
- [x] (03C): Implement status transitions, application rows, and Qdrant status sync

#### Batch04

- [x] (04A): Verify scoring and embedding foundations
- [x] (04B): Verify deduplication and SQLite persistence behavior
- [x] (04C): Verify Qdrant service, scorable pipeline, and status sync behavior
- [x] (04D): Run full Phase 3 verification and confirm handoff boundary

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
