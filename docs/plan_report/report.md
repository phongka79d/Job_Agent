# Review Report: Plan_1 to Plan_4 vs Master_Plan

## 1. Executive Summary

The four phase plans are close to implementation-ready, but they need revision before execution. They are well aligned with the MVP stack and largely respect the intended phase boundaries. The biggest issue is not missing architecture; it is preventing later phases from mutating earlier decisions.

- Overall readiness score: 87 / 100
- Biggest strengths:
  - Strong alignment with SQLite, Qdrant Local, FastAPI, React/Vite, LangGraph, and Pydantic structured output.
  - Phase boundaries are mostly explicit and practical.
  - Deduplication, scoring, Qdrant sync, and UI visibility are specified in implementation-level detail.
  - Verification checklists are unusually strong for a solo-developer MVP.
- Biggest risks:
  - Plan_3 still contains a schema-edit escape hatch that conflicts with Plan_1 ownership.
  - Plan_4 has an internal contradiction on `applications` writes.
  - Plan_4 demo seed counts conflict with the Master Plan example output.
  - Demo reset scoping references an `is_demo` flag that does not exist in the schema.
  - Warning propagation from Phase 2 to Phase 4 is present conceptually but not fully wired as a handoff contract.
- Recommendation: revise the plans first, then start implementation. The revisions are targeted; no major rewrite is required.

## 2. Source of Truth Check

`Master_Plan.md` defines a local, demo-friendly MVP:

- React + TypeScript + Vite frontend.
- FastAPI backend.
- LangChain/LangGraph agent flow.
- Pydantic structured extraction.
- SQLite local database through `sqlite+aiosqlite`.
- Qdrant Local through Docker Compose.
- `httpx` + `trafilatura` for URL extraction.
- Tavily or similar public search API.
- Single root `.env`.
- No GraphRAG, Neo4j, Jina Reranker, auto-apply, authenticated social crawler, PostgreSQL, Celery/Redis, multi-user auth, or extra env files.

| Required Decision | Plan Status | Notes |
|---|---|---|
| SQLite, not PostgreSQL | Pass | All plans explicitly reject PostgreSQL. |
| Qdrant Local, not Qdrant Cloud | Pass | Docker Compose local Qdrant is preserved. |
| FastAPI backend | Pass | Phase 4 owns routes and app integration. |
| React + TypeScript + Vite frontend | Pass | Phase 4 owns Vite app. |
| LangChain/LangGraph for agent flow | Pass | Phase 2 and 3 use LangGraph boundaries. |
| Pydantic structured output | Pass | Phase 2 specifies structured output/parser plus validation. |
| `httpx` + `trafilatura` URL extraction | Pass | Phase 2 owns it and bans custom parser/browser rendering. |
| No GraphRAG | Pass | Repeatedly excluded. |
| No Neo4j | Pass | Repeatedly excluded. |
| No Jina Reranker in MVP | Pass | Repeatedly excluded. |
| No auto-apply | Pass | Repeatedly excluded. |
| No LinkedIn/Facebook authenticated crawler | Pass | Repeatedly excluded. |
| No authentication/multi-user system | Pass | Repeatedly excluded. |
| Single root `.env` | Pass with minor risk | Phase 4 must avoid Vite `.env` drift. |

## 3. Individual Plan Scores

### 3.1 Plan_1.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Correct stack, schema, env, Docker, and SQLite rules. |
| Correct phase scope | 10 | Strongly limited to foundation. |
| Completeness | 9 | Covers tables, indexes, constraints, PRAGMAs, config, and verification. |
| Technical specificity | 10 | Very implementation-ready. |
| Dependency handoff quality | 9 | Good handoff to Phase 2 and Phase 3. |
| Consistency with other plans | 9 | Mostly consistent; application-row handoff needs alignment with Plan_4. |
| Implementation readiness | 9 | Clear scripts and checks. |
| MVP simplicity | 8 | Full dependency install in Phase 1 is convenient but slightly heavy. |
| Risk control and error handling | 9 | Strong database drift and PostgreSQL checks. |
| Testability | 10 | Schema verification is concrete. |

Overall score: 92 / 100

Strengths:

- Correctly owns the schema and avoids PostgreSQL.
- Includes `raw_content_hash`, `dedup_key`, `duplicate_of_job_id`, score columns, token/cost fields, and all required indexes.
- Correctly uses root `.env`, `sqlite+aiosqlite`, UUID strings, and Qdrant-only Docker Compose.
- Strong verification script requirements.

Problems:

- The handoff note says Phase 4 must define whether status updates also write `applications` rows, but Plan_4 later both defers and requires those writes.
- Installing all future dependencies in Phase 1 is acceptable, but implementation agents may still over-infer scope despite the warning.

Missing details:

- Add a final note that Phase 1 creates `.env.example` only; local `.env` may be copied manually and must not be committed.
- Tighten the `applications` handoff after Plan_4 is corrected.

Conflicts with `Master_Plan.md`:

- None blocking.

Conflicts with other phase plans:

- Plan_3 step 9 allows adding missing Master Plan fields in Phase 3, while Plan_1 says schema changes must trigger Phase 1 revision or an explicit migration.
- Plan_4 has contradictory `applications` behavior, which makes Plan_1's handoff unresolved.

Specific fixes required:

- Clarify that schema changes after Phase 1 require an explicit migration/revision task.
- Replace the open-ended `applications` handoff with the final policy chosen in Plan_4.

### 3.2 Plan_2.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Correct extraction stack, retry, schema, and fallback behavior. |
| Correct phase scope | 9 | Avoids scoring, dedup, Qdrant, routes, and UI. |
| Completeness | 9 | Covers URL/manual text, schema, prompts, graph, fallback, and tests. |
| Technical specificity | 9 | Strong enough for direct implementation. |
| Dependency handoff quality | 8 | Needs explicit `user_warning` propagation to Phase 3/4. |
| Consistency with other plans | 9 | Mostly clean. |
| Implementation readiness | 9 | Tests are concrete and mock LLM/network correctly. |
| MVP simplicity | 8 | Good, though graph internals are fairly detailed for Phase 2. |
| Risk control and error handling | 9 | Strong fallback and no-crash behavior. |
| Testability | 10 | Excellent test matrix. |

Overall score: 89 / 100

Strengths:

- Correctly uses `httpx` + `trafilatura`.
- Correctly rejects browser rendering, BeautifulSoup, scoring, dedup, Qdrant, APIs, and UI.
- Preserves `batch_id`, `role_profile_id`, `input_source`, metadata, status fields, token/cost fields, and fallback state.
- Correctly generates `raw_content_hash` from normalized clean text.

Problems:

- `user_warning` is added to `JobAgentState`, but the Phase 3 handoff list omits it.
- Acceptance criteria say "Phase 3/4 must persist" fallback records, while later text correctly says Phase 3 owns persistence and Phase 4 only invokes it.
- `extracted_job` handoff should specify whether Phase 3 receives a `JobPostExtract` instance or `model_dump()` dict.

Missing details:

- Explicit contract mapping `user_warning` -> Phase 3 `StoredJobResult.warning` -> Phase 4 API `warning`.
- Serialization rule for `JobPostExtract`.

Conflicts with `Master_Plan.md`:

- None blocking.

Conflicts with other phase plans:

- Minor ownership wording conflict with Plan_3/Plan_4 around who persists fallback records.

Specific fixes required:

- Add `user_warning` to Phase 3 handoff.
- Replace "Phase 3/4 must persist" with "Phase 3 persists; Phase 4 invokes Phase 3 through the pipeline."
- Define `extracted_job = JobPostExtract.model_dump()` at the graph boundary unless Phase 3 explicitly accepts the Pydantic object.

### 3.3 Plan_3.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 9 | Correct scoring, dedup, Qdrant, status sync, and SQLite source of truth. |
| Correct phase scope | 8 | Mostly correct, but schema-edit language and manual correction capability need tightening. |
| Completeness | 9 | Very complete for scoring/storage/sync. |
| Technical specificity | 9 | Detailed enough for implementation. |
| Dependency handoff quality | 9 | Strong Phase 2 and Phase 4 contracts. |
| Consistency with other plans | 8 | Conflicts with Plan_1 schema ownership. |
| Implementation readiness | 8 | Good, but must remove schema mutation ambiguity. |
| MVP simplicity | 7 | Some service-capable edit/vector recomputation behavior risks overengineering. |
| Risk control and error handling | 9 | Good Qdrant failure and dedup handling. |
| Testability | 9 | Strong unit/fake-client test plan. |

Overall score: 85 / 100

Strengths:

- Correctly owns skill normalization, dynamic role query text, clean embedding text, scoring, dedup, persistence, and Qdrant sync.
- Correctly rejects Qdrant/vector deduplication.
- Correctly specifies Qdrant UUID point IDs, payload indexes, filters, approve payload update, and reject vector delete.
- Good transaction behavior: do not upsert Qdrant if SQLite save fails; keep SQLite source of truth if Qdrant fails.

Problems:

- Implementation step 9 says "add only missing Master Plan fields", which contradicts Plan_1's schema ownership and should not happen silently in Phase 3.
- Manual correction/vector recomputation support is larger than needed for the MVP and may encourage edit APIs/UI.
- `user_warning` from Phase 2 is not explicitly consumed in storage result/API handoff.
- The semantic similarity section allows local cosine or Qdrant-equivalent scoring; this is acceptable, but the production contract should be stated as one primary path.

Missing details:

- Explicit IntegrityError handling for the partial unique `raw_content_hash` index during concurrent or repeated inserts.
- Explicit mapping of Phase 2 `user_warning` to storage/API warning.

Conflicts with `Master_Plan.md`:

- None blocking if schema edits are removed.

Conflicts with other phase plans:

- Conflicts with Plan_1 by allowing Phase 3 to add missing schema fields.

Specific fixes required:

- Remove schema-edit permission from Phase 3.
- Add warning propagation from Phase 2 state to `StoredJobResult.warning`.
- Mark manual content correction/vector recomputation as non-MVP optional internal support, or delete it.
- Choose one production embedding similarity contract and keep Qdrant usage clearly separate from deduplication.

### 3.4 Plan_4.md Review

| Criterion | Score / 10 | Notes |
|---|---:|---|
| Alignment with `Master_Plan.md` | 8 | Mostly aligned, but demo seed counts conflict with Master example output. |
| Correct phase scope | 8 | Correct owner of API/UI/demo, but scope is large. |
| Completeness | 9 | Covers endpoints, DTOs, UI, seed, demo, metrics, tests. |
| Technical specificity | 9 | Very detailed. |
| Dependency handoff quality | 8 | Good reuse language; warning and batch metrics need tightening. |
| Consistency with other plans | 7 | Internal application-policy contradiction and demo reset issue. |
| Implementation readiness | 8 | Ready after targeted fixes. |
| MVP simplicity | 7 | UI/test/demo scope is large for solo implementation. |
| Risk control and error handling | 8 | Good warnings and partial success handling; reset scoping risk remains. |
| Testability | 9 | Strong backend/frontend/e2e test list. |

Overall score: 81 / 100

Strengths:

- Correctly owns seed demo, mock data, FastAPI endpoints, Tavily integration, React UI, score breakdown, metrics, manual inputs, and demo readiness.
- Strong rule that Phase 4 calls Phase 2/3 services instead of reimplementing them.
- Good DTO coverage and UI visibility for duplicate and Qdrant sync warnings.
- Correctly keeps demo jobs as `pending_review`.

Problems:

- `applications` policy is contradictory: first says writes may be deferred, then says they MUST be implemented.
- Demo seed summary says 10 scorable jobs and 10 Qdrant vectors, while `Master_Plan.md` example output says 8 scorable jobs, 2 need-review/social jobs, 2 unrelated jobs, and 8 vectors.
- Reset scoping says use `source_platform='mock'` or `is_demo`; `is_demo` is not in the Phase 1 schema.
- Role profile reset scoping is underspecified because `role_profiles` has no `source_platform` or `is_demo`.
- Metrics UI depends on `batch_id`, but the plan does not clearly define active/latest batch selection after reload or across multiple batches.

Missing details:

- Exact safe demo reset strategy for role profiles without adding schema.
- Exact warning propagation source from Phase 2/3 to API response.
- Whether `/api/jobs/search` is synchronous request-scoped processing or a true background job. Avoid wording that invites Celery/Redis.

Conflicts with `Master_Plan.md`:

- Demo seed expected output conflicts with the Master Plan example unless the Master Plan is revised.

Conflicts with other phase plans:

- Application-row policy conflicts internally and with Plan_1's unresolved handoff.
- `is_demo` reset option conflicts with Phase 1 schema.

Specific fixes required:

- Resolve application writes as one rule.
- Align demo seed counts with Master Plan or revise Master Plan first.
- Remove `is_demo` unless Phase 1 schema is revised.
- Add active/latest batch behavior for the MetricsPanel.

## 4. Cross-Phase Consistency Review

### Phase 1 -> Phase 2

Phase 1 provides what Phase 2 needs:

- config system: yes
- database session: yes
- project structure: yes
- dependency setup: yes, including extraction/LangGraph dependencies
- `.env`: yes, single root `.env`
- local database path: yes, `backend/data/job_matching.db`

Gap: none blocking. Plan_2 may add test dependencies; that is acceptable.

### Phase 2 -> Phase 3

Phase 2 provides most Phase 3 inputs:

- extracted job object: yes, but serialization should be clarified
- `jd_status`: yes
- `should_score_similarity`: yes
- source metadata: yes
- `raw_content_hash`: yes
- extraction status: yes
- error reason: yes
- token/cost fields: yes
- LangGraph state preservation: yes

Gaps:

- Add `user_warning` to the formal handoff.
- Clarify that `extracted_job` is a Pydantic object or a `model_dump()` dict.
- Correct ownership wording so Phase 3 persists fallback records and Phase 4 only invokes that service.

### Phase 3 -> Phase 4

Phase 3 provides most Phase 4 needs:

- stored jobs: yes
- score fields: yes
- status fields: yes
- Qdrant sync behavior: yes
- approve/reject behavior: yes
- batch/job summary data: mostly yes
- dashboard-ready query behavior: yes through Master and Plan_4

Gaps:

- `StoredJobResult.warning` should explicitly carry Phase 2 `user_warning`.
- Batch summary durability is mostly handled, but Plan_4 must define how the frontend selects the relevant batch.
- Application-row policy must be resolved before routes are implemented.

## 5. Duplicated Work Review

| Duplicate Area | Found In | Problem | Recommended Owner Phase |
|---|---|---|---|
| Database schema changes | Plan_1, Plan_3 | Plan_3 says it can add missing Master Plan fields, conflicting with Plan_1 schema ownership. | Phase 1 only, or explicit migration task. |
| `raw_content_hash` generation | Plan_2, Plan_3 | Phase 3 may recompute only when reliable text exists; avoid duplicate hash policy. | Phase 2 generates; Phase 3 consumes or narrowly repairs missing reliable hashes. |
| Warning text for failed URL extraction | Plan_2, Plan_4 | Both contain the same warning; without a handoff, Phase 4 may hardcode a divergent copy. | Phase 2 owns stable warning; Phase 4 displays it. |
| Batch summary counters | Plan_3, Plan_4 | Shared responsibility is fine, but DTO/source of truth must stay consistent. | Phase 3 prepares immediate counters; Phase 4 exposes/reconstructs. |
| Applications status policy | Plan_1, Plan_4 | Plan_1 defers the policy; Plan_4 contradicts itself. | Phase 4 route/service integration. |
| Qdrant sync functions vs routes | Plan_3, Plan_4 | Not a bad duplicate if boundaries hold; route handlers must not reimplement sync. | Phase 3 service functions; Phase 4 routes call them. |
| Manual input flow | Plan_2, Plan_4 | Acceptable split, but keep service/UI boundary clear. | Phase 2 extraction service; Phase 4 API/UI. |

## 6. Missing Work Review

Most mandatory Master Plan items are present: SQLite indexes and constraints, partial unique index, `raw_content_hash`, `dedup_key`, `duplicate_of_job_id`, Qdrant payload indexes, UUID point ID rule, reject-vector-delete, approve-payload-update, JD status rules, `contact_for_jd`, `needs_manual_input`, metrics fields, seed data, review query, saved dashboard query, and frontend failed-URL warning.

The remaining items are missing or underspecified:

| Missing Item | Required By Master Plan Section | Impact | Recommended Phase |
|---|---|---|---|
| Formal `user_warning` propagation from Phase 2 state through Phase 3 storage result to Phase 4 API response | Sections 8, 15, 27 | Frontend may lose or reinvent the required failed-URL warning. | Phase 2/3/4 handoff |
| Safe demo role profile reset strategy without adding `is_demo` | Sections 6, 35 | Reset may either leave duplicate demo profiles or delete non-demo data. | Phase 4 |
| Active/latest `batch_id` selection for metrics UI | Sections 16, 27 | MetricsPanel may not know which batch summary to request after reload. | Phase 4 |
| Single resolved application-row write policy | Sections 24, 37 | Manual status tracking may be inconsistent across API and UI. | Phase 4 |
| Reconciliation of demo scorable/vector counts | Section 6 | Seed script output may not match Master Plan demo expectations. | Phase 4, or Master Plan revision |
| Exact batch summary SQL aggregation rules | Sections 16, 25, 27 | Metrics can drift between immediate response and reconstructed API summary. | Phase 4 |

## 7. Conflict Review

| Conflict | Location | Why It Is a Problem | Fix |
|---|---|---|---|
| Phase 3 may add schema fields | Plan_3 Implementation Step 9 vs Plan_1 Handoff/Acceptance | Allows schema drift after Phase 1. | Replace with fail-fast verification and explicit Phase 1 revision/migration. |
| Application writes may be deferred and also MUST be implemented | Plan_4 Error Handling/Application policy | Internal contradiction blocks implementation agents. | Delete one rule; recommended: keep MUST write application rows for applied/interview/rejected/offer. |
| Demo seed says 10 scorable jobs, Master example says 8 | Plan_4 Seed Demo vs Master Section 6 | Seed output and Qdrant vector count will not match source of truth. | Align Plan_4 with Master, or revise Master first. |
| Reset can use `is_demo` but schema lacks it | Plan_4 Seed Demo | Encourages unplanned schema change or unsafe reset. | Remove `is_demo`; reset by `source_platform='mock'` jobs and safe demo profile matching. |
| Phase 2 says Phase 3/4 must persist fallback records | Plan_2 Acceptance vs Plan_3/4 ownership | Blurs persistence ownership. | Say Phase 3 persists; Phase 4 invokes the Phase 3 pipeline. |
| Role profile reset by `source_platform` is impossible | Plan_4 Seed Demo | `role_profiles` has no `source_platform`. | Define deterministic demo profile deletion only when no non-mock jobs reference it, or do not delete profile. |
| "Start background public web search" wording vs no Celery/Redis | Master endpoint wording and Plan_4 search | Could trigger queue infrastructure drift. | Clarify request-scoped async processing for MVP; no persistent queue. |
| Manual correction/vector recomputation support vs no edit UI/routes | Plan_3 Qdrant Vector Update Rules | Service capability can leak into extra UI/API work. | Mark as non-MVP internal only or remove. |

## 8. Architecture Drift Review

| Drift Risk | Severity | Why It Matters | Prevention |
|---|---|---|---|
| Schema mutation after Phase 1 | High | Breaks phase ownership and can create hidden migration debt. | Phase 3 verifies only; schema fixes require explicit revision/migration. |
| Demo reset using absent `is_demo` | High | Can cause schema drift or accidental data deletion. | Remove `is_demo`; use existing fields and safe deletion rules. |
| Application policy contradiction | Medium | Status tracking may be partly implemented. | Keep one explicit rule and tests. |
| Deterministic mock vectors leaking into normal flows | Medium | Demo-only shortcuts could corrupt scoring behavior. | Keep explicit demo-only flag and tests that normal flows cannot use it. |
| Background search wording leading to Celery/Redis | Medium | Adds out-of-scope infrastructure. | State in-process/request-scoped MVP behavior. |
| Manual correction/vector recomputation growing into edit UI | Medium | Adds scope not required for portfolio MVP. | Remove or mark optional internal support only. |
| Batch metrics leading to `search_runs` table | Medium | Master explicitly avoids new batch summary tables. | Reconstruct from `job_posts`; skipped duplicates are immediate-only/null later. |
| Frontend `.env` drift | Medium | Violates single root `.env` and risks secret exposure. | Keep `src/config.ts`; add tests/grep for frontend `.env*`. |
| Qdrant/vector dedup returning | Low | Plans strongly reject it, but it is a tempting shortcut. | Keep tests proving dedup uses only hash and key. |
| Overbuilt React UI | Low | Solo MVP may slow down. | Keep UI operational and compact; avoid nonessential polish. |

## 9. Specific Rewrite Instructions

### Plan_1.md Fixes

```text
1. Replace the final handoff bullet "Phase 4 must define whether manual application status updates only update job_posts.status or also create/update rows in applications" with the final policy selected in Plan_4.
2. Add: "If Plan_4 keeps application-row writes, Phase 4 must update job_posts.status as source of truth and create/update applications rows for applied, interview, rejected, and offer transitions."
3. Add: "Phase 1 creates .env.example only. A local root .env may be copied manually and must remain gitignored."
4. Keep the existing rule that Plan_3 may verify models.py/session.py but must not alter schema without an explicit migration/revision task.
```

### Plan_2.md Fixes

```text
1. Add user_warning to the Phase 3 handoff field list.
2. Add a handoff rule: Phase 3 must map JobAgentState.user_warning to StoredJobResult.warning when present.
3. Replace "Phase 3/4 must persist controlled unclear fallback records" with "Phase 3 persists controlled unclear fallback records; Phase 4 invokes Phase 3 through the pipeline."
4. Add a serialization rule: terminal success states hand off extracted_job as JobPostExtract.model_dump() unless Phase 3 explicitly accepts a JobPostExtract object.
5. Add a test assertion that needs_manual_input terminal states include the exact stable user_warning text.
```

### Plan_3.md Fixes

```text
1. Replace Implementation Step 9 with: "Verify models.py already contains required Master Plan fields and indexes. If anything is missing, fail Phase 3 verification and create an explicit Phase 1 revision or migration task. Do not alter schema in Phase 3."
2. Add user_warning to consumed Phase 2 state fields and StoredJobResult.warning mapping.
3. Add IntegrityError handling for raw_content_hash unique-index collisions: rollback, fetch existing job, return skipped_exact_duplicate, and do not upsert Qdrant.
4. Clarify the production embedding_similarity path: use local cosine over role/job embeddings for pair scoring, while Qdrant stores/searches vectors; or explicitly use Qdrant score. Do not leave both as equally primary.
5. Delete or mark manual job-content correction and scorable/non-scorable transitions as optional internal non-MVP service support with no Phase 3/4 routes or UI.
6. Add a storage test that parse_status=needs_manual_input carries warning/error fields into the stored/API handoff contract.
```

### Plan_4.md Fixes

```text
1. Delete the lines saying application-row writes may be deferred if the later MUST rule remains.
2. Keep one policy: /api/jobs/{id}/status updates job_posts.status and MUST create/update applications rows for applied, interview, rejected, and offer.
3. Replace the seed expected output with the Master Plan output: Inserted jobs 12, Scorable jobs 8, Need-review/social jobs 2, Unrelated jobs 2, Local Qdrant vectors upserted 8. If unrelated jobs should be scorable low-score examples, revise Master_Plan.md first.
4. Delete "or is_demo flag" from demo reset scoping unless Phase 1 schema is revised.
5. Add safe reset behavior: delete job_posts where source_platform='mock'; delete Qdrant points filtered by source_platform='mock'; delete the demo role profile only if it matches the deterministic demo profile and has no remaining non-mock jobs.
6. Add active batch behavior: after parse/search/mock-load, store the returned batch_id in frontend state/localStorage; MetricsPanel uses that batch_id, with a backend latest-batch-for-role fallback if implemented.
7. Add a rule that API warnings must come from Phase 2/3 user_warning/warning fields when present.
8. Clarify /api/jobs/search is request-scoped async MVP processing, not a persistent background queue.
9. Add verification that no frontend .env, frontend/.env.example, or frontend/job-agent-ui/.env.example exists.
```

## 10. Recommended Final Phase Boundary

| Phase | Owns | Must Not Own |
| ----- | ---- | ------------ |
| Phase 1 | Project structure, backend config, root `.env.example`, Qdrant Docker Compose, SQLite async setup, core tables, indexes, constraints, schema verification | Extraction, LangGraph behavior, scoring, dedup behavior, Qdrant vectors, APIs, React UI, seed data |
| Phase 2 | URL/manual text preparation, `httpx` + `trafilatura`, `JobPostExtract`, structured output, retry/repair, `JobAgentState`, extraction graph, `mark_unclear`, observability, warning state | SQLite final persistence, scoring, dedup, Qdrant sync, FastAPI routes, React UI, seed/demo loading |
| Phase 3 | Skill normalization, role/job embedding text, embeddings, scoring formula, JD multiplier, dedup policy, SQLite persistence services, Qdrant collection/payload/upsert/delete/update, status sync services, batch counters | React UI, final dashboard endpoints, route handlers, authentication, auto-apply, cover letters, GraphRAG, Neo4j, Jina, Celery/Redis, schema redesign |
| Phase 4 | `seed_demo.py`, mock data, shared demo loader, Tavily integration, FastAPI routes, pipeline orchestration, React/Vite UI, dashboard, review queue, role profiles, demo mode, metrics, manual URL/text flows, e2e demo | Changing extraction architecture, changing scoring/dedup/Qdrant policy, changing schema without approved migration, adding auth, adding extra env files, adding future-phase AI features |

## 11. Final Verdict

Needs revision before implementation.

The plans are strong and practical, but implementation should not start until the schema ownership conflict, Plan_4 application-policy contradiction, demo seed count mismatch, demo reset scoping, and warning handoff are fixed. These are targeted edits, not a major rewrite.

## 12. Final Score Summary

| Plan      | Score / 100 | Verdict |
| --------- | ----------: | ------- |
| Plan_1.md | 92 | Approved with minor edits |
| Plan_2.md | 89 | Approved with minor edits |
| Plan_3.md | 85 | Needs revision |
| Plan_4.md | 81 | Needs revision |
| Overall   | 87 | Needs revision before implementation |
