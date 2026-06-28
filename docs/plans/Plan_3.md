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
- [ ] Plan 1 Qdrant Docker Compose file exists.
- [ ] Plan 2 extraction graph returns `JobAgentState`.
- [ ] Plan 2 `JobPostExtract` schema is stable.
- [ ] `batch_id`, `role_profile_id`, and `input_source` are preserved by extraction.

## 4. Scope

- Implement deterministic scoring utilities in `scoring_service.py`.
- Implement skill alias normalization.
- Implement `build_embedding_text(job)` from clean extracted fields only.
- Implement `build_role_query_text(role_profile)` dynamically without storing it.
- Implement `embedding_service.py` using `OPENAI_EMBEDDING_MODEL` from settings.
- Generate embeddings for both `build_role_query_text(role_profile)` and `build_embedding_text(job)`.
- Validate embedding vector length against `EMBEDDING_DIMENSION`.
- Calculate `embedding_similarity` as normalized cosine similarity between role and job embeddings.
- Implement location and level scoring using three-tier rules.
- Implement skill overlap normalized to `[0, 1]`.
- Implement base score and final score formulas.
- Implement JD confidence multiplier for `full_jd` and `partial_jd`.
- Ensure embedding/scoring failures do not crash the whole batch; persist the job with null score fields and an error reason.
- Implement deduplication by `raw_content_hash` first and `dedup_key` second.
- Implement duplicate status policy so saved, applied, interview, rejected, and offer jobs do not re-enter `pending_review`.
- Implement job persistence using the Plan 1 `job_posts` schema.
- Add one orchestration helper that converts a Plan 2 `JobAgentState` into a persisted `job_posts` row and optional Qdrant point.
- Implement Qdrant collection creation with cosine distance and embedding dimension from `.env`.
- Implement Qdrant payload indexes.
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
qdrant_service.py          -> Qdrant collection, indexes, upsert/delete/filter/status payload
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
- If embedding generation fails, persist the job as `pending_review` with all score fields as `None` and `error_reason` set.
- Map the incoming `JobAgentState.user_warning` (if present) to the returned `JobProcessingResult.warnings`.

Semantic similarity:

Use local cosine similarity calculation as the primary path to score role and job embedding pairs.

```python
def calculate_embedding_similarity(role_vector: list[float], job_vector: list[float]) -> float:
    """Return cosine similarity clamped to [0, 1]."""
```

`embedding_similarity` must be normalized and clamped to `[0, 1]` before use in the final score. Do not rely on Qdrant query scores for the final score, only for candidate retrieval.

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
   - embed role query text
   - embed job embedding_text
   - calculate embedding_similarity
   - calculate deterministic score components
   - calculate final_score and final_score_percent
9. If non-duplicate and non-scorable:
   - persist with status = pending_review
   - all score fields = null
   - no Qdrant upsert
10. Insert SQLite row first using a canonical UUID string.
11. After SQLite commit, upsert Qdrant point only if the job is scorable and embedding succeeded.
12. Return a processing result containing inserted/skipped/duplicate/qdrant status counts.
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

Exact duplicate policy:

- Compute `raw_content_hash` from cleaned raw content.
- If `raw_content_hash` already exists, skip inserting a new row and count it as `skipped_exact_duplicate`.

Dedup key policy:

```python
TRACKED_STATUSES = {"saved", "applied", "interview", "rejected", "offer"}


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

Status flow:

```text
pending_review -> saved -> applied -> interview -> rejected -> offer
pending_review -> ignored
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

Qdrant delete and payload update helpers must be idempotent.
Deleting a missing point should not fail the workflow.
The `QdrantService` must dynamically verify if the `job_posts` collection exists during backend startup, and initialize it with the configured vector dimension and cosine metric if missing.

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

## 8. Implementation Steps

- [ ] Create `backend/app/services/scoring_service.py`.
- [ ] Implement `normalize_skill`, skill alias mapping, and skill overlap.
- [ ] Implement `build_embedding_text` and `build_role_query_text`.
- [ ] Implement location and level scoring.
- [ ] Implement JD confidence multiplier, base score, final score, and final percent.
- [ ] Create `backend/app/services/embedding_service.py`.
- [ ] Implement OpenAI embedding generation using configured model and dimension.
- [ ] Implement cosine similarity calculation and clamp result to `[0, 1]`.
- [ ] Create `backend/app/services/dedup_service.py`.
- [ ] Implement `raw_content_hash` exact duplicate check.
- [ ] Implement `dedup_key` generation and duplicate action policy.
- [ ] Create `backend/app/services/job_processing_service.py`.
- [ ] Implement the full Plan 2 state -> dedup -> score -> SQLite -> Qdrant pipeline.
- [ ] Add persistence helpers that convert Plan 2 extraction state into `job_posts` rows.
- [ ] Ensure every persisted new job defaults to `status = pending_review`.
- [ ] Ensure duplicate metadata rows use `status = ignored` and `duplicate_of_job_id`.
- [ ] Ensure duplicate skipped jobs do not call embedding or Qdrant.
- [ ] Ensure non-scorable jobs do not call embedding or Qdrant.
- [ ] Ensure embedding failures persist jobs with null score fields and `error_reason`.
- [ ] Create `backend/app/services/qdrant_service.py`.
- [ ] Implement collection creation with configured embedding dimension and cosine distance.
- [ ] Implement Qdrant payload indexes.
- [ ] Implement vector upsert for scorable jobs only.
- [ ] Implement point deletion for ignored review jobs and deleted jobs.
- [ ] Implement payload status update for saved/applied/interview/rejected/offer.
- [ ] Ensure Qdrant failures do not roll back SQLite commits.
- [ ] Use update-payload for manual `rejected`; delete only for `ignored`.
- [ ] Implement role-profile and status filter builders.
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
- Cosine similarity is clamped to `[0, 1]`.

Expected dedup test cases:

- Duplicate `raw_content_hash` skips insert.
- Existing `pending_review` duplicate skips insert.
- Existing tracked duplicate can be inserted only as `status = ignored` with `duplicate_of_job_id`.
- Existing `ignored` duplicate skips insert.

Expected persistence/Qdrant tests:

- SQLite row is committed before Qdrant upsert.
- Qdrant upsert failure keeps the SQLite row.
- Duplicate metadata row is inserted as `ignored` and does not upsert Qdrant.
- Manual `rejected` updates Qdrant payload instead of deleting.
- Review reject to `ignored` deletes Qdrant point idempotently.

Expected Qdrant test cases:

- Scorable job upserts with canonical UUID point ID.
- Non-scorable job does not upsert.
- Review reject to `ignored` deletes point.
- Approve updates payload status to `saved`.
- Pending review filter includes both `role_profile_id` and `status`.
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
- Qdrant collection auto-initialization, upsert, delete, payload update, and filter helpers.
- Status mutation service behavior that keeps SQLite and Qdrant synchronized.
- Propagated warning strings in `JobProcessingResult.warnings`.

Plan 4 must:

- Call `job_processing_service.py` instead of reimplementing scoring, deduplication, embedding, persistence, or Qdrant sync inside route handlers.
- Add Tavily search and route-level input validation.
- Add `seed_demo.py` and mock data that reuse the same persistence and Qdrant services.
- Keep SQLite as the source of truth for job status.
- Ensure the API routes explicitly map `JobProcessingResult.warnings` to warning fields in API response DTOs.
- Rely on `job_processing_service.update_job_status(...)` to create or update the corresponding `applications` row when manual job status changes to `applied`, `interview`, `rejected`, or `offer` occur.

Hard rules for later phases:

- API routes must reuse Plan 3 services and must not duplicate scoring or dedup logic.
- Demo seeding must use the same score and Qdrant sync behavior as real parsing.
- Later phases must not re-open duplicates of saved, applied, interview, rejected, or offer jobs into `pending_review`.
- Qdrant collection checks and creations must occur dynamically during `QdrantService` constructor initialization.
- The `seed_demo.py` CLI script must follow the Master Plan command: `python scripts/seed_demo.py --reset` from the `backend/` directory.
