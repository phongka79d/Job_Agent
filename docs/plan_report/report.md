# Review Report: Plan_1 to Plan_4 vs Master_Plan

## 1. Executive Summary

The 4 phase plans are largely ready, but should receive targeted edits before implementation.

- Overall readiness score: 90 / 100
- Biggest strengths: strong phase separation, correct MVP stack, explicit exclusion of PostgreSQL/GraphRAG/Neo4j/Jina/auth/auto-apply, good SQLite/Qdrant detail, strong fallback and test planning.
- Biggest risks: Phase 4 review/dashboard queries omit explicit `role_profile_id` filtering, batch summary counters are under-specified for skipped duplicates, Phase 3 leaves small room for schema ownership drift, and Phase 2 handoff wording ambiguously says Phase 3/4 decide persistence.
- Recommendation: Approved with minor edits. Apply the fixes below before assigning implementation agents.

## 2. Source of Truth Check

`Master_Plan.md` defines a local-first MVP:

- Frontend: React + TypeScript + Vite
- Backend: FastAPI
- Agent flow: LangChain + LangGraph + Pydantic structured output
- Database: SQLite via `sqlite+aiosqlite`
- Vector DB: Qdrant Local via Docker Compose
- URL extraction: `httpx` + `trafilatura`
- Search: Tavily or similar public API
- Config: single root `.env`
- No PostgreSQL, Qdrant Cloud, GraphRAG, Neo4j, Jina Reranker, auto-apply, authenticated social crawler, auth/multi-user system, Celery/Redis, or extra frontend/backend env files.

Architecture decision check:

| Required Decision | Status | Notes |
|---|---|---|
| SQLite, not PostgreSQL | Pass | All plans explicitly reject PostgreSQL. |
| Qdrant Local, not Qdrant Cloud | Pass | Docker Compose local Qdrant only. |
| FastAPI backend | Pass | Phase 4 owns routes. |
| React + TypeScript + Vite frontend | Pass | Phase 4 owns frontend. |
| LangChain/LangGraph | Pass | Phase 2 extraction graph, Phase 3 extension. |
| Pydantic structured output | Pass | Phase 2 is specific. |
| `httpx` + `trafilatura` | Pass | Phase 2 owns URL extraction. |
| No GraphRAG | Pass | Explicitly excluded. |
| No Neo4j | Pass | Explicitly excluded. |
| No Jina Reranker | Pass | Explicitly excluded. |
| No auto-apply | Pass | Explicitly excluded. |
| No LinkedIn/Facebook authenticated crawler | Pass | Explicitly excluded. |
| No auth/multi-user | Pass | Explicitly excluded. |
| Single root `.env` | Pass | Strongly enforced. |

## 3. Individual Plan Scores

### 3.1 Plan_1.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 10 | Strong match to SQLite, Qdrant Local, root `.env`, schema. |
| Correct phase scope | 10 | Correctly avoids APIs, extraction, scoring, Qdrant vectors, UI. |
| Completeness | 10 | Includes tables, indexes, constraints, config, scripts, verification. |
| Technical specificity | 10 | Very specific SQLAlchemy, PRAGMA, path, and verification details. |
| Dependency handoff quality | 9 | Good handoff; minor risk from installing all later deps in Phase 1. |
| Consistency with other plans | 10 | Supports Phase 2/3/4 cleanly. |
| Implementation readiness | 10 | Directly executable. |
| MVP simplicity | 9 | Slightly heavy constraints/checks, but acceptable. |
| Risk control and error handling | 9 | Good schema verification; no runtime app behavior yet. |
| Testability | 9 | Strong verify script plan, but no pytest smoke test required. |

Overall score: 96 / 100

Strengths:

- Correctly owns only foundation work.
- Strong PostgreSQL prevention.
- Correct partial unique index for `raw_content_hash`.
- Correct root `.env` handling.
- Correct `job_posts.batch_id` instead of `search_runs`.

Problems:

- Later-phase dependencies are installed in Phase 1. The plan explains this as bootstrap-only, so it is acceptable but should stay dependency-only.
- Phase 1 is the schema owner, but Phase 3 later says it may patch models if Phase 1 missed fields. That weakens ownership.

Missing details:

- Add an explicit Phase 1 acceptance item that later phases must not silently mutate Phase 1 schema; schema misses should be fixed by revising Phase 1 output or a documented migration.

Conflicts with `Master_Plan.md`:

- None material.

Conflicts with other phase plans:

- Minor conflict with Plan 3 allowing model/schema fixes in Phase 3.

Specific fixes required:

- Add a note that Phase 1 is the canonical schema source for MVP tables/indexes and later phases should verify, not silently redesign, schema.

### 3.2 Plan_2.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Strong extraction alignment. |
| Correct phase scope | 9 | Avoids scoring/Qdrant/API/UI; one handoff phrase is ambiguous. |
| Completeness | 9 | Covers URL/manual text, schema, retry, fallback, observability. |
| Technical specificity | 9 | Strong service, graph, and test details. |
| Dependency handoff quality | 9 | Good Phase 1 inputs and Phase 3 outputs. |
| Consistency with other plans | 9 | Mostly clean; persistence ownership wording needs tightening. |
| Implementation readiness | 9 | Executable with tests and clear contracts. |
| MVP simplicity | 9 | Avoids Playwright/custom parser. |
| Risk control and error handling | 10 | Strong fallback and no-batch-crash behavior. |
| Testability | 10 | Excellent mocked LLM and extraction test plan. |

Overall score: 92 / 100

Strengths:

- Correctly owns `httpx` + `trafilatura`.
- Correctly handles `needs_manual_input`.
- Strong `JobAgentState` preservation.
- Correct retry-once repair flow.
- Correctly keeps score fields null and Qdrant out of scope.

Problems:

- Handoff says “Phase 3/4 decide the persistence implementation details.” That can let Phase 4 reimplement storage. Master boundaries say Phase 3 owns persistence rules/services and Phase 4 only calls them.
- Fallback state includes `error_reason`, but the frontend warning contract depends on a stable user-facing warning. This should be explicitly mapped.

Missing details:

- Add an explicit test that Phase 2 never writes SQLite job records.
- Add explicit fallback defaults for token/cost/time fields when extraction fails before LLM usage.

Conflicts with `Master_Plan.md`:

- No direct architecture conflict.

Conflicts with other phase plans:

- Minor ambiguity with Plan 3/4 persistence ownership.

Specific fixes required:

- Tighten handoff language so Phase 3 owns final SQLite persistence and Phase 4 owns only route orchestration.

### 3.3 Plan_3.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Strong scoring/dedup/Qdrant alignment. |
| Correct phase scope | 9 | Correctly owns scoring/storage/Qdrant sync services. |
| Completeness | 9 | Very detailed, but batch summary contract needs expansion. |
| Technical specificity | 9 | Strong scoring, dedup, Qdrant payload/index rules. |
| Dependency handoff quality | 8 | Good from Phase 2, but Phase 4 summary handoff is incomplete. |
| Consistency with other plans | 8 | Some overlap risk with Phase 1 schema and Phase 4 pipeline. |
| Implementation readiness | 9 | Implementation-ready with fake embeddings/Qdrant tests. |
| MVP simplicity | 8 | Mostly simple; vector update/manual correction rules may be extra. |
| Risk control and error handling | 9 | Good Qdrant failure and transaction handling. |
| Testability | 10 | Excellent unit-test plan. |

Overall score: 88 / 100

Strengths:

- Correct scoring formula and JD confidence multiplier.
- Correctly avoids vector deduplication.
- Correctly handles duplicate statuses.
- Correct Qdrant UUID point ID rule.
- Correct approve/reject/update/delete sync service ownership.

Problems:

- Says Phase 3 may update `models.py` if Phase 1 missed fields. That can blur Phase 1 schema ownership.
- Batch summary contract omits some fields Phase 4 expects: `failed_extractions`, token totals, cost totals, and average extraction time.
- Semantic similarity wording allows local cosine or Qdrant equivalent. That is acceptable technically, but should be clearer so Qdrant does not become optional for MVP vector behavior.
- “Non-scorable becomes scorable after manual correction” is likely future behavior unless Phase 4 implements job editing.

Missing details:

- Add a precise `BatchSummaryCounters` contract shared with Phase 4.
- Add saved-dashboard Qdrant filter helper or explicitly state SQL dashboard queries remain primary and Qdrant filters are only for vector search.

Conflicts with `Master_Plan.md`:

- No major conflict.
- Minor risk: Master describes Qdrant similarity; Plan 3 permits local cosine. This should be clarified as equivalent scoring math while still using Qdrant for vector storage/search.

Conflicts with other phase plans:

- Minor conflict with Plan 1 schema ownership.
- Potential overlap with Phase 4 if `job_pipeline_service.py` reimplements storage instead of calling Phase 3.

Specific fixes required:

- Make Phase 3 verify schema and fail clearly if Phase 1 is wrong, instead of silently changing schema.
- Expand the batch summary handoff.

### 3.4 Plan_4.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Strong integration/UI alignment. |
| Correct phase scope | 9 | Correctly owns API/UI/demo; must avoid service rewrites. |
| Completeness | 9 | Very complete, but route filtering and summary semantics need fixes. |
| Technical specificity | 8 | Good DTO/UI detail; query params need more precision. |
| Dependency handoff quality | 8 | Good reuse language, but summary contract and loader path need tightening. |
| Consistency with other plans | 8 | Mostly good; batch counters and pipeline ownership need care. |
| Implementation readiness | 8 | Needs small edits before execution. |
| MVP simplicity | 8 | Generally practical; offline vectors are useful but must stay isolated. |
| Risk control and error handling | 9 | Good warnings, partial failures, sync warnings. |
| Testability | 9 | Strong backend/frontend/E2E coverage. |

Overall score: 85 / 100

Strengths:

- Correctly owns FastAPI, React, demo seed, route orchestration, and UI.
- Strong single-root `.env` protection.
- Good warning/duplicate/sync-warning UI behavior.
- Correctly says Phase 4 must reuse Phase 2/3 services.
- Strong demo flow.

Problems:

- Review and dashboard query rules omit `role_profile_id = ?`, even though Master Plan requires role-profile isolation.
- `GET /api/jobs/review` and `GET /api/jobs` do not explicitly require `role_profile_id`.
- `GET /api/batches/{batch_id}/summary` includes skipped exact duplicates even though skipped rows are not reconstructable without a persisted summary or in-memory current-run summary.
- Shared demo loader is required, but no clear file such as `backend/app/services/demo_loader.py` is listed.
- Demo data scorable-count semantics are ambiguous: “unrelated jobs” should show low scores, but expected output says only 8 scorable jobs.

Missing details:

- Active/selected role profile propagation in frontend dashboard/review pages.
- Exact summary behavior after process restart.
- Allowed status transitions should be explicit enough to avoid `saved -> ignored` surprises unless intentionally allowed.

Conflicts with `Master_Plan.md`:

- Query conflict: Master dashboard/review SQL filters by `role_profile_id`; Plan 4 query rules omit it.
- Summary conflict: Master avoids extra batch/analytics tables, but Plan 4’s GET summary implies counters that cannot all be reconstructed.

Conflicts with other phase plans:

- Potential overlap if `job_pipeline_service.py` duplicates Phase 3 storage/scoring/dedup/Qdrant sync.
- Batch summary contract does not fully match Plan 3.

Specific fixes required:

- Add required `role_profile_id` filters and request/query DTOs.
- Add shared demo loader file and contract.
- Resolve batch summary reconstructability.

## 4. Cross-Phase Consistency Review

### Phase 1 → Phase 2

| Handoff Item | Status | Notes |
|---|---|---|
| Config system | Pass | Root `.env` and typed settings provided. |
| Database session | Pass | `session.py` provided, though Phase 2 should not persist jobs. |
| Project structure | Pass | `agents`, `services`, `core`, `db` folders exist. |
| Dependency setup | Pass | Includes LangChain, LangGraph, httpx, trafilatura. |
| `.env` | Pass | Single root `.env`. |
| Local database path | Pass | `backend/data/job_matching.db`. |

Assessment: Good handoff.

### Phase 2 → Phase 3

| Handoff Item | Status | Notes |
|---|---|---|
| Extracted job object | Pass | `JobPostExtract` / `extracted_job`. |
| `jd_status` | Pass | Explicit. |
| `should_score_similarity` | Pass | Explicit. |
| Source metadata | Pass | `source_url`, `source_platform`, `input_source`. |
| `raw_content_hash` | Pass | Strong contract. |
| Extraction status | Pass | `success/retried/failed`. |
| Error reason | Pass | Explicit. |
| Token/cost fields | Mostly pass | Present, but fallback defaults should be explicit. |
| LangGraph state preservation | Pass | Strong required-key tests. |

Assessment: Good, with minor persistence-ownership wording fix.

### Phase 3 → Phase 4

| Handoff Item | Status | Notes |
|---|---|---|
| Stored jobs | Pass | `job_storage_service.py`. |
| Score fields | Pass | Stored score breakdown fields. |
| Status fields | Pass | `pending_review/saved/...`. |
| Qdrant sync behavior | Pass | Service functions. |
| Approve/reject behavior | Pass | Phase 3 services, Phase 4 routes. |
| Batch/job summary data | Needs fix | Missing full shared contract for skipped duplicates and metrics. |
| Dashboard-ready query behavior | Needs fix | Plan 4 must include `role_profile_id` filter. |

Assessment: Mostly good, but Phase 4 needs query and summary contract edits.

## 5. Duplicated Work Review

| Duplicate Area | Found In | Problem | Recommended Owner Phase |
|---|---|---|---|
| Config updates | Plans 1, 2, 3, 4 | Later phases may mutate config casually. | Phase 1 owns base config; later phases add only missing typed fields. |
| DB schema/model fixes | Plans 1 and 3 | Phase 3 should not silently repair Phase 1 schema. | Phase 1 owns schema; Phase 3 verifies. |
| LangGraph files | Plans 2 and 3 | Phase 3 extends graph; could overwrite Phase 2 extraction graph. | Phase 2 owns extraction graph; Phase 3 appends processing nodes. |
| Raw content hash | Plans 2 and 3 | Recompute rules could diverge. | Phase 2 owns hash generation; Phase 3 consumes/recomputes only reliable missing hash. |
| Storage/pipeline orchestration | Plans 3 and 4 | Phase 4 could duplicate scoring/dedup/storage logic. | Phase 3 owns storage/scoring; Phase 4 owns route orchestration. |
| Qdrant sync | Plans 3 and 4 | Routes might implement sync directly. | Phase 3 owns sync services; Phase 4 calls them. |
| Batch summary counters | Plans 3 and 4 | Counter reconstructability is unclear. | Phase 3 owns immediate counters; Phase 4 exposes/aggregates. |
| Demo seed and mock-load | Plan 4 script/API | Duplicate seed logic possible. | Phase 4 owns one shared demo loader used by both. |

## 6. Missing Work Review

| Missing Item | Required By Master Plan Section | Impact | Recommended Phase |
|---|---|---|---|
| Explicit `role_profile_id` filter for review/dashboard API queries | Section 25 | Cross-profile job leakage and wrong dashboard results. | Phase 4 |
| Request/query DTOs for `GET /api/jobs/review` and `GET /api/jobs` with `role_profile_id` | Section 25 / 27 | Frontend cannot reliably select active profile. | Phase 4 |
| Durable semantics for `skipped_exact_duplicate` in `GET /api/batches/{batch_id}/summary` | Sections 16, 17, 27 | API may report fake or unreconstructable counts. | Phase 4 with Phase 3 handoff |
| Shared demo loader file path/contract | Section 6 / 35 | Seed script and mock-load may diverge. | Phase 4 |
| Explicit fallback token/cost/time defaults | Sections 5.1, 16, 19 | Metrics may be null/inconsistent after failed extraction. | Phase 2 |
| Clear demo category `jd_status` / scorable mapping | Section 6 | Demo may fail to show both low-score and non-scorable examples. | Phase 4 |
| Status transition policy for manual updates | Section 20 | User actions could bypass intended HITL flow. | Phase 4 |

Items checked and present:

| Required Item | Status |
|---|---|
| SQLite indexes and constraints | Present in Plan 1 |
| Partial unique indexes | Present in Plan 1 |
| `raw_content_hash` | Present in Plans 1/2/3 |
| `dedup_key` | Present in Plans 1/3 |
| `duplicate_of_job_id` | Present in Plans 1/3/4 |
| Qdrant payload indexes | Present in Plan 3 |
| Qdrant UUID point ID rule | Present in Plans 1/3 |
| Reject deletes vector | Present in Plans 3/4 |
| Approve updates Qdrant payload | Present in Plans 3/4 |
| JD status rules | Present in Plans 2/3 |
| `contact_for_jd` handling | Present in Plans 2/3/4 |
| `needs_manual_input` handling | Present in Plans 2/4 |
| Metrics fields | Present across Plans 1/2/4 |
| Seed demo data | Present in Plan 4 |
| Frontend warning for failed URL extraction | Present in Plan 4 |

## 7. Conflict Review

| Conflict | Location | Why It Is a Problem | Fix |
|---|---|---|---|
| Review/dashboard queries omit `role_profile_id` | Plan 4, API query rules | Violates Master SQL and can leak jobs across profiles. | Add `role_profile_id = ?` and require query param. |
| Phase 3 may patch models if Phase 1 missed fields | Plan 3 target structure/steps | Blurs schema ownership and hides Phase 1 failures. | Change to verify/fail; fix Phase 1 schema before Phase 3. |
| Persistence wording says Phase 3/4 decide details | Plan 2 handoff | Could allow Phase 4 to implement persistence logic. | State Phase 3 owns persistence; Phase 4 calls service. |
| Batch summary includes unreconstructable skipped duplicates | Plan 4 summary endpoint | No `search_runs` table; skipped rows are not stored. | Define immediate response vs persisted summary behavior. |
| Local cosine vs Qdrant similarity wording | Plan 3 scoring | Could make Qdrant appear optional for vector behavior. | Clarify scoring math and Qdrant storage/search responsibilities. |
| Demo scorable count ambiguity | Plan 4 demo data/output | Unrelated jobs cannot both be “low scored” and excluded from scorable count unless defined. | Add category table with expected `jd_status` and `should_score_similarity`. |
| Manual status values include `ignored` broadly | Plan 4 StatusSelect/API rules | May bypass intended `pending_review -> ignored` path. | Add allowed transition table or explicitly allow with Qdrant delete. |
| Shared loader required but no file listed | Plan 4 seed/mock-load | Script/API seed paths may diverge. | Add `backend/app/services/demo_loader.py`. |

## 8. Architecture Drift Review

| Drift Risk | Severity | Why It Matters | Prevention |
|---|---|---|---|
| Phase 4 reimplements Phase 3 scoring/storage/dedup/Qdrant sync | High | Duplicates core architecture and creates inconsistent behavior. | Route handlers must call Phase 3 public services only. |
| Missing `role_profile_id` filters | High | Breaks query isolation and demo correctness. | Require `role_profile_id` for review/dashboard endpoints. |
| Adding batch summary table to solve skipped duplicates | Medium | Master says no `search_runs` or deep analytics tables. | Use immediate response/in-memory current-run summary or nullable/reconstructable fields. |
| Phase 3 silently mutates Phase 1 schema | Medium | Creates phase ownership drift. | Treat schema mismatch as Phase 1 revision. |
| Deterministic demo vectors leaking into normal flows | Medium | Demo-only shortcut could corrupt real scoring. | Explicit `--offline-demo-vectors` only; tests prevent normal use. |
| Qdrant/vector deduplication reintroduced | High | Master explicitly removed vector dedup. | Keep dedup tests proving Qdrant is not called during dedup. |
| Playwright/custom parser added for URL extraction | Medium | Increases crawler complexity. | Keep `httpx` + `trafilatura`; manual paste fallback. |
| Frontend `.env` introduced | Medium | Violates single root `.env` and risks secret exposure. | Use hardcoded safe `src/config.ts` or generated safe public config only. |
| Auth/multi-user added early | High | Overcomplicates solo MVP. | Keep single local profile workflow. |
| Jina Reranker/GraphRAG/Neo4j added | High | Expands beyond MVP architecture. | Keep explicit banned dependency checks. |
| PostgreSQL assumptions reappear | Critical | Directly violates stack decision. | Keep dependency and SQL syntax checks. |
| Auto-apply/cover letters added | High | Risky and out of scope. | Keep UI/API scope restricted to review/status tracking. |

## 9. Specific Rewrite Instructions

### Plan_1.md Fixes

```text
1. Add to Section 14 Acceptance Criteria:
   "Later phases must treat this schema as the canonical MVP schema. If required Master Plan columns, constraints, or indexes are missing, the implementation must revise/fix Phase 1 output rather than silently redesign schema in Phase 3."

2. Add to Section 16 Handoff Notes:
   "Phase 3 may verify models and indexes, but should not introduce new schema decisions unless this Phase 1 plan is explicitly revised."

3. Keep the later-phase dependencies note, but add:
   "Implementation agents must not infer ownership of extraction, LangGraph, Qdrant vector, search, or API code from dependency presence."
```

### Plan_2.md Fixes

```text
1. Replace:
   "Phase 3/4 decide the persistence implementation details"
   with:
   "Phase 3 owns final SQLite persistence, scoring, deduplication, and Qdrant sync services. Phase 4 only invokes those services through API orchestration."

2. Add to the fallback requirements:
   "Fallback states must set input_tokens=0, output_tokens=0, estimated_cost_usd=0.0 when no LLM call occurred, and must set extraction_time_ms when measurable."

3. Add a test case:
   "Phase 2 graph execution does not insert or update job_posts rows."

4. Add an optional terminal field or mapping note:
   "The stable manual-input warning text must be available to Phase 4 either through error_reason or a user_warning field; Phase 4 must not invent a different warning."
```

### Plan_3.md Fixes

```text
1. Replace:
   "Only adjust models.py or session.py if Phase 1 implementation missed required Master Plan columns..."
   with:
   "Verify models.py/session.py against Master Plan. If required schema is missing, fail Phase 3 verification and send the fix back to Phase 1 unless an explicit migration task is approved."

2. Add a shared BatchSummaryCounters contract with:
   inserted, scorable, non_scorable, skipped_exact_duplicate, duplicate_ignored,
   qdrant_upserted, qdrant_failed, failed_extractions,
   total_input_tokens, total_output_tokens, total_tokens,
   estimated_cost_usd, average_extraction_time_ms.

3. Clarify semantic similarity:
   "Production scoring must produce the normalized embedding_similarity used by the Master formula and must still upsert scorable jobs to Qdrant. Unit tests may use local cosine with fake embeddings. Qdrant/vector search must not be used for deduplication."

4. Mark manual scorable/non-scorable transitions as service support only:
   "Do not build job-edit UI or routes in Phase 3; expose only service behavior if later phases call it."

5. Add a test:
   "Batch summary counters include failed extraction and token/cost aggregation from persisted job fields."
```

### Plan_4.md Fixes

```text
1. Change API query rules for review queue to:
   "WHERE role_profile_id = :role_profile_id AND status = 'pending_review' AND duplicate_of_job_id IS NULL
    ORDER BY final_score IS NULL, final_score DESC, discovered_at DESC."

2. Change API query rules for dashboard to:
   "WHERE role_profile_id = :role_profile_id AND status = 'saved' AND duplicate_of_job_id IS NULL
    ORDER BY final_score IS NULL, final_score DESC."

3. Add request/query requirement:
   "GET /api/jobs/review and GET /api/jobs require role_profile_id as a query parameter."
   Example: GET /api/jobs/review?role_profile_id=<uuid>.

4. Add frontend requirement:
   "DashboardPage and ReviewQueuePage must require/select an active role profile and pass role_profile_id to API calls."

5. Add:
   "backend/app/services/demo_loader.py"
   to the Phase 4-owned file list, and state that both seed_demo.py and /api/jobs/mock-load call it.

6. Replace BatchSummaryResponse skipped duplicate semantics with:
   "skipped_exact_duplicate is authoritative in immediate pipeline responses. GET /api/batches/{batch_id}/summary may return reconstructed persisted metrics and must document skipped_exact_duplicate as unavailable/null unless preserved in current process memory. Do not add a batch summary table unless Master_Plan changes."

7. Add demo data table with columns:
   category, count, jd_status, should_score_similarity, expected score behavior.
   Resolve whether the 2 unrelated jobs are scored low or non-scorable. Keep the expected output consistent with that choice.

8. Add status transition rules:
   "pending_review may transition to saved or ignored. saved may transition to applied/interview/rejected/offer. If ignored is allowed from saved/tracked states, it must call Phase 3 sync and delete/update Qdrant according to policy."

9. Add backend tests:
   "Review queue and dashboard endpoints filter by role_profile_id."
   "GET batch summary does not invent skipped_exact_duplicate after restart."
```

## 10. Recommended Final Phase Boundary

| Phase | Owns | Must Not Own |
| ----- | ---- | ------------ |
| Phase 1 Foundation | Project structure, venv setup, root `.env`, Qdrant Docker Compose, SQLAlchemy SQLite setup, DB file, core tables, indexes, constraints, backend config foundation | Extraction, LangGraph behavior, scoring, dedup behavior, Qdrant vectors, APIs, React UI |
| Phase 2 AI Extraction & LangGraph | URL/manual text extraction, Pydantic extraction schema, structured output, validation, retry once, `JobAgentState`, extraction graph, `mark_unclear`, extraction observability | Scoring, dedup policy, SQLite final persistence, Qdrant upsert/search/delete, FastAPI routes, React UI, demo seeding |
| Phase 3 Scoring & Storage Sync | Skill normalization, role/job embedding text, scoring formula, JD multiplier, dedup policy, SQLite persistence service, Qdrant collection/payload/upsert/delete, SQLite-Qdrant sync services, batch counter contract | FastAPI routes, React UI, auth, auto-apply, cover letters, GraphRAG, Neo4j, Jina Reranker, Tavily endpoint UI |
| Phase 4 Integration & UI | `seed_demo.py`, mock data, shared demo loader, FastAPI routes, Tavily endpoint orchestration, job pipeline orchestration, React UI, dashboard, review queue, role profiles, demo mode, warnings, metrics, E2E demo | Changing extraction architecture, scoring formula, dedup policy, Qdrant sync rules, schema decisions, second `.env`, auth, auto-apply, future AI features |

## 11. Final Verdict

Approved with minor edits.

The plans are strong and aligned with `Master_Plan.md`. They are specific enough for implementation agents, and the phase boundaries are mostly correct. The required edits are targeted: add role-profile query isolation, tighten persistence ownership, fix summary-counter semantics, prevent schema ownership drift, and clarify demo scorable counts.

Implementation should start after those edits are applied.

## 12. Final Score Summary

| Plan      | Score / 100 | Verdict |
| --------- | ----------: | ------- |
| Plan_1.md | 96 | Approved with minor edits |
| Plan_2.md | 92 | Approved with minor edits |
| Plan_3.md | 88 | Approved with minor edits |
| Plan_4.md | 85 | Needs targeted edits before implementation |
| Overall   | 90 | Approved with minor edits |