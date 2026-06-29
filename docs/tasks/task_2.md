# Plan 2 - LangGraph Extraction and Input Parsing Execution Tasks

## Purpose

Implement the extraction-only phase of the Agentic Job Matching System: accept manual text or URL-derived content, clean and bound the input, produce validated structured job data through a LangGraph workflow, retry invalid LLM output once, classify JD completeness, and return a resilient `JobAgentState`.

This task file stops at extraction and JD classification. It does not add persistence, deduplication, scoring, Qdrant, Tavily search, API routes, or frontend behavior.

## Authoritative Source

Source precedence for execution:

1. `docs/plans/Master_Plan.md` is the architecture and MVP source of truth.
2. `docs/plans/Plan_2.md` defines the approved Phase 2 boundary and detailed extraction contracts where it does not conflict with the master plan.
3. `README.md` records the current Phase 1 project state and established file layout; it does not override either plan.

Comparison result:

- No architecture, scope, batch-order, or validation conflict was found between the master plan and Plan 2.
- The README confirms the Phase 1 backend package, settings, shared constants, dependencies, database models, and test layout already exist.
- New tests must use the established `backend/tests/` directory.
- Existing Phase 1 settings and constants must be reused rather than redefined.

## Source Section Index

- `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack` -> approved backend and agent stack.
- `docs/plans/Master_Plan.md` > `## 4. Architecture` -> extraction, validation, retry, classification, and unclear fallback flow.
- `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking` -> shared state and required-key preservation.
- `docs/plans/Master_Plan.md` > `## 6. Input Sources` -> supported MVP input types.
- `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners` -> URL extraction and manual-input fallback.
- `docs/plans/Master_Plan.md` > `## 8. JD Status Rules` -> JD classification and scoring eligibility.
- `docs/plans/Master_Plan.md` > `## 15. Cost & Performance Metrics Panel` -> stored extraction usage and timing fields.
- `docs/plans/Master_Plan.md` > `## 18. LLM JSON Fallback` -> one repair attempt and resilient unclear result.
- `docs/plans/Master_Plan.md` > `## 27. URL Parsing Security Note` -> MVP URL safety boundary.
- `docs/plans/Master_Plan.md` > `## 28. Input Size and Retry Limits` -> configured limits and one-retry cap.
- `docs/plans/Master_Plan.md` > `## 29. Pydantic Schema Sketch` -> structured extraction fields and defaults.
- `docs/plans/Master_Plan.md` > `## 30. Project Directory Structure` -> approved agents, services, and tests modules.
- `docs/plans/Master_Plan.md` > `## 31. Environment Setup` -> runtime and test dependencies.
- `docs/plans/Master_Plan.md` > `## 32. Single Root .env` -> backend model and limit settings.
- `docs/plans/Master_Plan.md` > `## 35. Implementation Checklist` > `### LangGraph State` / `### Extraction` / `### Search and Parsing` -> MVP completion requirements used by this phase.
- `docs/plans/Plan_2.md` > `## 1. Objective` -> extraction-only phase outcome.
- `docs/plans/Plan_2.md` > `## 3. Prerequisites from Prior Phases` -> required Phase 1 foundation.
- `docs/plans/Plan_2.md` > `## 4. Scope` and `## 5. Out of Scope` -> phase boundary.
- `docs/plans/Plan_2.md` > `## 6. Target Directory Structure` -> Phase 2 file locations.
- `docs/plans/Plan_2.md` > `## 7. Technical Specifications` -> state, schema, mapping, entrypoint, client, parsing, fallback, and limit contracts.
- `docs/plans/Plan_2.md` > `## 8. Implementation Steps` -> required implementation inventory.
- `docs/plans/Plan_2.md` > `## 9. Verification & Testing Plan` -> automated and manual checks.
- `docs/plans/Plan_2.md` > `## 10. Handoff Notes for Phase 3` -> output guarantees for the next phase.
- `README.md` > `## Directory Structure` -> current Phase 1 modules and `backend/tests/` location.
- `README.md` > `## Setup and Running Instructions` -> established backend verification workflow.

## Approved Architecture Summary

- `JobAgentState` is the shared LangGraph contract. Every node preserves `batch_id`, `role_profile_id`, and `input_source`.
- Runtime source and status validation imports the Phase 1 tuples in `backend/app/core/constants.py`; type-level `Literal` annotations must not create competing executable sets.
- Raw text is cleaned and truncated with Phase 1 settings. URL input is fetched with `httpx`, bounded by timeout and response size, and converted to readable text with `trafilatura`.
- URL content below 150 clean characters, or otherwise blocked, login-gated, JavaScript-only, or unreliable, returns `parse_status = "needs_manual_input"` and never calls the LLM.
- Usable content enters structured extraction through a mockable client boundary. Invalid output receives exactly one repair attempt.
- The graph distinguishes parsing from extraction: parser fallback leaves `extraction_status = None`; LLM/schema failure after successful parsing preserves `parse_status = "success"` and sets `extraction_status = "failed"`.
- Terminal outputs include a complete `extracted_job` dictionary compatible with `JobPostExtract`, nullable scoring placeholders, observability fields, and preserved required identifiers.
- Public async service entrypoints hide LangGraph internals from later phases.

## Global Implementation Rules

- Reuse `backend/app/core/config.py` for `OPENAI_MODEL`, input limits, retry count, timeout, and response-size limits.
- Reuse `backend/app/core/constants.py` for all runtime source and status validation.
- Keep tests under `backend/tests/`, matching the established repository layout.
- Keep LLM behavior replaceable with a fake client; automated tests must not require network access or a real API key.
- Use Pydantic structured output and return `JobPostExtract.model_dump()` dictionaries at successful graph terminals.
- Treat `parse_status` and `extraction_status` as independent status dimensions.
- Return all score fields as `None`; do not implement any score calculation in this phase.
- Do not log raw secrets, authorization headers, provider credentials, or complete unsafe provider responses.
- Do not add a custom HTML parser, browser renderer, persistence call, route handler, search call, Qdrant call, or frontend change.
- Do not modify established Phase 1 models or constants unless execution uncovers a demonstrable Plan 2 compatibility defect; report such a defect before expanding scope.

## Execution Agent Coding Style Requirements

- Write clean, idiomatic, readable Python.
- Use descriptive names for modules, functions, variables, settings, protocols, and tests.
- Keep functions and modules focused on one clear responsibility.
- Prefer simple, explicit control flow over clever abstractions.
- Follow FastAPI, Pydantic v2, async `httpx`, LangChain, and LangGraph conventions already approved by the plans.
- Use clear typing and typed protocol boundaries.
- Avoid `Any` outside the approved state payload boundary, broad exception handling, hidden global state, and hardcoded configuration values.
- Add comments only for non-obvious decisions, including the required production SSRF note.
- Keep backend-only secrets and configuration names out of frontend code.
- Do not add formatters, linters, frameworks, or architecture changes outside the approved plans.

## Batch Map

| Batch | Outcome | Depends On |
|---|---|---|
| Batch01 | Stable extraction contracts, mappings, prompts, and observability helpers | Phase 1 foundation |
| Batch02 | Bounded raw-text and URL preparation with parser-only fallback behavior | Batch01 |
| Batch03 | Mockable LLM extraction, LangGraph orchestration, and public service entrypoints | Batch01, Batch02 |
| Batch04 | Focused contract, parser, graph, and phase-boundary verification | Batch01, Batch02, Batch03 |

## Mandatory Batch01 - Extraction Contracts and Shared Utilities

### Goal

Create the typed state, structured extraction schema, shared validation/mapping helpers, prompts, and observability utilities that all later Phase 2 work uses.

### Why this batch exists

Content preparation and graph orchestration need one stable contract before behavior is implemented. Centralizing these definitions prevents divergent status values and incomplete fallback records.

### Inputs / Dependencies

- Completed Phase 1 package structure.
- `backend/app/core/config.py`.
- `backend/app/core/constants.py`.
- Existing runtime dependencies in `backend/requirements.txt`.

### Tasks

- [x] (01A): Define the extraction state and structured output schema
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking` > `### Required State Fields`
    - `docs/plans/Master_Plan.md` > `## 29. Pydantic Schema Sketch`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### JobAgentState` / `### JobPostExtract`
  - Source Requirements:
    - Define the complete `JobAgentState` contract, including identifiers, parsing, extraction, scoring placeholders, warning, and observability fields.
    - Define `JobPostExtract` with the approved defaults and controlled values.
    - Preserve `should_score_similarity` as part of the extraction handoff.
  - Details: Add the Phase 2 schema module without changing the existing persistence models.
  - Dependencies: Phase 1 shared constants and Pydantic dependency.
  - User Action: None.
  - Agent Work: Create `backend/app/agents/schemas.py`, define the typed state and Pydantic model, and keep executable validation tied to shared constants.
  - Specific Steps:
    1. Add every field listed in the Plan 2 state contract.
    2. Add every `JobPostExtract` field and approved default.
    3. Validate controlled Pydantic fields against the existing constants without duplicating runtime tuples.
    4. Ensure model dumps contain defaulted fields needed by Phase 3.
  - Output: Typed state and validated extraction model.
  - Acceptance: Valid structured jobs validate; invalid controlled values fail; defaulted fields are present in serialized output.
  - Validation: Run focused schema tests created in Batch04.
  - Blocked Condition: None.
  - Files: `backend/app/agents/schemas.py`.

- [x] (01B): Add source mapping, state-preservation, and fallback-shape helpers
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking` > `### Required Rule`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### Source Mapping` / `### LLM Fallback`
  - Source Requirements:
    - Map each supported input source to the identical approved source platform.
    - Reject unsupported input sources or emitted source platforms.
    - Preserve `batch_id`, `role_profile_id`, and `input_source` in every node update.
    - Produce complete unclear `extracted_job` dictionaries and `None` score placeholders.
  - Details: Provide small reusable helpers so success and fallback paths cannot drift.
  - Dependencies: (01A).
  - User Action: None.
  - Agent Work: Implement mapping, required-state preservation, score-placeholder, and unclear-job helper functions in the schema or extraction-support module.
  - Specific Steps:
    1. Validate inputs against `INPUT_SOURCES`.
    2. Validate outputs against `SOURCE_PLATFORMS`.
    3. Implement exact mappings for `tavily`, `manual_url`, `manual_text`, and `mock`.
    4. Add a helper that reads and returns all three required state keys.
    5. Add one canonical complete unclear-job builder parameterized by source URL, source platform, and extraction note.
  - Output: Reusable validated contract helpers.
  - Acceptance: Unsupported values fail safely, every helper-produced node update preserves required keys, and unclear outputs include all approved defaults.
  - Validation: Unit tests for every mapping, invalid values, required-key preservation, and fallback keys.
  - Blocked Condition: None.
  - Files: `backend/app/agents/schemas.py` or a narrowly scoped support module if needed.

- [x] (01C): Define extraction and repair prompt templates
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4. Architecture`
    - `docs/plans/Master_Plan.md` > `## 8. JD Status Rules`
    - `docs/plans/Master_Plan.md` > `## 18. LLM JSON Fallback`
    - `docs/plans/Plan_2.md` > `## 4. Scope`
  - Source Requirements:
    - Request only the approved structured job fields.
    - Apply the five JD classifications and scorable-status rule.
    - Repair invalid output without adding unsupported facts.
  - Details: Keep prompt text isolated from orchestration and suitable for both production and fake clients.
  - Dependencies: (01A).
  - User Action: None.
  - Agent Work: Create clear extraction and repair prompt templates with explicit no-hallucination and classification instructions.
  - Specific Steps:
    1. Define extraction instructions using the `JobPostExtract` field meanings.
    2. Include the exact JD classification criteria.
    3. State that only `full_jd` and `partial_jd` are scorable.
    4. Define repair instructions that receive invalid output and validation error context.
    5. Keep source URL and source platform as supplied context, not inferred content.
  - Output: Stable extraction and repair prompts.
  - Acceptance: Prompts cover all schema fields, all JD statuses, scoring eligibility, and safe repair behavior.
  - Validation: Import smoke test and prompt-content assertions where useful.
  - Blocked Condition: None.
  - Files: `backend/app/agents/prompts.py`.

- [x] (01D): Add token, cost, and timing normalization utilities
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 15. Cost & Performance Metrics Panel`
    - `docs/plans/Plan_2.md` > `## 4. Scope`
    - `docs/plans/Plan_2.md` > `## 8. Implementation Steps`
  - Source Requirements:
    - Return `input_tokens`, `output_tokens`, `estimated_cost_usd`, and `extraction_time_ms` as provider-derived values or explicit `None`.
    - Do not fabricate token counts or pricing.
  - Details: Normalize optional provider usage data and elapsed time without coupling graph code to one response object.
  - Dependencies: Phase 1 `OPENAI_MODEL` setting.
  - User Action: None.
  - Agent Work: Create a small cost/usage service that safely extracts available usage and calculates cost only when supported inputs and explicit pricing are available.
  - Specific Steps:
    1. Define a typed usage result shape.
    2. Normalize missing usage values to `None`.
    3. Calculate elapsed milliseconds with a monotonic clock around attempted extraction.
    4. Return `estimated_cost_usd = None` when reliable pricing or token data is unavailable.
    5. Avoid logging provider secrets or raw authorization data.
  - Output: Provider-neutral observability helpers.
  - Acceptance: All four observability fields can be populated or explicitly set to `None` without raising on missing metadata.
  - Validation: Focused unit tests with complete, partial, and absent usage metadata.
  - Blocked Condition: None.
  - Files: `backend/app/services/cost_service.py`.

### Files or Modules Likely Created or Updated

- `backend/app/agents/schemas.py`
- `backend/app/agents/prompts.py`
- `backend/app/services/cost_service.py`
- `backend/app/agents/__init__.py` or `backend/app/services/__init__.py` only if public exports are needed

### Required Outputs / Artifacts

- One shared state contract.
- One structured extraction model.
- Validated source mapping and stable fallback helpers.
- Extraction and repair prompts.
- Optional observability normalization utilities.

### Acceptance Criteria

- Schema defaults and controlled values match the plans.
- No independent executable source/status sets are introduced.
- Required identifiers and complete fallback fields are reusable across nodes.

### Required Tests or Validations

- Schema construction and rejection tests.
- Mapping and helper contract tests.
- Observability helper tests.
- Module import checks.

### Explicit Non-Goals

- LLM calls.
- URL fetching.
- LangGraph compilation.
- Database schema changes.
- Scoring logic.

## Mandatory Batch02 - Input Preparation and URL Fallback

### Goal

Prepare bounded clean content from raw text or a public URL and return parser-only fallback states when URL content is unusable.

### Why this batch exists

The LLM must receive deterministic, bounded content and must never be asked to infer a job from an empty, blocked, or unreliable page.

### Inputs / Dependencies

- Batch01 contracts and helpers.
- Phase 1 input-limit and timeout settings.
- Existing `httpx` and `trafilatura` dependencies.

### Tasks

- [x] (02A): Implement raw-text cleaning, truncation, and content hashing
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 28. Input Size and Retry Limits`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### Input Limits`
    - `docs/plans/Plan_2.md` > `## 8. Implementation Steps`
  - Source Requirements:
    - Enforce `MAX_RAW_TEXT_CHARS` and `MAX_CLEAN_TEXT_CHARS`.
    - Compute `raw_content_hash` from clean content when clean content exists.
    - Manual text must not perform URL fetches.
  - Details: Build deterministic text preparation primitives used by both manual text and URL paths.
  - Dependencies: (01A), (01B).
  - User Action: None.
  - Agent Work: Add raw-input bounds, whitespace/readability cleanup, low-signal truncation, clean-text bounds, and stable hashing.
  - Specific Steps:
    1. Bound raw input using the Phase 1 setting.
    2. Normalize text without deleting meaningful JD sections.
    3. Bound clean text using the Phase 1 setting.
    4. Hash the final clean content using a deterministic standard hash.
    5. Return `parse_status = "success"` only when usable clean text exists.
  - Output: Reusable clean/truncate/hash functions and manual-text preparation.
  - Acceptance: Manual text stays within configured bounds, produces a stable hash, and never invokes HTTP.
  - Validation: Unit tests for empty, normal, oversized, and repeat-hash inputs.
  - Blocked Condition: None.
  - Files: `backend/app/services/extraction_service.py`.

- [x] (02B): Implement bounded HTTP fetch and trafilatura extraction
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners`
    - `docs/plans/Master_Plan.md` > `## 27. URL Parsing Security Note`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### URL Parsing`
  - Source Requirements:
    - Accept only `http` and `https`.
    - Apply configured timeout and response-size limits.
    - Use `httpx` and `trafilatura` as the primary extraction path.
    - Include the required production SSRF mitigation note.
  - Details: Fetch public content safely within the MVP boundary and avoid unbounded response buffering.
  - Dependencies: (02A).
  - User Action: None.
  - Agent Work: Validate URL schemes, stream or otherwise enforce the response byte cap, handle redirects and HTTP failures safely, and run `trafilatura` on accepted content.
  - Specific Steps:
    1. Reject non-HTTP(S) schemes before network access.
    2. Use `REQUEST_TIMEOUT_SECONDS`.
    3. Stop and return a parser failure/fallback when `MAX_RESPONSE_SIZE_MB` is exceeded.
    4. Extract readable text with `trafilatura`.
    5. Apply the shared cleaning, truncation, and hashing functions.
    6. Add the exact production SSRF note from the plans near URL-fetch code.
  - Output: Bounded URL fetch and extraction path.
  - Acceptance: Valid mocked pages produce bounded clean text; invalid scheme, timeout, oversized, and failed HTTP cases do not crash.
  - Validation: `respx`-backed tests with no live network dependency.
  - Blocked Condition: None.
  - Files: `backend/app/services/extraction_service.py`, `backend/tests/test_url_cleaning.py`.

- [x] (02C): Implement low-content and unreliable-page fallback semantics
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners` > `### UI Warning Example`
    - `docs/plans/Master_Plan.md` > `## 8. JD Status Rules`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### Parse vs Extraction Status Semantics` / `### URL Parsing`
  - Source Requirements:
    - Treat fewer than 150 clean characters as unreliable.
    - Return the exact stable manual-input warning for low-content or unreliable pages.
    - Set `parse_status = "needs_manual_input"`, `jd_status = "unclear"`, `should_score_similarity = False`, all score fields to `None`, and `extraction_status = None`.
    - Do not call the LLM on this path.
  - Details: Make parser fallback a complete terminal state rather than an exception or partial dictionary.
  - Dependencies: (01B), (02B).
  - User Action: User must paste the JD text manually when the application surfaces this returned warning; no action is required to complete the implementation task.
  - Agent Work: Implement `is_unreliable_extraction`, detect low-content/blocked/login/JavaScript-only signals as supported by fetched content, and build the exact fallback state.
  - Specific Steps:
    1. Apply the 150-character threshold after cleaning.
    2. Use the canonical unclear-job and score-placeholder helpers.
    3. Preserve required identifiers and source URL.
    4. Set parser and extraction statuses independently.
    5. Return the exact multiline warning from Plan 2.
    6. Ensure orchestration treats this result as terminal before LLM extraction.
  - Output: Complete manual-input fallback state.
  - Acceptance: Unreliable URL content returns the exact contract and zero LLM calls.
  - Validation: Unit test exact status values, warning text, fallback keys, score placeholders, and fake-client call count.
  - Blocked Condition: None for implementation; runtime processing of a specific inaccessible URL may return `needs_manual_input` by design.
  - Files: `backend/app/services/extraction_service.py`, `backend/tests/test_url_cleaning.py`.

### Files or Modules Likely Created or Updated

- `backend/app/services/extraction_service.py`
- `backend/tests/test_url_cleaning.py`

### Required Outputs / Artifacts

- Shared raw-text preparation.
- Bounded URL-fetch and `trafilatura` extraction.
- Stable clean-content hash.
- Complete low-content/manual-input fallback.

### Acceptance Criteria

- All configured limits are honored.
- Parser failures remain distinct from extraction failures.
- Unreliable content never reaches the LLM.
- URL handling remains within the MVP security scope.

### Required Tests or Validations

- Raw-text cleaning and bounds.
- Invalid-scheme rejection.
- Mocked success, timeout, oversized response, HTTP failure, and low-content URL cases.
- Exact warning and no-LLM assertion.

### Explicit Non-Goals

- Enterprise SSRF mitigation.
- Playwright or browser rendering.
- Custom HTML parser logic.
- Authenticated scraping.
- Tavily search calls or API routes.

## Mandatory Batch03 - Structured Extraction Graph and Service API

### Goal

Run usable clean content through a mockable structured-output client and LangGraph workflow, retry invalid output exactly once, classify the JD, and expose stable async entrypoints.

### Why this batch exists

Later phases need extraction behavior without depending on graph internals or provider-specific response objects.

### Inputs / Dependencies

- Batch01 contracts, prompts, helpers, and observability utilities.
- Batch02 content-preparation behavior.
- Existing LangChain, LangGraph, and OpenAI dependencies.

### Tasks

- [x] (03A): Implement the mockable LLM extraction client boundary
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack`
    - `docs/plans/Master_Plan.md` > `## 18. LLM JSON Fallback`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### Mockable LLM Client Boundary`
  - Source Requirements:
    - Provide async `extract_job` and `repair_job` operations returning `JobPostExtract`.
    - Keep tests able to inject fake valid, repair-success, and repair-failure behavior.
    - Use structured output and capture available observability metadata.
  - Details: Isolate LangChain/OpenAI provider code behind the approved protocol.
  - Dependencies: (01A), (01C), (01D).
  - User Action: Add a valid `OPENAI_API_KEY` to the uncommitted root `.env` only for an optional live-provider smoke test.
  - Agent Work: Define the protocol and production implementation, use backend-only settings, and expose dependency injection to graph/service code.
  - Specific Steps:
    1. Define the exact protocol signatures from Plan 2.
    2. Configure structured output for `JobPostExtract`.
    3. Keep extraction and repair operations separate.
    4. Surface validation/provider failures to orchestration in a safe typed form.
    5. Normalize usage and timing fields without logging secrets.
    6. Avoid constructing a required live client during test module import.
  - Output: Production-capable, fake-replaceable extraction client.
  - Acceptance: A fake client can drive every graph path; production code reads model/key configuration only from backend settings.
  - Validation: Fake-client unit tests; optional live smoke only when the user supplies credentials.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for an explicitly requested live-provider validation when a valid API key is absent; mocked automated acceptance remains available.
  - Files: `backend/app/services/extraction_service.py` and, only if separation is clearer, one narrowly scoped client module.

- [x] (03B): Implement extraction, retry, classification, and unclear nodes
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4. Architecture`
    - `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking`
    - `docs/plans/Master_Plan.md` > `## 8. JD Status Rules`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### JD Status Rules` / `### Parse vs Extraction Status Semantics` / `### LLM Fallback`
  - Source Requirements:
    - Preserve all required identifiers in every node update.
    - Retry invalid LLM/schema output exactly once.
    - Mark retry success as `extraction_status = "retried"`.
    - Preserve parser success and return a complete unclear fallback after final extraction failure.
    - Set scoring eligibility true only for `full_jd` and `partial_jd`.
  - Details: Implement small nodes with explicit partial updates and no persistence side effects.
  - Dependencies: (01B), (03A).
  - User Action: None.
  - Agent Work: Create content-preparation integration, initial extraction, repair, classification, and `mark_unclear` nodes.
  - Specific Steps:
    1. Start each update with the required-state helper.
    2. Short-circuit parser terminal states before extraction.
    3. Serialize valid outputs with `model_dump()`.
    4. Route first validation failure to repair only when the configured retry cap permits the single approved retry.
    5. Classify/normalize JD status and derive `should_score_similarity`.
    6. Build the complete unclear fallback after retry failure or attempted provider/schema failure.
    7. Preserve `parse_status = "success"` for post-parse extraction failures.
    8. Populate observability fields or explicit `None`.
  - Output: Side-effect-free extraction graph nodes.
  - Acceptance: Success, retry success, retry failure, and parser fallback all return complete, distinguishable states.
  - Validation: Mocked node and graph tests covering every terminal path.
  - Blocked Condition: None.
  - Files: `backend/app/agents/nodes.py`.

- [x] (03C): Compile the extraction graph and expose public service entrypoints
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4. Architecture`
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### Public Extraction Entrypoints`
    - `docs/plans/Plan_2.md` > `## 10. Handoff Notes for Phase 3`
  - Source Requirements:
    - Expose `run_extraction_graph`, `extract_from_raw_text`, and `extract_from_url`.
    - Default direct URL parsing to `manual_url`; accept `tavily` only where specified.
    - Return a complete `JobAgentState` and hide LangGraph internals.
    - Perform no persistence, batch creation, scoring, Qdrant, or search work.
  - Details: Wire nodes in the approved preparation-to-classification order with explicit conditional edges.
  - Dependencies: (02C), (03B).
  - User Action: None.
  - Agent Work: Create and compile the graph, wire terminal parser fallback and retry branches, and add thin public service wrappers.
  - Specific Steps:
    1. Build the graph from preparation through classification.
    2. Route parser fallback directly to graph end.
    3. Route invalid initial extraction through one repair attempt.
    4. Route exhausted/failed extraction through `mark_unclear`.
    5. Make the LLM client injectable for tests.
    6. Build initial states for raw text and URL entrypoints with required identifiers.
    7. Validate URL entrypoint input source as only `manual_url` or `tavily`.
    8. Return the final state without database or external-index side effects.
  - Output: Compiled extraction graph and stable public async service API.
  - Acceptance: All three entrypoints return complete states, preserve required identifiers, and follow the approved routing semantics.
  - Validation: Import smoke test and mocked end-to-end graph tests.
  - Blocked Condition: None.
  - Files: `backend/app/agents/graph.py`, `backend/app/services/extraction_service.py`, package `__init__.py` files only if exports are needed.

### Files or Modules Likely Created or Updated

- `backend/app/agents/nodes.py`
- `backend/app/agents/graph.py`
- `backend/app/services/extraction_service.py`
- Package `__init__.py` files only for intentional public exports

### Required Outputs / Artifacts

- Mockable client protocol and production implementation.
- LangGraph nodes and compiled extraction graph.
- Three public async extraction entrypoints.
- Complete success and fallback state outputs.

### Acceptance Criteria

- Retry count is exactly one.
- Parser and extraction statuses remain independently interpretable.
- Every terminal path preserves required identifiers and all score placeholders.
- No persistence or scoring side effects occur.

### Required Tests or Validations

- Valid first-attempt extraction.
- Repair success.
- Repair failure.
- Attempted provider/schema failure.
- Parser short-circuit.
- Public entrypoint import and behavior.

### Explicit Non-Goals

- SQLite writes or batch creation.
- Deduplication or embedding construction.
- Similarity or final score calculation.
- Qdrant operations.
- Tavily search implementation.
- FastAPI route handlers.

## Mandatory Batch04 - Contract and Phase Verification

### Goal

Prove the complete Plan 2 boundary with deterministic automated tests and smoke checks.

### Why this batch exists

Phase 3 depends on exact state and fallback contracts. Verification must catch status drift, missing keys, accidental side effects, and retry/fallback regressions before handoff.

### Inputs / Dependencies

- Completed Batch01 through Batch03 implementation.
- Existing `pytest`, `pytest-asyncio`, and `respx` development dependencies.
- Established `backend/tests/` layout.

### Tasks

- [x] (04A): Verify schema, constants, mapping, and fallback contracts
  - Source of Truth:
    - `docs/plans/Plan_2.md` > `## 7. Technical Specifications` > `### JobAgentState` / `### JobPostExtract` / `### Source Mapping`
    - `docs/plans/Plan_2.md` > `## 9. Verification & Testing Plan`
  - Source Requirements:
    - Validate approved schema values and default fields.
    - Prove runtime status/source validation stays synchronized with Phase 1 constants.
    - Prove fallback dictionaries are directly ingestible without missing-key defaults.
  - Details: Add contract-focused tests independent of network and provider APIs.
  - Dependencies: Batch01.
  - User Action: None.
  - Agent Work: Test every controlled value, invalid values, source mappings, required-key helper, score placeholders, and complete fallback shape.
  - Specific Steps:
    1. Test valid `JobPostExtract` serialization.
    2. Test invalid controlled fields fail.
    3. Parametrize all source mappings and shared status constants.
    4. Assert unknown sources are rejected.
    5. Assert every fallback default field and score placeholder.
  - Output: Extraction schema and constants contract test suite.
  - Acceptance: Tests detect divergent source/status sets or incomplete fallback output.
  - Validation: `pytest tests/test_extraction_schema.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_extraction_schema.py`.

- [x] (04B): Verify raw-text and URL preparation behavior
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners`
    - `docs/plans/Master_Plan.md` > `## 27. URL Parsing Security Note`
    - `docs/plans/Master_Plan.md` > `## 28. Input Size and Retry Limits`
    - `docs/plans/Plan_2.md` > `## 9. Verification & Testing Plan`
  - Source Requirements:
    - Verify manual text, HTTP/trafilatura extraction, configured bounds, invalid schemes, unreliable content, and stable warning behavior.
    - Prove low-content URL handling never calls the LLM.
  - Details: Use `respx` and deterministic fixtures; do not access the internet.
  - Dependencies: Batch02, (03A) fake client.
  - User Action: None.
  - Agent Work: Add focused tests for successful and failing parser paths.
  - Specific Steps:
    1. Test manual text without HTTP calls.
    2. Test successful mocked URL fetch and extraction.
    3. Test invalid scheme, timeout, oversized response, and HTTP failure.
    4. Test fewer-than-150-character content.
    5. Assert exact warning text, complete fallback, `extraction_status is None`, and zero fake-client calls.
    6. Assert stable clean-content hashing and truncation bounds.
  - Output: URL and raw-input behavior test suite.
  - Acceptance: All parser paths are bounded, deterministic, and semantically distinct from LLM failures.
  - Validation: `pytest tests/test_url_cleaning.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_url_cleaning.py`.

- [x] (04C): Verify graph success, retry, failure, and state preservation
  - Source of Truth:
    - `docs/plans/Master_Plan.md` > `## 4. Architecture`
    - `docs/plans/Master_Plan.md` > `## 4.1. LangGraph State Tracking`
    - `docs/plans/Master_Plan.md` > `## 18. LLM JSON Fallback`
    - `docs/plans/Plan_2.md` > `## 9. Verification & Testing Plan`
  - Source Requirements:
    - Prove valid extraction, exactly-one retry, repair success, repair failure, and non-crashing fallback.
    - Preserve identifiers and parser status on every path.
    - Populate observability fields or explicit `None`.
  - Details: Drive the compiled graph exclusively with configurable fake clients.
  - Dependencies: Batch03.
  - User Action: None.
  - Agent Work: Add end-to-end graph tests for every required route and service entrypoint.
  - Specific Steps:
    1. Test valid first-attempt extraction.
    2. Test invalid first output followed by repair success and assert one repair call.
    3. Test invalid output after repair and assert no further retry.
    4. Test attempted provider/schema failure after parser success.
    5. Assert required identifiers on success, retry success, retry failure, and parser fallback.
    6. Assert JD classification and scoring eligibility.
    7. Assert all failed/non-scorable score fields are `None`.
    8. Assert observability keys always exist.
  - Output: Extraction graph behavior test suite.
  - Acceptance: The graph cannot lose required context, exceed one retry, or conflate parser and extraction failures.
  - Validation: `pytest tests/test_extraction_graph.py`.
  - Blocked Condition: None.
  - Files: `backend/tests/test_extraction_graph.py`.

- [x] (04D): Run full Phase 2 verification and confirm the handoff boundary
  - Source of Truth:
    - `docs/plans/Plan_2.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Plan_2.md` > `## 10. Handoff Notes for Phase 3`
    - `README.md` > `## Setup and Running Instructions` > `### 4. Running Backend Verification`
  - Source Requirements:
    - Run focused and full backend tests.
    - Confirm extraction can return structured and unclear results without crashing.
    - Confirm this phase inserts no SQLite rows and creates no Qdrant collection.
  - Details: Perform the final evidence-based verification and document any environment limitation.
  - Dependencies: (04A), (04B), (04C).
  - User Action: None for mocked verification; a real provider key is optional and not required for Phase 2 acceptance.
  - Agent Work: Run all required commands, inspect failures, confirm no out-of-scope side effects, and update the task progress only for satisfied items.
  - Specific Steps:
    1. Run each focused Phase 2 test file.
    2. Run the full backend test suite.
    3. Run an import smoke check for all public entrypoints.
    4. Run mocked raw-JD success and retry-failure service calls.
    5. Confirm no Phase 2 code imports or calls persistence, Qdrant, Tavily search, or route modules.
    6. Record commands and results in the execution report.
  - Output: Verification evidence and Phase 3-ready extraction contract.
  - Acceptance: Focused and full test suites pass, smoke checks pass, and no out-of-scope side effects are present.
  - Validation: From `backend`: `pytest tests/test_extraction_schema.py`, `pytest tests/test_extraction_graph.py`, `pytest tests/test_url_cleaning.py`, then `pytest`.
  - Blocked Condition: None unless the established local Python environment cannot install or run the already-approved dependencies; report the exact safe error if so.
  - Files: Test files and execution report/progress artifact only; no new runtime scope.

### Files or Modules Likely Created or Updated

- `backend/tests/test_extraction_schema.py`
- `backend/tests/test_extraction_graph.py`
- `backend/tests/test_url_cleaning.py`
- Task progress and execution report artifacts used by the execution workflow

### Required Outputs / Artifacts

- Deterministic schema and constants tests.
- Deterministic parser tests.
- Deterministic graph and retry tests.
- Focused and full-suite verification evidence.
- Explicit Phase 3 handoff confirmation.

### Acceptance Criteria

- Every Plan 2 terminal path has automated coverage.
- Tests use mocks/fakes and do not require live network or provider credentials.
- Full backend regression suite passes.
- No Phase 3 or Phase 4 behavior is implemented.

### Required Tests or Validations

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_extraction_schema.py
pytest tests/test_extraction_graph.py
pytest tests/test_url_cleaning.py
pytest
```

### Explicit Non-Goals

- Live-provider testing as a mandatory gate.
- Performance/load testing.
- Database persistence integration.
- Qdrant integration.
- API endpoint or UI testing.

## Optional Future Tracks

No optional implementation track belongs to Plan 2.

The following work is explicitly outside the mandatory Phase 2 batch chain and must remain in later approved phases:

- Scoring, embedding construction, persistence, deduplication, and Qdrant synchronization.
- Tavily search orchestration and FastAPI route handlers.
- Demo seeding and mock-data loading.
- React UI and warning presentation.
- Enterprise SSRF mitigation or browser-rendered parsing.

## Dependency Chain

- Phase 1 foundation -> Batch01
- Batch01 -> Batch02
- Batch01 + Batch02 -> Batch03
- Batch01 + Batch02 + Batch03 -> Batch04

Future-phase tracks are outside this mandatory chain.

## Global Verification Checklist

- [x] `JobAgentState` and `JobPostExtract` match the approved contracts.
- [x] Runtime sources and statuses use Phase 1 shared constants.
- [x] Every node preserves `batch_id`, `role_profile_id`, and `input_source`.
- [x] Raw and clean input limits use Phase 1 settings.
- [x] URL parsing allows only HTTP(S), enforces timeout/size limits, and uses `trafilatura`.
- [x] Low-content URL results use the exact warning, skip the LLM, and leave `extraction_status = None`.
- [x] Invalid LLM/schema output retries exactly once.
- [x] LLM/schema failure after parsing preserves `parse_status = "success"` and sets `extraction_status = "failed"`.
- [x] Every fallback job includes all `JobPostExtract` default fields and all score fields are `None`.
- [x] Observability fields are present as provider values or explicit `None`.
- [x] Public entrypoints are async, importable, and free of persistence/scoring side effects.
- [x] Focused Phase 2 tests and the full backend test suite pass.
- [x] No SQLite rows are inserted and no Qdrant collections are created by Phase 2.
- [x] Implementation code is clean, idiomatic, typed where appropriate, and easy to understand.
- [x] No scoring, persistence, deduplication, Qdrant, Tavily search, route, seed, or frontend scope was added.

## Progress Tracker

### Batches

- [x] Batch01 - Extraction Contracts and Shared Utilities
- [x] Batch02 - Input Preparation and URL Fallback
- [x] Batch03 - Structured Extraction Graph and Service API
- [x] Batch04 - Contract and Phase Verification

### Task IDs

#### Batch01

- [x] (01A): Define the extraction state and structured output schema
- [x] (01B): Add source mapping, state-preservation, and fallback-shape helpers
- [x] (01C): Define extraction and repair prompt templates
- [x] (01D): Add token, cost, and timing normalization utilities

#### Batch02

- [x] (02A): Implement raw-text cleaning, truncation, and content hashing
- [x] (02B): Implement bounded HTTP fetch and trafilatura extraction
- [x] (02C): Implement low-content and unreliable-page fallback semantics

#### Batch03

- [x] (03A): Implement the mockable LLM extraction client boundary
- [x] (03B): Implement extraction, retry, classification, and unclear nodes
- [x] (03C): Compile the extraction graph and expose public service entrypoints

#### Batch04

- [x] (04A): Verify schema, constants, mapping, and fallback contracts
- [x] (04B): Verify raw-text and URL preparation behavior
- [x] (04C): Verify graph success, retry, failure, and state preservation
- [x] (04D): Run full Phase 2 verification and confirm the handoff boundary

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
