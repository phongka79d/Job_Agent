# Review Report: Plan_1 to Plan_5 vs Master_Plan

## 1. Executive Summary

The five phase plans are aligned with `Master_Plan.md` and with each other. The previous blockers have been resolved: Plan 3 now uses Qdrant as the canonical semantic similarity source, Plan 4 demo reset handles dependent `applications` rows, Plan 3/4/5 agree on `job_ids` to full job DTO response shaping, and warning handling is consistently ingestion-level with persisted job-card errors coming from `Job.error_reason`.

- Overall readiness score: 100 / 100
- Biggest strengths:
  - Clear phase ownership from backend foundation through frontend MVP.
  - Master stack, single root `.env`, local SQLite, local Qdrant, and React/Vite boundaries are preserved.
  - Extraction, scoring, persistence, Qdrant sync, route formatting, and frontend rendering have clean handoffs.
  - Demo reset, duplicate handling, status sync, and warning propagation are now explicitly testable.
- Biggest risks:
  - None blocking. Remaining implementation risk is normal execution risk covered by the verification plans.
- Verdict: Approved

## 2. Source of Truth Check

| Source-of-Truth Area | Status | Notes |
|---|---|---|
| Core stack | Pass | Plans use FastAPI, LangChain/LangGraph, SQLite, Qdrant Local, and React + TypeScript + Vite. |
| Environment model | Pass | Single root `.env` is preserved; frontend env files are explicitly forbidden. |
| Infrastructure | Pass | Only Qdrant uses Docker Compose; SQLite remains a local file. |
| Database schema | Pass | Plans define only `role_profiles`, `job_posts`, and `applications`; no non-Master columns or tables are introduced. |
| API contracts | Pass | Master endpoints are covered; `status=tracked` is a route-query convenience for the tracked dashboard without schema drift. |
| Status and sync rules | Pass | Plan 3 owns status/application/Qdrant side effects; Plan 4 routes delegate to services. |
| Vector-store behavior | Pass | Plan 3 now uses Qdrant query scores as canonical `embedding_similarity`. |
| MVP scope | Pass | No auth, organizations, cover letters, auto-apply, browser scraping, Celery, Redis, or hidden analytics tables. |
| Testing and demo readiness | Pass | Demo seed, reset-after-application, Qdrant sync, route, backend, and frontend checks are covered. |

## 3. Individual Plan Scores

### Plan_1.md

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with Master Plan | 10 | Matches the stack, root env, SQLite schema, indexes, and Qdrant Compose requirements. |
| Correct phase scope | 10 | Owns foundation only and excludes extraction, scoring, routes, Qdrant client behavior, and frontend. |
| Completeness | 10 | Covers package layout, dependencies, config, logging, async SQLAlchemy, PRAGMAs, models, indexes, and bootstrap. |
| Technical specificity | 10 | Lists exact env keys, table columns, allowed statuses, indexes, commands, and expected DB outputs. |
| Dependency handoff quality | 10 | Gives Plan 2 stable settings, package layout, session utilities, and model contracts. |
| Consistency with other plans | 10 | Later plans consume the schema without renaming fields or adding hidden tables. |
| Implementation readiness | 10 | A coding agent can execute the setup directly from the steps and commands. |
| MVP simplicity | 10 | Avoids `search_runs`, users, organizations, analytics, and vector metadata tables. |
| Risk control and error handling | 10 | Foreign keys, WAL, schema boundaries, and application-row delete behavior for demo reset are documented. |
| Testability | 10 | Includes import, DB init, table/index, PRAGMA, FK behavior, and Qdrant Compose checks. |

- Strengths: Strong storage and configuration contract.
- Problems: None.
- Missing details: None.
- Conflicts with Master Plan / other plans: None.
- Specific fixes required: None.

### Plan_2.md

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with Master Plan | 10 | Matches LangGraph state tracking, trafilatura parsing, retry-once extraction, JD statuses, and fallback behavior. |
| Correct phase scope | 10 | Owns extraction and parsing only; excludes persistence, scoring, Qdrant, Tavily routes, and UI. |
| Completeness | 10 | Covers schemas, prompts, raw text, URL cleaning, fallback states, observability fields, and warning state. |
| Technical specificity | 10 | Defines exact `JobAgentState`, `JobPostExtract`, source mapping, low-content threshold, and fallback output. |
| Dependency handoff quality | 10 | Hands parse status, extracted job, hashes, warnings, observability fields, and nullable score placeholders to Plan 3. |
| Consistency with other plans | 10 | Does not persist or score early, and maps warnings through Plan 3 result warnings. |
| Implementation readiness | 10 | Concrete modules, helper behavior, and failure states are specified. |
| MVP simplicity | 10 | Keeps parsing to `httpx` + `trafilatura`; no Playwright/browser rendering. |
| Risk control and error handling | 10 | Covers invalid JSON, retry failure, low-content URLs, invalid schemes, timeouts, oversized responses, and state preservation. |
| Testability | 10 | Mocked tests cover success, retry, failure, URL cleaning, state preservation, and observability fields. |

- Strengths: Strong fallback and state-preservation contract.
- Problems: None.
- Missing details: None.
- Conflicts with Master Plan / other plans: None.
- Specific fixes required: None.

### Plan_3.md

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with Master Plan | 10 | Implements Master scoring, JD confidence, dedup, smart embedding, Qdrant similarity, point IDs, and status sync. |
| Correct phase scope | 10 | Owns scoring, embeddings, deduplication, persistence, Qdrant sync, and status/application service behavior only. |
| Completeness | 10 | Covers deterministic scores, Qdrant query scoring, null-safe dedup, SQLite persistence, Qdrant init/upsert/delete/update/filter behavior. |
| Technical specificity | 10 | Gives exact formulas, alias table, duplicate policy, pipeline order, Qdrant failure behavior, and result object. |
| Dependency handoff quality | 10 | Receives Plan 2 state and exposes service methods/results for Plan 4, including `job_ids` and warnings. |
| Consistency with other plans | 10 | Centralizes status/application/Qdrant side effects and requires Plan 4 to fetch full job rows for responses. |
| Implementation readiness | 10 | Concrete service files, helpers, order of operations, and tests are listed. |
| MVP simplicity | 10 | Uses local Qdrant and SQLite only; no vector dedup or non-MVP infrastructure. |
| Risk control and error handling | 10 | Handles embedding failures, Qdrant scoring failures, Qdrant sync failures, idempotent deletes, and SQLite `IntegrityError`. |
| Testability | 10 | Strong unit, integration, persistence, dedup, and mocked Qdrant test coverage. |

- Strengths: Strong backend service boundary with Master-aligned Qdrant similarity.
- Problems: None.
- Missing details: None.
- Conflicts with Master Plan / other plans: None.
- Specific fixes required: None.

### Plan_4.md

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with Master Plan | 10 | Implements required API routes, Tavily search, manual URL/text, mock load, review, dashboard, status, summary, and demo seed. |
| Correct phase scope | 10 | Owns HTTP validation/formatting, API schemas, search service, demo loader, seed script, and mock data. |
| Completeness | 10 | Covers endpoints, CORS, response shapes, full job DTO response shaping, seed reset order, mock data, and route tests. |
| Technical specificity | 10 | Provides concrete payloads, SQL queries, transitions, batch aggregation formulas, reset filters, and demo dataset composition. |
| Dependency handoff quality | 10 | Consumes Plan 3 services and hands stable API contracts, full jobs, warnings, and metrics to Plan 5. |
| Consistency with other plans | 10 | Routes delegate business logic to Plan 3 and warning semantics match Plan 5. |
| Implementation readiness | 10 | Route, search, mock-load, demo seed, reset, and response shaping tasks are executable. |
| MVP simplicity | 10 | `status=tracked` is a small query convenience; no hidden infrastructure or extra tables. |
| Risk control and error handling | 10 | Covers Tavily failure, per-URL failure continuation, invalid transitions, secret exposure, Qdrant sync delegation, and reset-after-application safety. |
| Testability | 10 | Route, seed, reset-after-application, CORS, duplicate exclusion, status sync, response shaping, and batch summary tests are specified. |

- Strengths: Clear API-service boundary and demo readiness.
- Problems: None.
- Missing details: None.
- Conflicts with Master Plan / other plans: None.
- Specific fixes required: None.

### Plan_5.md

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with Master Plan | 10 | Implements React dashboard/review workflow, score breakdown, metrics, ingestion, approval/rejection, and manual status updates. |
| Correct phase scope | 10 | Owns only frontend app, API client, UI state, rendering, and frontend tests. |
| Completeness | 10 | Covers profile creation, ingestion controls, review queue, tracked dashboard, metrics, warnings, errors, score breakdown, and states. |
| Technical specificity | 10 | Provides client functions, TypeScript contracts, active batch lifecycle, status dropdown rules, and verification steps. |
| Dependency handoff quality | 10 | Consumes Plan 4 contracts and does not redesign backend behavior. |
| Consistency with other plans | 10 | Uses `status=tracked`, full job DTOs, ingestion-level warnings, and `Job.error_reason` consistently. |
| Implementation readiness | 10 | Clear file structure, dependencies, components, client functions, and manual checks. |
| MVP simplicity | 10 | Work-focused app UI with no frontend secrets or direct OpenAI/Tavily/Qdrant/SQLite access. |
| Risk control and error handling | 10 | Covers loading, empty, disabled, validation error, terminal status, null score, warning, and mobile layout states. |
| Testability | 10 | Build, typecheck, Vitest/jsdom setup, API mocks, low-content warning checks, and manual demo verification are included. |

- Strengths: Complete frontend workflow that respects backend as source of truth.
- Problems: None.
- Missing details: None.
- Conflicts with Master Plan / other plans: None.
- Specific fixes required: None.

## 4. Cross-Phase Consistency Review

- Phase 1 -> Phase 2: Pass. Plan 2 consumes stable config, dependencies, package layout, and model/session contracts without touching persistence.
- Phase 2 -> Phase 3: Pass. Plan 3 consumes `JobAgentState`, `JobPostExtract`, parse status, hashes, warnings, observability fields, and nullable score placeholders.
- Phase 3 -> Phase 4: Pass. Plan 4 calls Plan 3 services for processing/status/Qdrant/application behavior and fetches full job DTOs from `job_ids`.
- Phase 4 -> Phase 5: Pass. Plan 5 consumes full `jobs`, ingestion-level `warnings`, `Job.error_reason`, `status=tracked`, batch summary, and stable route contracts.

## 5. Duplicated Work Review

| Duplicate Area | Found In | Problem | Recommended Owner Phase |
|---|---|---|---|
| Scoring formulas | Plan 3 / Plan 5 | No duplication; frontend only formats backend score fields. | Plan 3 |
| Status/Qdrant/application mutation | Plan 3 / Plan 4 | No duplication; routes must call service methods. | Plan 3 |
| Demo loading | Plan 4 mock-load / `seed_demo.py` | Shared through `demo_loader.py`; no duplicated loader logic. | Plan 4 |
| Warning handling | Plans 2-5 | No schema drift; warnings are transient and job cards use persisted `error_reason`. | Plan 2 creates, Plan 3 propagates, Plan 4 returns, Plan 5 displays |
| Semantic similarity | Master / Plan 3 | No conflict; Plan 3 uses Qdrant query scores as canonical similarity. | Plan 3 |

## 6. Missing Work Review

| Missing Item | Required By Master Plan Section | Impact | Recommended Phase |
|---|---|---|---|
| None | - | All Master-required MVP capabilities are assigned and testable. | - |

## 7. Conflict Review

| Conflict | Location | Why It Is a Problem | Fix |
|---|---|---|---|
| None | - | Current phase plans align with the master and each other. | - |

## 8. Architecture Drift Review

| Drift Risk | Severity | Why It Matters | Prevention |
|---|---|---|---|
| None blocking | Low | The remaining risk is normal implementation quality risk. | Follow each plan's verification gates and preserve phase boundaries. |

## 9. Specific Rewrite Instructions

### Plan_1.md Fixes
```text
No rewrite required.
```

### Plan_2.md Fixes
```text
No rewrite required.
```

### Plan_3.md Fixes
```text
No rewrite required.
```

### Plan_4.md Fixes
```text
No rewrite required.
```

### Plan_5.md Fixes
```text
No rewrite required.
```

## 10. Recommended Final Phase Boundary

| Phase | Owns | Must Not Own |
|---|---|---|
| Plan 1 | Backend skeleton, dependencies, root env example, SQLite schema/indexes/PRAGMAs, Qdrant Docker Compose, minimal FastAPI bootstrap. | Extraction, scoring, Qdrant client code, API workflows, frontend. |
| Plan 2 | LangGraph state, Pydantic extraction schema, prompts, URL/text cleaning, retry/fallback extraction, warning state. | SQLite writes, scoring, embeddings, Qdrant, Tavily routes, frontend. |
| Plan 3 | Scoring, embeddings, deduplication, SQLite job persistence, Qdrant similarity/sync, status/application service side effects. | FastAPI route formatting, Tavily search route, demo files, React UI. |
| Plan 4 | FastAPI routes, API schemas, Tavily search service, demo loader, `seed_demo.py`, mock data, batch summaries. | Reimplementing scoring/dedup/persistence/Qdrant/status logic. |
| Plan 5 | React app, API client, profile/ingestion/review/tracked dashboard UI, metrics, score display, frontend tests. | Backend secrets, direct OpenAI/Tavily/Qdrant/SQLite access, backend scoring. |

## 11. Final Verdict

Approved.

All supplied plans are approved with no remaining rewrite instructions.

## 12. Final Score Summary

| Plan | Score / 100 | Verdict |
|---|---:|---|
| Plan_1.md | 100 | Approved |
| Plan_2.md | 100 | Approved |
| Plan_3.md | 100 | Approved |
| Plan_4.md | 100 | Approved |
| Plan_5.md | 100 | Approved |
