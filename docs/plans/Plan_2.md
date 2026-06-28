# Plan 2 - LangGraph Extraction and Input Parsing

## 1. Objective

Implement the AI extraction layer up to structured job extraction and JD classification. This phase accepts raw text or fetched URL content, cleans it, runs Pydantic structured output through an LLM, retries once on invalid output, and returns a resilient `JobAgentState` result without scoring or persistence.

The goal is to make extraction reliable and testable before adding scoring, deduplication, Qdrant, API routes, or frontend behavior.

## 2. Source of Truth

- `Master_Plan.md` section 4, "Architecture"
- `Master_Plan.md` section 4.1, "LangGraph State Tracking"
- `Master_Plan.md` section 6, "Input Sources"
- `Master_Plan.md` section 7, "Handling JavaScript Pages and Cookie Banners"
- `Master_Plan.md` section 8, "JD Status Rules"
- `Master_Plan.md` section 18, "LLM JSON Fallback"
- `Master_Plan.md` section 27, "URL Parsing Security Note"
- `Master_Plan.md` section 28, "Input Size and Retry Limits"
- `Master_Plan.md` section 29, "Pydantic Schema Sketch"
- `Master_Plan.md` section 30, "Project Directory Structure"
- `Master_Plan.md` section 35, "Implementation Checklist: LangGraph State, Extraction, Search and Parsing"

## 3. Prerequisites from Prior Phases

- [ ] Plan 1 backend package structure exists.
- [ ] Plan 1 environment settings exist.
- [ ] Plan 1 backend dependencies are installable.
- [ ] `backend/app/core/config.py` exposes input limits and model settings.
- [ ] `backend/app/db/models.py` already defines final persistence fields, but this phase does not write to them.

## 4. Scope

- Define `JobAgentState` as the shared LangGraph state contract.
- Define `JobPostExtract` as the Pydantic structured output schema.
- Add extraction prompts and repair prompts.
- Add a URL fetch and clean path using `httpx` plus `trafilatura`.
- Add raw text cleaning and truncation using configured size limits.
- Detect low-content or unreliable URL extraction and set `parse_status = needs_manual_input`.
- Add LangGraph nodes for:
  - preparing content
  - extracting structured job output
  - retrying once with a repair prompt
  - classifying JD status
  - marking unclear fallback records
- Add a graph builder that runs extraction through JD classification.
- Capture extraction observability fields: token counts, estimated cost, extraction time, error reason, and user warning when available.
- Add unit tests with mocked LLM responses and mocked URL content.

## 5. Out of Scope

- Do not save jobs to SQLite.
- Do not calculate embedding similarity.
- Do not calculate final scores.
- Do not implement skill overlap, location score, or level score.
- Do not create, query, or update Qdrant collections.
- Do not implement Tavily search.
- Do not implement FastAPI route handlers except optional internal import smoke tests.
- Do not implement `seed_demo.py` or mock data files.
- Do not implement React UI.
- Do not use Playwright or browser rendering for MVP parsing.
- Do not add custom HTML parser logic beyond `trafilatura` unless needed for a controlled demo source.

## 6. Target Directory Structure

```text
backend/
`-- app/
    |-- agents/
    |   |-- __init__.py
    |   |-- graph.py
    |   |-- nodes.py
    |   |-- prompts.py
    |   `-- schemas.py
    |-- services/
    |   |-- __init__.py
    |   |-- cost_service.py
    |   `-- extraction_service.py
    `-- tests/
        |-- __init__.py
        |-- test_extraction_graph.py
        |-- test_extraction_schema.py
        `-- test_url_cleaning.py
```

If the repository does not already use `backend/app/tests`, place tests under `backend/tests/` but keep the same test names.

## 7. Technical Specifications

### JobAgentState

Define this state in `backend/app/agents/schemas.py`:

```python
from typing import Any, Literal, TypedDict


class JobAgentState(TypedDict, total=False):
    batch_id: str
    role_profile_id: str
    input_source: Literal["tavily", "manual_url", "manual_text", "mock"]

    source_url: str | None
    raw_text: str | None
    raw_content_hash: str | None

    clean_text: str | None
    parse_status: Literal["success", "needs_manual_input", "failed"]
    extracted_job: dict[str, Any] | None
    jd_status: Literal["full_jd", "partial_jd", "contact_for_jd", "no_jd", "unclear"] | None
    should_score_similarity: bool | None

    embedding_text: str | None
    embedding_similarity: float | None
    skill_overlap_score: float | None
    location_match_score: float | None
    level_match_score: float | None
    base_score: float | None
    jd_confidence_multiplier: float | None
    final_score: float | None
    final_score_percent: float | None

    extraction_status: Literal["success", "retried", "failed"] | None
    error_reason: str | None
    user_warning: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    extraction_time_ms: int | None
```

Every node must return partial updates that preserve these required fields:

```text
batch_id
role_profile_id
input_source
```

Implementation should use a small helper such as `preserve_required_state(state)` so every node includes:

```python
{
    "batch_id": state["batch_id"],
    "role_profile_id": state["role_profile_id"],
    "input_source": state["input_source"],
}
```

Tests must cover this for success, retry success, retry failure, and low-content URL paths.

### JobPostExtract

Define this Pydantic model in `backend/app/agents/schemas.py`:

```python
from typing import Literal
from pydantic import BaseModel, Field


class JobPostExtract(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    work_mode: Literal["onsite", "remote", "hybrid", "unknown"] = "unknown"
    level: Literal["intern", "fresher", "junior", "mid", "senior", "unknown"] = "unknown"
    employment_type: Literal["internship", "full-time", "part-time", "contract", "unknown"] = "unknown"
    salary: str | None = None

    responsibilities: str | None = None
    requirements: str | None = None
    skills: list[str] = Field(default_factory=list)

    source_url: str | None = None
    source_platform: str

    jd_status: Literal["full_jd", "partial_jd", "contact_for_jd", "no_jd", "unclear"]
    should_score_similarity: bool

    extraction_notes: str | None = None
```

### Source Mapping

Map `JobAgentState.input_source` to `JobPostExtract.source_platform` exactly:

| input_source | source_platform |
|---|---|
| tavily | tavily |
| manual_url | manual_url |
| manual_text | manual_text |
| mock | mock |

`job_board` is allowed in the database schema but is not produced by Plan 2 unless a later approved phase adds normalization for known boards.

### JD Status Rules

Extraction must produce one of:

```text
full_jd
partial_jd
contact_for_jd
no_jd
unclear
```

Rules:

- `full_jd`: clear responsibilities, requirements, and skills.
- `partial_jd`: useful JD details exist but are incomplete.
- `contact_for_jd`: content asks the user to inbox, DM, or comment for JD.
- `no_jd`: hiring mention exists but no useful JD details exist.
- `unclear`: extraction failed or content is unreliable.

Only `full_jd` and `partial_jd` set `should_score_similarity = true`.

### URL Parsing

URL parsing must:

- Allow only `http` and `https` URLs.
- Use configured request timeout.
- Limit response size using `MAX_RESPONSE_SIZE_MB`.
- Use `httpx` for fetch.
- Use `trafilatura` as the primary HTML-to-text extractor.
- Define a concrete low-content threshold where clean text has fewer than 150 characters, or use the helper function `is_unreliable_extraction(text)`.
- Set `parse_status = "needs_manual_input"` when extracted text falls below the low-content threshold, or is blocked, login-gated, or JavaScript-only.
- Set `parse_status = "success"` when text extraction successfully passes the threshold checks.
- Return this warning when URL extraction is unreliable:

```text
We could not extract enough job content from this URL.
The page may require JavaScript rendering, login, or cookie acceptance.
Please paste the job description text manually.
```

Low-content or unreliable URL extraction must not ask the LLM to hallucinate a job.

If `trafilatura` returns text that falls below the threshold, return this state:

```python
{
    "batch_id": state["batch_id"],
    "role_profile_id": state["role_profile_id"],
    "input_source": state["input_source"],
    "source_url": state.get("source_url"),
    "raw_text": None,
    "clean_text": extracted_text_or_none,
    "raw_content_hash": content_hash_or_none,
    "parse_status": "needs_manual_input",
    "extracted_job": {
        "title": None,
        "company": None,
        "location": None,
        "responsibilities": None,
        "requirements": None,
        "skills": [],
        "source_url": state.get("source_url"),
        "source_platform": map_input_source_to_source_platform(state["input_source"]),
        "jd_status": "unclear",
        "should_score_similarity": False,
        "extraction_notes": "URL content was too short or unreliable for extraction",
    },
    "jd_status": "unclear",
    "should_score_similarity": False,
    "embedding_text": None,
    "embedding_similarity": None,
    "skill_overlap_score": None,
    "location_match_score": None,
    "level_match_score": None,
    "base_score": None,
    "jd_confidence_multiplier": None,
    "final_score": None,
    "final_score_percent": None,
    "extraction_status": "failed",
    "error_reason": "URL content was too short or unreliable for extraction",
    "user_warning": "We could not extract enough job content from this URL.\nThe page may require JavaScript rendering, login, or cookie acceptance.\nPlease paste the job description text manually.",
}
```

Add the production note in URL parsing code:

```text
Production note: Implement SSRF mitigation for URL parsing endpoints.
Block localhost, private IPs, link-local metadata IPs, unsafe redirects, and internal network targets.
```

### Input Limits

Use Plan 1 settings:

```text
MAX_RAW_TEXT_CHARS=20000
MAX_CLEAN_TEXT_CHARS=12000
MAX_RETRY_PER_JOB=1
REQUEST_TIMEOUT_SECONDS=10
MAX_RESPONSE_SIZE_MB=2
```

If content is too long:

- Extract readable text with `trafilatura` first when URL based.
- Prefer job-related sections.
- Truncate low-signal content.
- Ask for manual paste when extraction confidence is low.

### LLM Fallback

Extraction flow:

```text
raw content -> LLM structured output -> Pydantic validation
invalid output -> repair prompt retry once -> Pydantic validation
still invalid -> mark unclear
```

Fallback result must include:

```json
{
  "parse_status": "failed",
  "extracted_job": {
    "title": null,
    "company": null,
    "location": null,
    "responsibilities": null,
    "requirements": null,
    "skills": [],
    "jd_status": "unclear",
    "should_score_similarity": false
  },
  "jd_status": "unclear",
  "should_score_similarity": false,
  "embedding_text": null,
  "embedding_similarity": null,
  "skill_overlap_score": null,
  "location_match_score": null,
  "level_match_score": null,
  "base_score": null,
  "jd_confidence_multiplier": null,
  "final_score": null,
  "final_score_percent": null,
  "extraction_status": "failed",
  "error_reason": "LLM output failed schema validation after retry"
}
```

The actual returned `JobAgentState` must also preserve `batch_id`, `role_profile_id`, and `input_source`.

## 8. Implementation Steps

- [ ] Create `backend/app/agents/schemas.py` with `JobAgentState` and `JobPostExtract`.
- [ ] Create `backend/app/agents/prompts.py` with extraction and repair prompt templates.
- [ ] Create `backend/app/services/cost_service.py` for token and estimated cost calculations.
- [ ] Ensure `input_tokens`, `output_tokens`, `estimated_cost_usd`, and `extraction_time_ms` are always returned as provider values or explicitly `None`.
- [ ] Create `backend/app/services/extraction_service.py` for URL fetch, text cleaning, content hashing, LLM structured output, and retry orchestration.
- [ ] Create `backend/app/agents/nodes.py` with content preparation, extraction, retry, classification, and `mark_unclear` nodes.
- [ ] Create `backend/app/agents/graph.py` to compile and run the extraction graph.
- [ ] Ensure every node preserves `batch_id`, `role_profile_id`, and `input_source`.
- [ ] Add source mapping from `input_source` to `source_platform`.
- [ ] Ensure URL parsing uses `httpx` and `trafilatura`.
- [ ] Ensure low-content URL parsing returns `parse_status = needs_manual_input` and the configured user warning.
- [ ] Ensure low-content URL parsing skips LLM extraction and returns `needs_manual_input`.
- [ ] Ensure invalid LLM output retries exactly once.
- [ ] Ensure failed extraction returns `jd_status = unclear`, `should_score_similarity = false`, and score fields as `None`.
- [ ] Ensure every failure path sets all score fields to `None`.
- [ ] Ensure `raw_content_hash` is computed from cleaned content when clean content exists.
- [ ] Add a reusable helper for preserving required state keys.
- [ ] Add mocked tests for valid extraction, retry success, retry failure, low-content URL extraction, and state key preservation.

## 9. Verification & Testing Plan

Automated tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Focused checks:

```powershell
pytest tests/test_extraction_schema.py
pytest tests/test_extraction_graph.py
pytest tests/test_url_cleaning.py
```

Expected test coverage:

- Valid LLM JSON validates as `JobPostExtract`.
- Invalid first LLM response retries once.
- Invalid response after retry returns `jd_status = unclear`.
- `mark_unclear` preserves `batch_id`, `role_profile_id`, and `input_source`.
- `manual_text` input does not require URL fetch.
- `manual_url` input uses `httpx` and `trafilatura`.
- Low-content URL output sets `parse_status = needs_manual_input`.
- Low-content URL path does not call the LLM.
- Low-content URL path returns `jd_status = unclear`, `should_score_similarity = false`, and all score fields as `None`.
- Low-content URL path preserves `batch_id`, `role_profile_id`, and `input_source`.
- Low-content URL path returns the exact stable `user_warning` text.
- `input_source` maps to the expected `source_platform`.
- Invalid URL scheme rejects non-http/non-https URLs.
- Timeout or oversized response returns `parse_status = failed` or `needs_manual_input` without crashing the graph.
- Token, cost, and extraction time fields are present or explicitly `None`.

Manual verification:

- Run an extraction service call with a mocked raw JD and confirm a structured dict is returned.
- Run an extraction service call with intentionally bad LLM output and confirm the graph does not crash.
- Confirm no SQLite rows are inserted by this phase.
- Confirm no Qdrant collection is created by this phase.

## 10. Handoff Notes for Phase 3

Plan 3 consumes:

- `JobAgentState` with extraction, scoring placeholder fields, and `user_warning`.
- `JobPostExtract` validated output shape.
- `clean_text`, `raw_content_hash`, `parse_status`, `extracted_job`, `jd_status`, `should_score_similarity`, `user_warning`, and observability fields.
- The guarantee that all failed extractions return `jd_status = unclear` and preserve foreign key context.

Plan 3 must be able to persist both successful extraction states and low-content/manual-input states. Plan 2 guarantees that these states always include `batch_id`, `role_profile_id`, `input_source`, `parse_status`, `jd_status`, `should_score_similarity`, and nullable score placeholders.

Plan 3 must:

- Build clean embedding text only from extracted job fields.
- Score only `full_jd` and `partial_jd`.
- Save every parsed job to SQLite first as `pending_review` unless dedup rules skip or mark a duplicate.
- Add deduplication, scoring, persistence, and Qdrant sync without changing Plan 2 schemas.
- Map `JobAgentState.user_warning` into Plan 3 `JobProcessingResult.warnings` when propagating warning messages to later stages.
- Persist controlled unclear fallback records using Phase 3 storage utilities (Phase 4 invokes the Phase 3 pipeline).

Hard rules for later phases:

- Do not make the extraction graph responsible for final scoring.
- Do not let any node drop `batch_id`, `role_profile_id`, or `input_source`.
- Do not introduce Playwright/browser rendering in the MVP parser.
- Do not let one bad job crash an entire batch.
- Terminal success states of the extraction graph must hand off `extracted_job` as a `JobPostExtract.model_dump()` dictionary so Phase 3 services can ingest it directly.
