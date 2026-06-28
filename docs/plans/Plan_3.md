# Plan 3 - Scoring, Deduplication, Persistence, and Qdrant Sync

## 1. Objective

Complete the backend job-processing pipeline after extraction: normalize skills, build embedding text, calculate deterministic score components, apply JD confidence, enforce duplicate rules, persist jobs as `pending_review`, and synchronize scorable jobs with local Qdrant.

This phase connects the Plan 2 extraction result to the Plan 1 SQLite schema and local Qdrant storage without adding public API routes or frontend screens.

## 2. Source of Truth

- `Master_Plan.md` section 4, "Architecture"
- `Master_Plan.md` section 8, "JD Status Rules"
- `Master_Plan.md` section 9, "Scoring Formula"
- `Master_Plan.md` section 10, "JD Confidence Multiplier"
- `Master_Plan.md` section 11, "Simplified Location and Level Scoring"
- `Master_Plan.md` section 12, "Skill Overlap Normalization"
- `Master_Plan.md` section 13, "Skill Alias Normalization"
- `Master_Plan.md` section 16, "Simplified Deduplication Strategy"
- `Master_Plan.md` section 17, "Smart Embedding Strategy"
- `Master_Plan.md` section 20, "SQLite Database Design"
- `Master_Plan.md` section 22, "Table: job_posts"
- `Master_Plan.md` section 24, "SQLite Indexes"
- `Master_Plan.md` section 25, "Qdrant Local Collection Schema"
- `Master_Plan.md` section 35, "Implementation Checklist: Scoring, Database, Qdrant Local"

## 3. Prerequisites from Prior Phases

- [ ] Plan 1 database models, async session, and environment settings exist.
- [ ] Plan 1 shared constants in `backend/app/core/constants.py` exist and expose the Master-approved status/source values.
- [ ] Plan 1 Qdrant Docker Compose file exists.
- [ ] Plan 2 extraction graph returns `JobAgentState`.
- [ ] Plan 2 `JobPostExtract` schema is stable.
- [ ] `batch_id`, `role_profile_id`, and `input_source` are preserved by extraction.

## 4. Scope

- Implement deterministic scoring utilities in `scoring_service.py`.
- Import Plan 1 shared constants for executable status/source/JD validation and transition policies.
- Implement skill alias normalization.
- Implement `build_embedding_text(job)` from clean extracted fields only.
- Implement `build_role_query_text(role_profile)` dynamically without storing it.
- Implement `embedding_service.py` using `OPENAI_EMBEDDING_MODEL` from settings.
- Generate embeddings for both `build_role_query_text(role_profile)` and `build_embedding_text(job)`.
- Validate embedding vector length against `EMBEDDING_DIMENSION`.
- Calculate `embedding_similarity` from the local Qdrant cosine query score, normalized to `[0, 1]`.
- Implement location and level scoring using three-tier rules.
- Implement skill overlap normalized to `[0, 1]`.
- Implement base score and final score formulas.
- Implement JD confidence multiplier for `full_jd` and `partial_jd`.
- Ensure embedding/scoring failures do not crash the whole batch; the job must already be persisted with null score fields before any embedding or Qdrant operation is attempted.
- Implement deduplication by `raw_content_hash` first and `dedup_key` second.
- Implement duplicate status policy so saved, applied, interview, rejected, and offer jobs do not re-enter `pending_review`.
- Implement job persistence using the Plan 1 `job_posts` schema.
- Add one orchestration helper that converts a Plan 2 `JobAgentState` into a persisted `job_posts` row and optional Qdrant point.
- Implement Qdrant collection creation with cosine distance and embedding dimension from `.env`.
- Implement Qdrant payload indexes.
- Expose an idempotent `ensure_collection()` / startup initialization method in `qdrant_service.py` so Plan 4 can initialize Qdrant during FastAPI startup without owning collection logic.
- Upsert only scorable jobs into Qdrant.
- Use `job_posts.id` canonical UUID strings as Qdrant point IDs.
- Implement Qdrant payload updates for status changes.
- Delete Qdrant vectors only when review jobs move to `ignored`.
- Add tests for scoring, deduplication, persistence, Qdrant payload behavior, and status sync.

## 5. Out of Scope

- Do not implement FastAPI route handlers.
- Do not implement Tavily search.
- Do not implement `seed_demo.py` or mock JSON data.
- Do not implement React UI.
- Do not change database schema from Plan 1. Verify models.py already contains required Master Plan fields and indexes. If anything is missing, fail Phase 3 verification and create an explicit Phase 1 revision or migration task. Do not alter schema in Phase 3.
- Do not add vector similarity deduplication.
- Do not score `contact_for_jd`, `no_jd`, or `unclear` jobs.
- Do not store raw HTML or messy full JD text as `embedding_text`.
- Do not use Qdrant as the source of truth for job status; SQLite remains the source of truth.

## 6. Target Directory Structure

```text
backend/
`-- app/
    |-- services/
    |   |-- __init__.py
    |   |-- dedup_service.py
    |   |-- embedding_service.py
    |   |-- extraction_service.py
    |   |-- job_processing_service.py
    |   |-- qdrant_service.py
    |   `-- scoring_service.py
    |-- db/
    |   |-- models.py
    |   `-- session.py
    `-- tests/
        |-- test_dedup_service.py
        |-- test_embedding_service.py
        |-- test_job_processing_service.py
        |-- test_job_persistence.py
        |-- test_qdrant_service.py
        `-- test_scoring_service.py
```

Recommended ownership:

```text
embedding_service.py       -> embedding API calls and vector validation
scoring_service.py         -> deterministic score math only
dedup_service.py           -> duplicate decisions only
qdrant_service.py          -> Qdrant collection, indexes, upsert/delete/filter/similarity query/status payload
job_processing_service.py  -> end-to-end Plan 2 state -> SQLite + Qdrant pipeline
```

If a repository/helper module is needed for database access, add it under `backend/app/db/` or `backend/app/services/` and keep it private to the backend implementation. Do not add new tables.

## 7. Technical Specifications

### Scorable JD Rules

Only these statuses are scorable:

```text
full_jd
partial_jd
```

These statuses must not be embedded or scored:

```text
contact_for_jd
no_jd
unclear
```

For non-scorable jobs:

```text
should_score_similarity = false
embedding_text = null
embedding_similarity = null
skill_overlap_score = null
location_match_score = null
level_match_score = null
base_score = null
jd_confidence_multiplier = null
final_score = null
final_score_percent = null
```

### Scoring Formula

All components must be normalized to `[0, 1]`.

```text
base_score =
  0.55 * embedding_similarity
+ 0.25 * skill_overlap_score
+ 0.10 * location_match_score
+ 0.10 * level_match_score
```

Then:

```text
final_score = base_score * jd_confidence_multiplier
final_score_percent = final_score * 100
```

Clamp all user-visible scores to `[0, 1]` before converting to percent.

### JD Confidence Multiplier

```text
full_jd = 1.00
partial_jd = 0.85
contact_for_jd = null
no_jd = null
unclear = null
```

### Location Match

```text
exact match = 1.0
remote acceptable or partial match = 0.5
mismatch = 0.0
```

### Level Match

```text
exact level match = 1.0
adjacent level match = 0.5
mismatch = 0.0
```

Required adjacent level behavior:

- `intern` and `fresher` are adjacent.
- `fresher` and `junior` are adjacent.
- `junior` and `mid` are adjacent.
- `mid` and `senior` are adjacent.
- `unknown` should not produce a stronger score than `0.0` unless an explicit local rule is added and tested.

### Skill Normalization

Use this alias table:

```python
SKILL_ALIASES = {
    "sqlite": "sqlite",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "large language model": "llm",
    "large language models": "llm",
    "vector database": "vector db",
    "javascript": "js",
    "typescript": "typescript",
}
```

Normalization:

```python
def normalize_skill(skill: str) -> str:
    value = skill.strip().lower()
    return SKILL_ALIASES.get(value, value)
```

Skill overlap:

```python
def calculate_skill_overlap_score(user_skills: set[str], job_required_skills: set[str]) -> float:
    if not job_required_skills:
        return 0.0
    matched = user_skills.intersection(job_required_skills)
    return len(matched) / len(job_required_skills)
```

### Embedding Text

Do not embed:

```text
About us
Company culture
Benefits
Legal footer
Cookie banner text
Navigation menu
Equal opportunity employer block
Random unrelated page content
```

Build job embedding text only from:

```text
title
level
location
work mode
responsibilities
requirements
skills
tech stack
```

Required shape:

```python
def build_embedding_text(job) -> str:
    parts = [
        f"Title: {job.title}" if job.title else None,
        f"Level: {job.level}" if job.level else None,
        f"Location: {job.location}" if job.location else None,
        f"Work mode: {job.work_mode}" if job.work_mode else None,
        f"Responsibilities: {job.responsibilities}" if job.responsibilities else None,
        f"Requirements: {job.requirements}" if job.requirements else None,
        f"Skills: {', '.join(job.skills)}" if job.skills else None,
    ]
    return "\n".join([part for part in parts if part])
```

Role query text must be built dynamically:

```python
def build_role_query_text(role_profile) -> str:
    parts = [
        f"Target role: {role_profile.target_role}" if role_profile.target_role else None,
        f"Level: {role_profile.level}" if role_profile.level else None,
        f"Location: {role_profile.location}" if role_profile.location else None,
        "Remote acceptable" if role_profile.accept_remote else None,
        f"Skills: {', '.join(role_profile.skills)}" if role_profile.skills else None,
        f"Resume/Profile: {role_profile.resume_text}" if role_profile.resume_text else None,
    ]
    return "\n".join([part for part in parts if part])
```

### Embedding and Semantic Similarity

Use `langchain_openai.OpenAIEmbeddings` configured from:

```text
OPENAI_EMBEDDING_MODEL
EMBEDDING_DIMENSION
OPENAI_API_KEY
```

Required helper behavior:

```python
async def embed_text(text: str) -> list[float]:
    """Return one embedding vector and validate its dimension."""
```

Rules:

- Do not call embeddings for non-scorable jobs.
- Do not embed raw HTML, raw scraped text, or full messy JD text.
- Build role text dynamically with `build_role_query_text(role_profile)`.
- Build job text with `build_embedding_text(job)`.
- Validate `len(vector) == settings.EMBEDDING_DIMENSION`.
- If embedding generation fails, keep the already committed job as `pending_review` with all score fields as `None` and set or append `error_reason`.
- Map the incoming `JobAgentState.user_warning` (if present) to the returned `JobProcessingResult.warnings`.

Semantic similarity:

```python
def normalize_qdrant_similarity_score(score: float) -> float:
    """Clamp the Qdrant cosine score to [0, 1] for final scoring."""
```

Use Qdrant as the canonical semantic similarity source for `embedding_similarity`, matching the Master Plan scoring path.

Ordering clarification:

```text
This phase follows the Master's explicit SQLite-first durability rule over the older architecture diagram ordering.
The canonical order is:
1. Insert the parsed job into SQLite as pending_review with nullable score fields.
2. Commit the SQLite row and use its canonical UUID as the Qdrant point ID.
3. Generate embeddings and upsert/query Qdrant.
4. Update the same SQLite row with score fields.
```

This avoids losing failed or partially processed jobs when embedding or Qdrant operations fail.

Required behavior:

- Build `embedding_text` locally from `build_embedding_text(job)` before insert when the job is scorable; this is deterministic string construction only and must not call external providers.
- Insert the SQLite row first with `status = pending_review`, the generated `embedding_text` if available, and nullable score fields so the canonical UUID `job_posts.id` exists before any external embedding or Qdrant call.
- Generate the role query embedding from `build_role_query_text(role_profile)` only after the SQLite row has committed.
- Generate the job vector from `build_embedding_text(job)` / the persisted `embedding_text` only after the SQLite row has committed.
- Upsert the scorable job vector into Qdrant using `job_posts.id` as the point ID.
- Query Qdrant with the role query vector using filters that include the active `role_profile_id`, `status = pending_review`, and the current point/job ID.
- Use the returned Qdrant cosine score as `embedding_similarity` after clamping to `[0, 1]`.
- Calculate deterministic score components, `base_score`, `final_score`, and `final_score_percent`.
- Update the same SQLite row with score fields after the Qdrant similarity score is available.

If Qdrant upsert or Qdrant similarity query fails, do not fall back to local cosine scoring in MVP. Keep the committed SQLite row visible as `pending_review`, set score fields to `None`, append/set an error reason, and return `qdrant_synced = false`.

### Qdrant Write/Read Consistency Guard

New scorable job scoring must not assume that a just-upserted vector is immediately visible to a filtered similarity query unless the Qdrant client call has explicitly requested write acknowledgement and the query can prove it found the current job.

Required behavior:

```text
1. Upsert the Qdrant point with `wait=True` or the client/library equivalent when available.
2. Use payload `job_id = current_job_id` and active `role_profile_id` + `status = pending_review` filters for the scoring query.
3. Treat "no point returned for current_job_id" as a transient Qdrant visibility/sync failure, not as a score of 0 and not as permission to use another job's score.
4. Retry the job-specific Qdrant scoring query with a small bounded retry policy such as 3 attempts with short backoff.
5. If the current job is still not returned, keep the SQLite row committed with null score fields, append/set `error_reason = "Qdrant similarity unavailable for newly upserted job"`, and return `qdrant_synced = false`.
```

Do not use local cosine fallback in this race condition path. The UI must still see the `pending_review` job, but score fields remain `null` until a later explicit reprocessing feature exists.

Durability rule:

```text
Dedup decision first.
SQLite insert second.
Embedding provider calls third.
Qdrant upsert/query fourth.
SQLite score update last.
```

The only exceptions are skipped duplicates, which do not insert or call embedding/Qdrant, and duplicate metadata rows, which insert `ignored` metadata and do not call embedding/Qdrant.

### Processing Pipeline Order

For each Plan 2 `JobAgentState`:

```text
1. Validate required state keys: batch_id, role_profile_id, input_source.
2. Load the role profile from SQLite.
3. Convert `extracted_job` into a job persistence payload.
4. Check exact duplicate by `raw_content_hash`.
5. Check duplicate by `dedup_key`.
6. If duplicate policy says skip, return a skipped result and do not embed.
7. If duplicate policy says insert ignored metadata, insert with:
   - status = ignored
   - duplicate_of_job_id = existing_job.id
   - should_score_similarity = false
   - all score fields = null
   - no Qdrant upsert
8. If non-duplicate and scorable:
   - build embedding_text
   - insert SQLite row first with a canonical UUID and nullable score fields
   - commit the row before external embedding or Qdrant calls
   - embed role query text
   - embed job embedding_text
   - upsert the job vector into Qdrant using the SQLite job ID as the point ID
   - query Qdrant for this job using role_profile_id, status, and point/job ID filters
   - use the Qdrant query score as embedding_similarity after clamping to [0, 1]
   - calculate deterministic score components
   - calculate final_score and final_score_percent
   - update the SQLite row with embedding and score fields
9. If non-duplicate and non-scorable:
   - persist with status = pending_review
   - all score fields = null
   - no Qdrant upsert
10. Return a processing result containing inserted/skipped/duplicate/qdrant status counts and inserted job IDs.
```

### Processing Result

`job_processing_service.py` should return an internal result object such as:

```python
from dataclasses import dataclass, field


@dataclass
class JobProcessingResult:
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    job_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

This is not a new database table.

### Deduplication

Use only:

```text
raw_content_hash
dedup_key = hash(normalized_company + normalized_title)
```

Null-safe dedup key rule:

```text
If either normalized_company or normalized_title is missing or blank, do not generate a dedup_key.
Never hash empty company/title values into a shared duplicate key.
Use raw_content_hash as the only duplicate signal for those rows.
```

Exact duplicate policy:

- Compute `raw_content_hash` from cleaned raw content.
- If `raw_content_hash` already exists, skip inserting a new row and count it as `skipped_exact_duplicate`.
- If `dedup_key` is `None` because company/title is incomplete, skip the dedup-key duplicate check.

Dedup key policy:

```python
# Import TRACKED_JOB_STATUSES from backend.app.core.constants.
TRACKED_STATUSES = TRACKED_JOB_STATUSES


def decide_duplicate_action(existing_job_status: str) -> str:
    if existing_job_status == "pending_review":
        return "skip_duplicate"
    if existing_job_status in TRACKED_STATUSES:
        return "mark_new_as_duplicate_ignored"
    if existing_job_status == "ignored":
        return "skip_duplicate"
    return "skip_duplicate"
```

If inserting duplicate metadata:

```text
duplicate_of_job_id = existing_job.id
status = ignored
should_score_similarity = false
final_score = null
```

Dashboard and review queue queries must exclude duplicates:

```sql
AND duplicate_of_job_id IS NULL
```

### Persistence

All non-skipped, non-duplicate-metadata parsed jobs are saved to SQLite with:

```text
status = pending_review
```

Explicit exception:

```text
Duplicate metadata rows for already tracked jobs are saved with:
status = ignored
duplicate_of_job_id = existing_job.id
should_score_similarity = false
all score fields = null
```

User approval later changes:

```text
pending_review -> saved
```

Allowed user-visible status transitions:

```text
pending_review -> ignored
pending_review -> saved
saved -> applied
saved -> rejected
applied -> interview
applied -> rejected
interview -> rejected
interview -> offer
```

### Service-Owned Status Transitions

`job_processing_service.py` owns status transition validation. FastAPI routes in Plan 4 must call these methods and translate service-domain errors into HTTP responses instead of duplicating transition rules.

Plan 5 frontend transition options must be generated from, exported from, or contract-tested against this backend transition map. The UI must not maintain an unverified independent transition map. Any `StatusSelect` options shown in the frontend must match backend-allowed transitions for the current job status, and frontend tests must fail if this backend map changes without an intentional frontend update.

Allowed transition map:

```python
# Build and validate this map against JOB_STATUSES and APPLICATION_STATUSES
# from backend.app.core.constants.
ALLOWED_STATUS_TRANSITIONS = {
    "pending_review": {"saved", "ignored"},
    "saved": {"applied", "rejected"},
    "applied": {"interview", "rejected"},
    "interview": {"rejected", "offer"},
    "rejected": set(),
    "offer": set(),
    "ignored": set(),
}
```

Required service behavior:

```python
class InvalidStatusTransition(ValueError):
    pass


async def approve_job(job_id: str) -> JobPost:
    """Validate pending_review -> saved, update SQLite, then update Qdrant payload."""


async def reject_job(job_id: str) -> JobPost:
    """Validate pending_review -> ignored, update SQLite, then delete the Qdrant point if present."""


async def update_job_status(job_id: str, status: Literal["applied", "interview", "rejected", "offer"]) -> JobPost:
    """Validate manual tracked transitions, update SQLite/applications, then update Qdrant payload."""
```

`PATCH /api/jobs/{id}/status` in Plan 4 must never pass `ignored`; only `reject_job(...)` can set review jobs to `ignored`.

### Applications Row Semantics

When `update_job_status(...)` changes a job to a tracked application state, it must create or update one `applications` row for that `job_post_id`.

Rules:

```text
1. If status becomes applied and no application row exists, create one with status = applied and applied_at = now.
2. If status becomes interview, rejected, or offer and an application row exists, update only applications.status and updated_at; preserve the existing applied_at.
3. If status becomes rejected directly from saved and no application row exists, create one with status = rejected and applied_at = null.
4. Do not create application rows for pending_review, saved, or ignored.
5. Do not create more than one application row for the same job_post_id.
```

### Qdrant Collection

Collection:

```text
job_posts
```

Runtime:

```text
QDRANT_URL=http://localhost:6333
```

Distance:

```text
Cosine
```

Vector size:

```text
EMBEDDING_DIMENSION from .env
default example: 1536
```

Point ID rule:

```text
Use job_posts.id as a standard UUID string.
Do not use arbitrary hash strings, slugs, or custom random text as Qdrant point IDs.
```

Payload:

```json
{
  "job_id": "job_post_uuid",
  "role_profile_id": "role_profile_uuid",
  "batch_id": "batch_uuid",
  "title": "AI Engineer Intern",
  "company": "ABC AI Lab",
  "location": "Ha Noi",
  "level": "intern",
  "jd_status": "full_jd",
  "status": "pending_review",
  "source_platform": "mock"
}
```

Qdrant rules:

- New scorable job: upsert vector.
- New scorable job scoring: query Qdrant with the role query vector and a job-specific filter; use the returned score for `embedding_similarity`.
- `embedding_text` changes: recompute vector.
- Job ignored or rejected from review queue: delete vector.
- Job deleted: delete vector.
- Job is not scorable: do not upsert vector.

Payload indexes:

```text
role_profile_id
status
jd_status
batch_id
source_platform
```

### Qdrant Failure Handling

SQLite remains the source of truth.

If Qdrant upsert, delete, payload update, or payload-index creation fails:

- Do not roll back the committed SQLite row.
- Log the Qdrant error.
- Return a processing result flag such as `qdrant_synced = false`.
- Keep the job visible in SQLite.
- Do not retry indefinitely in this phase.

If the Qdrant similarity query for a new scorable job fails after SQLite insert:

- Keep the SQLite row committed as `status = pending_review`.
- Set `embedding_similarity`, deterministic score components, `base_score`, `jd_confidence_multiplier`, `final_score`, and `final_score_percent` to `None`.
- Preserve `embedding_text` if it was generated.
- Set or append an `error_reason` explaining that Qdrant similarity failed.
- Return `qdrant_synced = false`.

Qdrant delete and payload update helpers must be idempotent.
Deleting a missing point should not fail the workflow.
The `QdrantService` must expose idempotent initialization that verifies whether the `job_posts` collection exists and creates it with the configured vector dimension and cosine metric if missing.
Plan 3 owns the initialization logic in `qdrant_service.py`; Plan 4 owns calling that logic from FastAPI startup. Unit tests may call it directly with mocked Qdrant clients.

During SQLite insertions, catch any `IntegrityError` caused by raw_content_hash unique collisions. When caught, roll back the transaction, fetch the existing job post ID, and return it as `skipped_exact_duplicate` without making Qdrant upsert calls.

### Qdrant Status Sync

SQLite is the source of truth.

Status-changing service methods must also update or delete Qdrant points:

```text
approve job -> SQLite status saved -> Qdrant payload status saved
reject job -> SQLite status ignored -> delete Qdrant point
manual status applied -> Qdrant payload status applied
manual status interview -> Qdrant payload status interview
manual status rejected -> Qdrant payload status rejected
manual status offer -> Qdrant payload status offer
delete job -> delete Qdrant point
```

Only review rejection (`pending_review -> ignored`) deletes the Qdrant point.
Manual tracked status `rejected` keeps the point and updates payload status to `rejected`.

**Service Layer Application Tracking Rule:**
- The `job_processing_service.update_job_status(job_id, status)` method is the single backend owner for status mutations.
- When `status` changes to any tracked state (`applied`, `interview`, `rejected`, or `offer`), this method MUST create or update the corresponding record in the `applications` table.
- API route handlers (in Plan 4) are strictly forbidden from implementing route-local business logic for `applications` record creation or Qdrant status updates; they must call the service methods directly to avoid drift.

### Query Isolation

Vector queries must filter by active role profile and status.

Pending review filter:

```python
def build_pending_review_filter(role_profile_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="role_profile_id",
                match=models.MatchValue(value=role_profile_id),
            ),
            models.FieldCondition(
                key="status",
                match=models.MatchValue(value="pending_review"),
            ),
        ]
    )
```

For saved dashboard search, use status `saved`.

Job-specific scoring filter:

```text
For computing the newly inserted job's `embedding_similarity`, the Qdrant query must also restrict the result to the current point/job ID.
This keeps scoring deterministic and prevents another pending job from supplying the score.
```

Implementation rule:

```text
The job-specific Qdrant filter must include payload field `job_id = current_job_id`.
If the Qdrant client supports direct point-ID lookup or a point-ID condition, use that as an additional guard.
Do not accept the highest-scoring result from other pending jobs as the newly inserted job's embedding_similarity.
```

## 8. Implementation Steps

- [ ] Create `backend/app/services/scoring_service.py`.
- [ ] Import Plan 1 constants for executable status/source/JD validation in scoring, deduplication, persistence, and status transition services.
- [ ] Implement `normalize_skill`, skill alias mapping, and skill overlap.
- [ ] Implement `build_embedding_text` and `build_role_query_text`.
- [ ] Implement location and level scoring.
- [ ] Implement JD confidence multiplier, base score, final score, and final percent.
- [ ] Create `backend/app/services/embedding_service.py`.
- [ ] Implement OpenAI embedding generation using configured model and dimension.
- [ ] Implement Qdrant similarity query scoring and clamp the returned score to `[0, 1]`.
- [ ] Create `backend/app/services/dedup_service.py`.
- [ ] Implement `raw_content_hash` exact duplicate check.
- [ ] Implement null-safe `dedup_key` generation and duplicate action policy.
- [ ] Create `backend/app/services/job_processing_service.py`.
- [ ] Implement the full Plan 2 state -> dedup -> score -> SQLite -> Qdrant pipeline.
- [ ] Implement `ALLOWED_STATUS_TRANSITIONS` and service-level transition validation in an importable backend module consumed by both status mutation services and the Plan 4 API contract export.
- [ ] Implement `InvalidStatusTransition` or an equivalent domain error for invalid status changes.
- [ ] Ensure `approve_job`, `reject_job`, and `update_job_status` are the only backend status mutation entrypoints consumed by routes.
- [ ] Ensure tracked status updates create or update exactly one `applications` row with the defined `applied_at` semantics.
- [ ] Add persistence helpers that convert Plan 2 extraction state into `job_posts` rows.
- [ ] Ensure every persisted new job defaults to `status = pending_review`.
- [ ] Ensure every non-duplicate scorable job commits a SQLite row before calling OpenAI embeddings or Qdrant.
- [ ] Ensure duplicate metadata rows use `status = ignored` and `duplicate_of_job_id`.
- [ ] Ensure duplicate skipped jobs do not call embedding or Qdrant.
- [ ] Ensure non-scorable jobs do not call embedding or Qdrant.
- [ ] Ensure embedding failures persist jobs with null score fields and `error_reason`.
- [ ] Create `backend/app/services/qdrant_service.py`.
- [ ] Implement idempotent collection creation with configured embedding dimension and cosine distance.
- [ ] Expose Qdrant collection initialization so Plan 4 can invoke it during FastAPI startup.
- [ ] Implement Qdrant payload indexes.
- [ ] Implement vector upsert for scorable jobs only.
- [ ] Implement Qdrant similarity query for newly inserted scorable jobs.
- [ ] Upsert Qdrant points with write acknowledgement (`wait=True` or client equivalent) and add a bounded retry for the current-job scoring query.
- [ ] Implement point deletion for ignored review jobs and deleted jobs.
- [ ] Implement payload status update for saved/applied/interview/rejected/offer.
- [ ] Ensure Qdrant failures do not roll back SQLite commits.
- [ ] Use update-payload for manual `rejected`; delete only for `ignored`.
- [ ] Implement role-profile and status filter builders.
- [ ] Add constants contract tests proving Plan 3 policies use Plan 1 shared constants instead of independent executable status sets.
- [ ] Add unit tests for every deterministic scoring function.
- [ ] Add tests for dedup decision policy.
- [ ] Add integration tests with SQLite for persistence and duplicate exclusion.
- [ ] Add mocked Qdrant tests for upsert, delete, payload update, and filters.

## 9. Verification & Testing Plan

Automated tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Focused checks:

```powershell
pytest tests/test_embedding_service.py
pytest tests/test_scoring_service.py
pytest tests/test_dedup_service.py
pytest tests/test_job_processing_service.py
pytest tests/test_job_persistence.py
pytest tests/test_qdrant_service.py
```

Expected scoring test cases:

- `full_jd` with base score `0.80` produces final score `0.80`.
- `partial_jd` with base score `0.80` produces final score `0.68`.
- `contact_for_jd`, `no_jd`, and `unclear` produce null score fields.
- Skill overlap returns `0.0` when job required skills are empty.
- Alias normalization maps "Retrieval-Augmented Generation" to `rag`.
- Location exact match returns `1.0`.
- Remote acceptable partial match returns `0.5`.
- Level `intern` vs `fresher` returns `0.5`.

Expected embedding/scoring pipeline tests:

- Scorable job calls embedding for role query and job text.
- Non-scorable job does not call embedding.
- Duplicate skipped job does not call embedding.
- Embedding vector dimension mismatch returns null score fields and an error reason.
- Embedding provider failure does not crash processing and still persists the job.
- Embedding provider failure happens after SQLite insert and leaves the committed row as `pending_review` with null score fields and an error reason.
- Qdrant query score is clamped to `[0, 1]`.
- Qdrant similarity query failure does not crash processing and leaves the persisted job with null score fields plus an error reason.
- Qdrant eventual-consistency visibility failure after upsert uses bounded retries, never borrows another job's score, and leaves the persisted row with null score fields plus `qdrant_synced = false` if the current job is not returned.

Expected dedup test cases:

- Duplicate `raw_content_hash` skips insert.
- Existing `pending_review` duplicate skips insert.
- Existing tracked duplicate can be inserted only as `status = ignored` with `duplicate_of_job_id`.
- Existing `ignored` duplicate skips insert.
- Missing company or missing title produces `dedup_key = None` and does not collide with other unclear jobs.

Expected persistence/Qdrant tests:

- SQLite row is committed before Qdrant upsert.
- SQLite row is committed before OpenAI embedding calls for scorable jobs.
- Scorable job updates the committed SQLite row after Qdrant returns the similarity score.
- Qdrant upsert failure keeps the SQLite row.
- Qdrant similarity query failure keeps the SQLite row with null score fields.
- Duplicate metadata row is inserted as `ignored` and does not upsert Qdrant.
- Invalid status transitions raise the service domain error before SQLite or Qdrant mutation.
- `ALLOWED_STATUS_TRANSITIONS` is importable by the Plan 4 API contract export and validates only statuses from Plan 1 constants.
- `saved -> rejected` creates one `applications` row with `applied_at = null` when no prior application exists.
- `applied -> interview/rejected` updates the existing `applications` row and preserves `applied_at`.
- Manual `rejected` updates Qdrant payload instead of deleting.
- Review reject to `ignored` deletes Qdrant point idempotently.

Expected Qdrant test cases:

- Scorable job upserts with canonical UUID point ID.
- Scorable job uses Qdrant query score for `embedding_similarity`.
- Scorable job upsert requests write acknowledgement before the scoring query.
- Non-scorable job does not upsert.
- Review reject to `ignored` deletes point.
- Approve updates payload status to `saved`.
- Pending review filter includes both `role_profile_id` and `status`.
- Job-specific scoring filter includes the current point/job ID.
- If the job-specific scoring query returns no current job after bounded retries, score fields stay null and the service returns `qdrant_synced = false`.
- Payload indexes are requested for configured fields.

Manual verification:

```powershell
docker compose up -d qdrant
```

- Run a local mocked extraction result through the scoring and persistence pipeline.
- Confirm the SQLite row is created with `status = pending_review`.
- Confirm scorable jobs create Qdrant points.
- Confirm non-scorable jobs are persisted without Qdrant points.
- Confirm review rejection to `ignored` deletes the Qdrant point.

## 10. Handoff Notes for Phase 4

Plan 4 consumes:

- Deterministic scoring functions.
- Deduplication service and duplicate action policy.
- Persistence helpers for extraction results and warning propagation through `JobProcessingResult.warnings`.
- Qdrant collection auto-initialization, upsert, similarity query scoring, delete, payload update, and filter helpers.
- Qdrant write/read consistency behavior for newly upserted points, including write acknowledgement, job-specific filtering, bounded retry, and null-score fallback when the current point is not visible.
- Status mutation service behavior that validates allowed transitions, creates/updates `applications`, and keeps SQLite and Qdrant synchronized.
- Canonical `ALLOWED_STATUS_TRANSITIONS` values that Plan 4 must export in the API contract and Plan 5 must consume or contract-test before rendering `StatusSelect` options.
- Propagated warning strings in `JobProcessingResult.warnings`.

Plan 4 must:

- Call `job_processing_service.py` instead of reimplementing scoring, deduplication, embedding, persistence, or Qdrant sync inside route handlers.
- Call Plan 3 status mutation methods instead of reimplementing status transition checks, application-row creation, or Qdrant status sync in route handlers.
- Call the Plan 3 Qdrant initialization helper during FastAPI startup; do not duplicate collection or payload-index creation logic in route modules.
- Pass `input_source = "tavily"` to the Plan 2 URL extraction entrypoint for Tavily search results.
- Add Tavily search and route-level input validation.
- Add `seed_demo.py` and mock data that reuse the same persistence and Qdrant services.
- Keep SQLite as the source of truth for job status.
- Keep Plan 1 shared constants as the source of truth for executable status/source validation.
- Ensure the API routes explicitly map `JobProcessingResult.warnings` to the ingestion response `warnings` array.
- Fetch full job rows for `JobProcessingResult.job_ids` before returning ingestion responses with a `jobs` array.
- Rely on `job_processing_service.update_job_status(...)` to create or update the corresponding `applications` row when manual job status changes to `applied`, `interview`, `rejected`, or `offer` occur.
- Export or expose the canonical status transition map through Plan 4's API contract artifact so Plan 5 cannot silently drift from backend transition rules.

Hard rules for later phases:

- API routes must reuse Plan 3 services and must not duplicate scoring or dedup logic.
- Demo seeding must use the same score and Qdrant sync behavior as real parsing.
- Later phases must not re-open duplicates of saved, applied, interview, rejected, or offer jobs into `pending_review`.
- Qdrant collection checks and creations must occur dynamically through `QdrantService` initialization / `ensure_collection()` methods.
- Plan 4 may invoke Qdrant startup initialization, but Plan 3 remains the only owner of Qdrant collection and payload-index logic.
- The `seed_demo.py` CLI script must follow the Master Plan command: `python scripts/seed_demo.py --reset` from the `backend/` directory.
