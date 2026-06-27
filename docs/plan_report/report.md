# Review Report: Plan_1 to Plan_4 vs Master_Plan

## 1. Executive Summary

The 4 plans are mostly aligned with `Master_Plan.md` and are much stronger than typical implementation plans. They are detailed, phase-aware, and generally safe for a solo-developer MVP.

- Overall readiness score: 83 / 100
- Biggest strengths: clear stack choices, strong SQLite/Qdrant constraints, good test planning, good human-review flow, strong anti-drift rules.
- Biggest risks: Phase 4 names a second source of truth, Phase 3/4 overlap around pipeline orchestration, batch summary persistence is underdefined, and a few edge cases could cause implementation drift.
- Recommendation: Needs revision before implementation, but not a major rewrite.

## 2. Source of Truth Check

`Master_Plan.md` defines a local MVP stack:

- SQLite using `sqlite+aiosqlite`, not PostgreSQL.
- Qdrant Local via Docker Compose, not Qdrant Cloud.
- FastAPI backend.
- React + TypeScript + Vite frontend.
- LangChain/LangGraph agent flow.
- Pydantic structured output.
- `httpx` + `trafilatura` for URL extraction.
- No GraphRAG, Neo4j, Jina Reranker, auto-apply, authenticated social crawling, authentication/multi-user system, or multiple `.env` files.
- Single root `.env`.

The phase plans mostly follow this. The main source-of-truth violation is in `Plan_4.md`, which adds `docs/plan_report/report.md` as priority 2. That must be removed because the user explicitly requires `Master_Plan.md` as the single source of truth.

## 3. Individual Plan Scores

### 3.1 Plan_1.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Strong SQLite/Qdrant/root-env alignment. |
| Correct phase scope | 10 | Foundation only; later behaviors excluded. |
| Completeness | 9 | Tables, indexes, config, Docker, verification covered. |
| Technical specificity | 9 | Very executable. |
| Dependency handoff quality | 8 | Good handoff, but `source_platform` rules could be clearer. |
| Consistency with other plans | 9 | Supports later phases well. |
| Implementation readiness | 9 | Clear steps and verification. |
| MVP simplicity | 8 | Installing all backend deps in Phase 1 is convenient but heavy. |
| Risk control and error handling | 9 | Strong PostgreSQL/env/schema drift checks. |
| Testability | 9 | Good schema verification scripts. |

Overall score: 89 / 100

Strengths:
- Correctly owns schema, config, Qdrant Docker Compose, and SQLite setup.
- Strong partial unique index handling for `raw_content_hash`.
- Good root `.env` resolution requirements.
- Strong anti-PostgreSQL safeguards.

Problems:
- Does not explicitly constrain `source_platform` values.
- `source_platform` is nullable, which is practical early but should be documented as “nullable only before ingestion.”
- Full backend dependency installation in Phase 1 could slow setup, though it is not architecturally wrong.

Missing details:
- Explicit check constraint or validation note for `source_platform`: `tavily`, `manual_url`, `manual_text`, `mock`, `job_board`.
- Whether `applications` table is reserved or expected to be used by Phase 4 status updates.

Conflicts with `Master_Plan.md`:
- No major conflict.

Conflicts with other phase plans:
- None serious.

Specific fixes required:
- Add `source_platform` allowed values.
- Add a handoff note saying Phase 4 must define whether manual application status updates create/update `applications` rows or only update `job_posts.status`.

### 3.2 Plan_2.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Matches extraction, Pydantic, retry, fallback. |
| Correct phase scope | 9 | Avoids scoring/API/UI; minor mock-path ambiguity. |
| Completeness | 9 | Strong URL/manual text/LLM/LangGraph coverage. |
| Technical specificity | 8 | Good, but source platform mapping needs tightening. |
| Dependency handoff quality | 8 | Good state handoff, but fallback persistence wording is too optional. |
| Consistency with other plans | 8 | Mostly consistent. |
| Implementation readiness | 8 | Executable, but quite complex. |
| MVP simplicity | 8 | Reasonable, but extraction graph is detailed. |
| Risk control and error handling | 9 | Strong fallback and no-crash behavior. |
| Testability | 9 | Excellent mocked test plan. |

Overall score: 85 / 100

Strengths:
- Correctly owns `httpx` + `trafilatura`, manual text preparation, Pydantic schema, retry once, `mark_unclear`, and observability.
- Good handling of `needs_manual_input`.
- Good no-real-OpenAI test requirement.
- Preserves required graph state.

Problems:
- Handoff says Phase 3 may persist fallback records “if the pipeline chooses,” but the master architecture expects failed/unclear parsed jobs to be saved as visible pending-review records.
- `source_platform` assignment is not explicit enough for `manual_url`, `manual_text`, `tavily`, and `mock`.
- `manual/mock input` in `prepare_content_node` risks confusing mock support ownership. Phase 2 may support the state shape, but Phase 4 owns mock loading.

Missing details:
- Exact `input_source` to `source_platform` mapping.
- Clear rule that Phase 2 never loads mock files or seed data.
- Explicit terminal-state shape for `needs_manual_input` with warning text.

Conflicts with `Master_Plan.md`:
- Minor: fallback persistence is worded as optional downstream behavior.

Conflicts with other phase plans:
- Minor overlap with Phase 4 around mock input handling.

Specific fixes required:
- Replace “if the pipeline chooses to save fallback records” with “Phase 3/4 must persist controlled `unclear` fallback records unless deduplication skips them.”
- Add explicit source platform mapping.
- Clarify that Phase 2 accepts `input_source="mock"` only as a state value and does not implement demo loading.

### 3.3 Plan_3.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 8 | Strong scoring/dedup/Qdrant alignment. |
| Correct phase scope | 8 | Mostly right; graph/service integration overlaps with Phase 4 orchestration. |
| Completeness | 8 | Good, but batch summary durability is underdefined. |
| Technical specificity | 8 | Strong formulas, weaker duplicate edge cases. |
| Dependency handoff quality | 7 | Needs clearer Phase 4 summary and API handoff. |
| Consistency with other plans | 8 | Mostly consistent. |
| Implementation readiness | 8 | Executable with a few corrections. |
| MVP simplicity | 7 | Qdrant update transitions may be more than MVP needs. |
| Risk control and error handling | 8 | Good Qdrant failure handling. |
| Testability | 8 | Good fake embeddings/Qdrant tests. |

Overall score: 78 / 100

Strengths:
- Correctly owns scoring, deduplication, persistence, Qdrant collection, payloads, filters, and sync service functions.
- Uses exact scoring formula and JD multiplier.
- Correctly avoids vector deduplication.
- Correctly keeps FastAPI routes and UI out of Phase 3.

Problems:
- “Run deduplication before scoring when possible” is too vague. Dedup should be mandatory whenever `raw_content_hash` or valid `dedup_key` exists.
- Missing rule for `dedup_key` when title/company are missing. Hashing empty values could collapse unrelated unclear jobs.
- Batch summary counters are prepared, but skipped exact duplicates are not persisted anywhere. Phase 4 cannot reliably reconstruct them from `job_posts`.
- Acceptance checklist says Qdrant payload indexes are “planned” instead of created and verified.
- Phase 3 graph integration and Phase 4 pipeline orchestration need a cleaner boundary.

Missing details:
- `dedup_key = None` when normalized company or title is missing/empty.
- Clear return object from storage service containing `stored_job_id`, `dedup_action`, counters, and warnings.
- Whether historical batch summaries are approximate or immediate-response only without a batch table.

Conflicts with `Master_Plan.md`:
- Minor: payload indexes should be created, not merely planned.
- Minor: deduplication should not be optional when required inputs exist.

Conflicts with other phase plans:
- Potential overlap with Plan 4’s `job_pipeline_service.py`.

Specific fixes required:
- Make deduplication mandatory before scoring when identifiers exist.
- Add missing-title/company `dedup_key` behavior.
- Define exact `StoredJobResult` / batch counter contract for Phase 4.
- Change “payload indexes are planned” to “created and verified.”
- State that Phase 4 calls Phase 3’s combined processing function or graph, not duplicate its logic.

### 3.4 Plan_4.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 8 | Mostly aligned, but adds another source of truth. |
| Correct phase scope | 8 | Correct broad integration phase. |
| Completeness | 8 | Strong UI/API/demo coverage; DTO gaps remain. |
| Technical specificity | 8 | Good endpoints and flows. |
| Dependency handoff quality | 8 | Good reuse requirement, but orchestration boundary needs tightening. |
| Consistency with other plans | 7 | Some overlap with Phase 3 pipeline/graph. |
| Implementation readiness | 8 | Executable after edits. |
| MVP simplicity | 7 | Large scope; frontend + API + seed + search is heavy. |
| Risk control and error handling | 8 | Good warnings and partial failure handling. |
| Testability | 8 | Good backend/frontend/e2e tests. |

Overall score: 78 / 100

Strengths:
- Correctly owns FastAPI routes, React UI, seed demo, Tavily integration, score breakdown UI, metrics UI, and demo flow.
- Good warning behavior for `needs_manual_input`.
- Correctly keeps seeded jobs as `pending_review`.
- Good no-secrets-in-frontend rules.

Problems:
- Adds `docs/plan_report/report.md` as a secondary source of truth. This conflicts directly with the review instruction and master plan discipline.
- `VITE_API_BASE_URL` example could encourage a separate frontend env source.
- `job_pipeline_service.py` may duplicate Phase 3 graph/storage orchestration unless constrained.
- Demo seeding and `/api/jobs/mock-load` could duplicate implementation unless a shared loader is defined.
- API DTOs for dashboard/review job list/detail are not fully specified.
- Batch summary endpoint may promise counters that cannot be reconstructed if skipped duplicates are not persisted.

Missing details:
- Job list/detail response DTOs including score components, observability fields, warnings, and source metadata.
- Exact role profile response DTOs.
- Whether `applications` rows are updated during manual status changes.
- Durable vs immediate-only batch summary behavior.

Conflicts with `Master_Plan.md`:
- Source-of-truth priority conflict.
- Potential single `.env` drift through frontend Vite env usage.

Conflicts with other phase plans:
- Potential overlap with Plan 3 orchestration and demo seeding logic.

Specific fixes required:
- Remove `docs/plan_report/report.md` from source priority.
- Tighten frontend config to avoid requiring or documenting frontend `.env`.
- Define one shared mock/demo loader used by both API and `seed_demo.py`.
- Specify that `job_pipeline_service.py` calls Phase 3 service/graph contracts rather than reimplementing extraction/scoring/storage.
- Add dashboard/review/detail DTOs.

## 4. Cross-Phase Consistency Review

### Phase 1 → Phase 2

Phase 1 provides:
- config system
- DB session
- project structure
- root `.env`
- local SQLite path
- requirements

Status: Good.

Main fix:
- Add explicit `source_platform` allowed values so Phase 2 and Phase 3 do not invent different values.

### Phase 2 → Phase 3

Phase 2 provides:
- extracted job object
- `jd_status`
- `should_score_similarity`
- source metadata
- `raw_content_hash`
- extraction status
- error reason
- token/cost/timing fields
- LangGraph state preservation

Status: Mostly good.

Main fixes:
- Remove optional wording around persisting fallback records.
- Define `source_platform` mapping.
- Ensure `needs_manual_input` always carries enough state for a visible `unclear` pending-review record.

### Phase 3 → Phase 4

Phase 3 provides:
- stored jobs
- score fields
- status fields
- Qdrant sync behavior
- approve/reject/status service functions
- batch counters
- dashboard-ready query behavior

Status: Adequate but needs tightening.

Main fixes:
- Define durable/immediate batch summary limits.
- Define exact storage result DTO.
- Ensure Phase 4 does not duplicate Phase 3 processing.

## 5. Duplicated Work Review

| Duplicate Area | Found In | Problem | Recommended Owner Phase |
|---|---|---|---|
| Pipeline orchestration | Plan 3 graph integration, Plan 4 `job_pipeline_service.py` | Could duplicate extraction → scoring → persistence flow | Phase 3 owns processing graph/service; Phase 4 owns route orchestration |
| Demo loading | Plan 4 `seed_demo.py`, `/api/jobs/mock-load` | Risk of two seed implementations | Phase 4, but one shared loader used by both |
| Raw content hash | Plan 2, Plan 3 | Phase 3 may recompute inconsistently | Phase 2 owns generation; Phase 3 may only fallback-compute if missing |
| Mock input handling | Plan 2, Plan 4 | Could imply Phase 2 owns demo loading | Phase 4 owns mock data loading |
| Batch summary counters | Plan 3, Plan 4 | Counter ownership and persistence unclear | Phase 3 returns counters; Phase 4 exposes them |

## 6. Missing Work Review

| Missing Item | Required By Master Plan Section | Impact | Recommended Phase |
|---|---|---|---|
| `source_platform` allowed values/constraint | Sections 23, 30 | Inconsistent source values across services | Phase 1 |
| Missing-title/company `dedup_key` rule | Section 17 | Could mark unrelated unknown jobs as duplicates | Phase 3 |
| Durable batch summary behavior | Sections 16, 27 | `/api/batches/{batch_id}/summary` may be inaccurate | Phase 3/4 |
| Qdrant payload index verification | Section 26 | Filters may work but drift from master | Phase 3 |
| Dashboard/review/detail response DTOs | Sections 15, 16, 25, 27 | Frontend may miss score/metrics fields | Phase 4 |
| Application table usage policy | Sections 20, 24 | Manual application tracking may ignore `applications` table | Phase 4 |
| Shared demo loader contract | Section 6 | Seed script and mock API may diverge | Phase 4 |

Checked required items:
- SQLite indexes and constraints: Present, with minor `source_platform` gap.
- Partial unique indexes: Present.
- `raw_content_hash`: Present.
- `dedup_key`: Present.
- `duplicate_of_job_id`: Present.
- Qdrant payload indexes: Present but needs “created/verified” wording.
- Qdrant UUID point ID rule: Present.
- Reject deletes vector: Present.
- Approve updates Qdrant payload: Present.
- JD status rules: Present.
- `contact_for_jd`: Present.
- `needs_manual_input`: Present.
- Metrics fields: Present.
- Seed demo data: Present.
- Review queue query: Present.
- Saved dashboard query: Present.
- Frontend failed URL warning: Present.

## 7. Conflict Review

| Conflict | Location | Why It Is a Problem | Fix |
|---|---|---|---|
| Secondary source of truth | `Plan_4.md` Source of Truth | User requires only `Master_Plan.md` | Delete `docs/plan_report/report.md` priority |
| Optional fallback persistence wording | `Plan_2.md` handoff | Master expects visible saved fallback records | Make downstream persistence mandatory unless dedup skips |
| Payload indexes “planned” | `Plan_3.md` acceptance | Master requires creating indexes | Change to created and verified |
| Dedup “when possible” | `Plan_3.md` persistence | Can skip required dedup behavior | Define mandatory dedup when identifiers exist |
| Phase 3 graph vs Phase 4 pipeline | `Plan_3.md`, `Plan_4.md` | Duplicate orchestration risk | Phase 4 calls Phase 3 contract |
| Frontend env example using Vite env | `Plan_4.md` config | Could encourage second env source | Use hardcoded safe default or generated safe config only |
| Mock vectors | `Plan_4.md` seed | Can fake scoring behavior if not isolated | Require Phase 3 scoring by default; mock only explicit demo-offline flag |

## 8. Architecture Drift Review

| Drift Risk | Severity | Why It Matters | Prevention |
|---|---|---|---|
| Adding a secondary source of truth | High | Later agents may follow stale report instead of master | Remove `docs/plan_report/report.md` priority |
| Reimplementing Phase 3 pipeline in Phase 4 | High | Scoring/dedup/Qdrant rules can fork | Phase 4 must call Phase 3 service/graph |
| Underdefined batch summaries | Medium | Metrics UI may show wrong duplicate/Qdrant counts | Define immediate vs persisted summary contract |
| Using frontend env files | Medium | Violates single root `.env` discipline | Do not create or document frontend `.env` |
| Mock vectors leaking outside demo | Medium | Demo stops proving real scoring pipeline | Explicit demo-only flag and tests |
| Overcomplicated Qdrant status transitions | Low | Solo MVP may spend too much time on edge updates | Keep required approve/reject/status sync first |
| Hashing empty dedup keys | High | False duplicates for unclear jobs | Set `dedup_key = None` unless company and title exist |
| Applications table unused/unclear | Low | Manual status tracking may look incomplete | Document whether it is reserved or updated |

## 9. Specific Rewrite Instructions

### Plan_1.md Fixes

```text
1. Add a `source_platform` check/validation note with allowed values: tavily, manual_url, manual_text, mock, job_board.
2. Change the `source_platform` column note to: nullable only before ingestion; persisted job records should set it when known.
3. Add a Phase 4 handoff note: define whether `/api/jobs/{id}/status` updates only `job_posts.status` or also creates/updates `applications`.
4. Add a schema verification check for `source_platform` if a constraint is implemented.
```

### Plan_2.md Fixes

```text
1. Replace “if the pipeline chooses to save fallback records” with “Phase 3/4 must persist controlled unclear fallback records unless deduplication skips them.”
2. Add explicit mapping: manual_url -> manual_url, manual_text -> manual_text, tavily -> tavily, mock -> mock.
3. Add a note that Phase 2 never reads mock_data files and never implements demo seeding.
4. Require `needs_manual_input` terminal states to include the exact frontend warning text or a stable warning code.
5. Clarify that Phase 3 consumes `raw_content_hash`; Phase 3 may recompute only if missing and reliable `clean_text` exists.
```

### Plan_3.md Fixes

```text
1. Replace “Run deduplication before scoring when possible” with “Run deduplication before scoring whenever raw_content_hash or a valid dedup_key exists.”
2. Add `dedup_key = None` when normalized company or title is missing, empty, or unknown.
3. Define a `StoredJobResult` contract with job_id, batch_id, status, dedup_action, duplicate_of_job_id, counters, qdrant_sync_status, warning, and error_reason.
4. Replace “Qdrant payload indexes are planned” with “Qdrant payload indexes are created and verified.”
5. Add tests for missing company/title dedup behavior.
6. Add a handoff note that Phase 4 calls Phase 3 processing contracts and must not rewire scoring/dedup/Qdrant logic.
7. Clarify whether skipped exact duplicate counts are immediate-response counters only or persisted in an allowed way without adding a `search_runs` table.
```

### Plan_4.md Fixes

```text
1. Delete `docs/plan_report/report.md` from the Source of Truth priority list.
2. Replace the priority list with: `Master_Plan.md` is the only source of truth.
3. Replace the frontend config example so it does not require a frontend `.env`; keep a safe hardcoded default or generated non-secret config.
4. Add `JobListItemResponse`, `JobDetailResponse`, `ScoreBreakdownResponse`, and `RoleProfileResponse` DTOs.
5. State that `job_pipeline_service.py` calls Phase 2/3 public service or graph contracts and does not duplicate their internals.
6. Define one shared demo loader used by both `seed_demo.py` and `/api/jobs/mock-load`.
7. Require demo seeding to use Phase 3 scoring/storage by default; allow deterministic mock vectors only behind an explicit demo-offline flag.
8. Clarify `/api/batches/{batch_id}/summary` behavior for counters that are not persisted, especially skipped exact duplicates.
9. Define whether manual status updates create/update `applications` rows or intentionally leave `applications` reserved.
```

## 10. Recommended Final Phase Boundary

| Phase | Owns | Must Not Own |
| ----- | ---- | ------------ |
| Phase 1 | Directory skeleton, backend env, root `.env`, Qdrant Docker Compose, SQLite async setup, core tables, indexes, constraints, config foundation | Extraction, LangGraph behavior, scoring, dedup behavior, Qdrant vectors, APIs, React UI |
| Phase 2 | URL/manual text extraction, Pydantic structured extraction, retry, `JobAgentState`, extraction graph, `mark_unclear`, observability state | Scoring, dedup, final persistence, Qdrant upsert/search/delete, FastAPI routes, React UI, demo loading |
| Phase 3 | Skill normalization, embedding text, scoring, dedup policy, SQLite persistence, Qdrant collection/payload/upsert/delete/status sync, processing service/graph contracts | FastAPI routes, React UI, seed script, Tavily endpoint, authentication, reranking, GraphRAG |
| Phase 4 | Seed demo, mock data, FastAPI routes, Tavily integration, API orchestration, React UI, dashboard, review queue, role profile UI, demo readiness | Changing extraction/scoring/dedup/Qdrant architecture, adding second env, auth, auto-apply, reranking, GraphRAG |

## 11. Final Verdict

Needs revision before implementation.

The plans are close and do not need a major rewrite. However, implementation should not start until the source-of-truth conflict in `Plan_4.md`, the Phase 3/4 orchestration boundary, the dedup edge cases, and the batch summary contract are corrected. Those are small edits, but they prevent real architecture drift.

## 12. Final Score Summary

| Plan      | Score / 100 | Verdict |
| --------- | ----------: | ------- |
| Plan_1.md | 89 | Approved with minor edits |
| Plan_2.md | 85 | Approved with minor edits |
| Plan_3.md | 78 | Needs targeted revision |
| Plan_4.md | 78 | Needs targeted revision |
| Overall   | 83 | Needs revision before implementation |