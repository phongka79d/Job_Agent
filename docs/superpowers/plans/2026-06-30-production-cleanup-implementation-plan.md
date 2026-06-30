# Production Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove confirmed runtime demo/mock/fake code, obsolete execution artifacts, unused assets, unused dependencies, and debug comments while preserving the existing production architecture and business flow.

**Architecture:** Keep the current `React -> FastAPI -> LangGraph/services -> SQLite + Qdrant` shape. Delete the runtime demo vertical slice, keep deterministic test doubles inside test paths, regenerate the backend-owned API contract before frontend cleanup, and verify the backend and frontend as runnable applications.

**Tech Stack:** FastAPI, SQLAlchemy async SQLite, Qdrant, LangGraph, Pydantic, React, TypeScript, Vite, Vitest, Pytest, Docker Compose.

---

## File Structure

- Delete: `mock_data/demo_jobs.json`, `mock_data/messy_social_posts.json`
- Delete: `backend/scripts/seed_demo.py`
- Delete: `backend/app/services/demo_loader.py`
- Delete: `backend/tests/test_seed_demo.py`
- Delete: `docs/tasks/`, `docs/reports/`, `docs/review/`, `docs/plans/`
- Delete: `frontend/job-agent-ui/README.md`
- Delete: unused frontend starter assets after reference checks: `frontend/job-agent-ui/src/App.css`, `frontend/job-agent-ui/src/assets/vite.svg`, `frontend/job-agent-ui/src/assets/react.svg`, `frontend/job-agent-ui/src/assets/hero.png`, `frontend/job-agent-ui/public/icons.svg`
- Create: `backend/tests/fakes.py` for test-only deterministic LLM client doubles
- Modify: `backend/app/api/routes_jobs.py` to remove `POST /api/jobs/mock-load` and demo imports
- Modify: `backend/app/api/schemas.py` to remove `MockLoadRequest`
- Modify: `backend/app/agents/schemas.py` to remove runtime `mock` values and replace production assertions with explicit validation
- Modify: `backend/app/agents/nodes.py` to remove the mock preparation branch
- Modify: `backend/app/core/constants.py` to remove runtime `mock` constants
- Modify: `backend/app/db/models.py` to remove demo-specific column documentation text
- Modify: `backend/app/services/llm_client.py` to remove `FakeJobExtractionClient`
- Modify: `backend/app/services/__init__.py` to remove the fake client export only
- Modify: `backend/app/services/extraction_service.py` and `backend/app/api/routes_jobs.py` to remove obsolete development comments
- Modify: `backend/scripts/export_api_contract.py` to remove mock-load contract declarations and replace `print` with logging
- Modify: `shared/api-contract.json` by regenerating from backend owners
- Modify: backend tests that reference runtime mock/demo values to use retained runtime values or `backend/tests/fakes.py`
- Modify: `frontend/job-agent-ui/src/api/client.ts`, `frontend/job-agent-ui/src/types/api.ts`, `frontend/job-agent-ui/src/components/IngestionPanel.tsx`, and frontend tests to remove demo UI/client/type usage
- Modify: `backend/requirements.txt` to remove unused production packages confirmed by import scan
- Modify: `README.md` as current production setup and operations documentation

---

## Task 1: Preflight and Safe Local Demo Data Cleanup

**Files:**
- Read: `backend/app/services/demo_loader.py`
- Read: `backend/app/db/session.py`
- Read: `backend/app/services/qdrant_service.py`
- No source edits in this task

- [ ] **Step 1: Confirm a clean starting point**

Run:
```powershell
git status --short
git log -1 --oneline
```

Expected: no unexpected uncommitted files except the plan file if it has not been committed yet.

- [ ] **Step 2: Verify Qdrant is available without deleting data**

Run:
```powershell
docker compose up -d qdrant
```

Expected: Qdrant container is running. Do not remove volumes and do not recreate the collection.

- [ ] **Step 3: Run the scoped demo reset while the reset helper still exists**

Run from `backend/`:
```powershell
@'
import asyncio
from sqlalchemy import func, or_, select
from qdrant_client import models as qmodels

from app.db.models import Application, JobPost, RoleProfile
from app.db.session import async_session_maker, init_db
from app.services.demo_loader import DEMO_ROLE_TARGET_ROLE, reset_mock_demo_data
from app.services.qdrant_service import QdrantService

async def count_non_mock_jobs(session):
    return (await session.execute(
        select(func.count())
        .select_from(JobPost)
        .where(or_(JobPost.source_platform.is_(None), JobPost.source_platform != "mock"))
    )).scalar_one()

async def count_mock_applications(session):
    return (await session.execute(
        select(func.count())
        .select_from(Application)
        .join(JobPost, Application.job_post_id == JobPost.id)
        .where(JobPost.source_platform == "mock")
    )).scalar_one()

async def count_demo_profiles(session):
    return (await session.execute(
        select(func.count())
        .select_from(RoleProfile)
        .where(RoleProfile.target_role == DEMO_ROLE_TARGET_ROLE)
    )).scalar_one()

async def count_qdrant_mock_points(qdrant_service):
    points, _ = await qdrant_service.client.scroll(
        collection_name=qdrant_service.collection_name,
        scroll_filter=qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="source_platform",
                    match=qmodels.MatchValue(value="mock"),
                )
            ]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    return len(points)

async def main():
    await init_db()
    qdrant_service = QdrantService()
    await qdrant_service.ensure_collection()

    async with async_session_maker() as session:
        mock_job_ids = list((await session.execute(
            select(JobPost.id).where(JobPost.source_platform == "mock")
        )).scalars())
        non_mock_before = await count_non_mock_jobs(session)
        mock_applications_before = await count_mock_applications(session)
        demo_profiles_before = await count_demo_profiles(session)
        qdrant_mock_before = await count_qdrant_mock_points(qdrant_service)

        print(
            "before "
            f"mock_jobs={len(mock_job_ids)} "
            f"mock_applications={mock_applications_before} "
            f"demo_profiles={demo_profiles_before} "
            f"qdrant_mock_points_visible={qdrant_mock_before} "
            f"non_mock_jobs={non_mock_before}"
        )

        result = await reset_mock_demo_data(session, qdrant_service=qdrant_service)

        remaining_mock_jobs = (await session.execute(
            select(func.count()).select_from(JobPost).where(JobPost.source_platform == "mock")
        )).scalar_one()
        non_mock_after = await count_non_mock_jobs(session)
        remaining_mock_applications = await count_mock_applications(session)
        remaining_qdrant_mock_points = await count_qdrant_mock_points(qdrant_service)

        print(
            "after "
            f"deleted_applications={result.deleted_applications} "
            f"deleted_job_posts={result.deleted_job_posts} "
            f"deleted_qdrant_vectors={result.deleted_qdrant_vectors} "
            f"deleted_role_profiles={result.deleted_role_profiles} "
            f"remaining_mock_jobs={remaining_mock_jobs} "
            f"remaining_mock_applications={remaining_mock_applications} "
            f"remaining_qdrant_mock_points_visible={remaining_qdrant_mock_points} "
            f"non_mock_jobs={non_mock_after}"
        )

        if remaining_mock_jobs != 0:
            raise SystemExit("mock-owned SQLite rows remain after scoped reset")
        if remaining_mock_applications != 0:
            raise SystemExit("mock-owned application rows remain after scoped reset")
        if non_mock_after != non_mock_before:
            raise SystemExit("non-mock SQLite row count changed during scoped reset")
        if remaining_qdrant_mock_points != 0:
            raise SystemExit("mock-owned Qdrant points remain visible after scoped reset")

asyncio.run(main())
'@ | .\.venv\Scripts\python.exe -
```

Expected: command exits `0`. If Qdrant is unavailable, stop source deletion and report that local demo data cleanup is blocked. If only `remaining_qdrant_mock_points_visible` remains nonzero, stop and report the exact evidence rather than broad-deleting Qdrant data.

---

## Task 2: Remove Backend Runtime Demo Surface

**Files:**
- Delete: `mock_data/demo_jobs.json`
- Delete: `mock_data/messy_social_posts.json`
- Delete: `backend/scripts/seed_demo.py`
- Delete: `backend/app/services/demo_loader.py`
- Delete: `backend/tests/test_seed_demo.py`
- Modify: `backend/app/api/routes_jobs.py`
- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/core/constants.py`
- Modify: `backend/app/agents/schemas.py`
- Modify: `backend/app/agents/nodes.py`
- Modify: `backend/app/db/models.py`
- Modify: `backend/scripts/export_api_contract.py`
- Modify: `backend/tests/test_api_contract_export.py`
- Modify: `backend/tests/test_constants_contract.py`
- Modify: `backend/tests/test_extraction_schema.py`
- Modify: `backend/tests/test_nodes.py`
- Modify: `backend/tests/test_routes_batches.py`

- [ ] **Step 1: Prove the runtime demo symbols are only in the deletion set or tests**

Run:
```powershell
rg -n "mock-load|MockLoadRequest|load_mock_fixture_states|reset_mock_demo_data|seed_demo|demo_loader|source_platform.*mock|input_source.*mock" backend mock_data shared frontend -S
```

Expected: references match the files listed in this task and the frontend files handled in Task 5.

- [ ] **Step 2: Remove the mock-load route and demo imports**

Edit `backend/app/api/routes_jobs.py`:
```python
from app.api.schemas import (
    IngestionResponse,
    JobListResponse,
    JobResponse,
    ParseJobTextRequest,
    ParseJobUrlRequest,
    SearchJobsRequest,
    StatusMutationResponse,
    StatusUpdateRequest,
)
```

Remove these declarations and imports:
```python
from pathlib import Path
from app.services.demo_loader import load_mock_fixture_states, reset_mock_demo_data

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MOCK_FIXTURE_PATHS = (
    REPOSITORY_ROOT / "mock_data" / "demo_jobs.json",
    REPOSITORY_ROOT / "mock_data" / "messy_social_posts.json",
)

@router.post("/mock-load", response_model=IngestionResponse)
async def mock_load_jobs(...):
    ...
```

Remove the SSRF development note comments above `extract_from_url(...)`; keep the existing scheme validation and error handling unchanged.

- [ ] **Step 3: Remove the mock request schema**

Edit `backend/app/api/schemas.py` and delete:
```python
class MockLoadRequest(ApiSchema):
    role_profile_id: UUID
    reset_existing_demo: bool = False
```

- [ ] **Step 4: Remove runtime `mock` from source contracts and explicit assertions**

Edit `backend/app/core/constants.py`:
```python
SOURCE_PLATFORMS = (
    "tavily",
    "manual_url",
    "manual_text",
    "job_board",
)

INPUT_SOURCES = (
    "tavily",
    "manual_url",
    "manual_text",
)
```

Edit `backend/app/agents/schemas.py`:
```python
_SOURCE_PLATFORM_BY_INPUT_SOURCE = {
    "tavily": "tavily",
    "manual_url": "manual_url",
    "manual_text": "manual_text",
}


def _require_valid_value(
    value: str | None,
    allowed_values: tuple[str, ...],
    field_name: str,
) -> str:
    validated = _validate_constant_value(value, allowed_values, field_name)
    if validated is None:
        raise ValueError(f"{field_name} must be one of {allowed_values}")
    return validated
```

Use `_require_valid_value(...)` inside `validate_input_source`, `validate_source_platform_value`, `validate_parse_status`, and `validate_jd_status`. Change `JobAgentState.input_source` to:
```python
input_source: Literal["tavily", "manual_url", "manual_text"]
```

- [ ] **Step 5: Remove the mock graph node branch**

Edit `backend/app/agents/nodes.py`:
```python
from app.services.extraction_service import (
    prepare_manual_text,
    prepare_url_content,
)
```

Delete the `elif input_source == "mock":` branch in `prepare_content`. Keep the final unsupported-source failure branch.

- [ ] **Step 6: Remove demo-specific ORM documentation**

Edit `backend/app/db/models.py`:
```python
source_platform: Mapped[str | None] = mapped_column(Text, nullable=True, doc="tavily/manual_url/manual_text/job_board")
```

Replace the `Application` delete behavior sentence with:
```python
When a job post is deleted, SQLite will automatically delete any matching
application tracking records, ensuring database consistency and safety.
```

- [ ] **Step 7: Remove mock-load from contract export**

Edit `backend/scripts/export_api_contract.py`:
```python
import json
import logging
import sys
```

Remove `MockLoadRequest` from imports, `ENDPOINTS`, and `SCHEMA_MODELS`. Add:
```python
logger = logging.getLogger(__name__)
```

Replace `main()` with:
```python
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output_path = write_api_contract()
    logger.info("Wrote %s", output_path.relative_to(REPOSITORY_ROOT))
```

- [ ] **Step 8: Delete backend demo files and datasets**

Run:
```powershell
git rm backend/scripts/seed_demo.py backend/app/services/demo_loader.py backend/tests/test_seed_demo.py mock_data/demo_jobs.json mock_data/messy_social_posts.json
```

Expected: files are staged for deletion. If `mock_data/` becomes empty, it should disappear from the worktree.

- [ ] **Step 9: Update backend tests for removed runtime values**

Edit tests:
- `backend/tests/test_api_contract_export.py`: remove `loadMockJobs` endpoint assertion and remove `MockLoadRequest` from expected schemas.
- `backend/tests/test_constants_contract.py`: remove `"mock"` from expected `SOURCE_PLATFORMS` and `INPUT_SOURCES`.
- `backend/tests/test_extraction_schema.py`: remove the `("mock", "mock")` mapping case and change `preserve_required_state` examples to `manual_text`.
- `backend/tests/test_nodes.py`: delete `test_prepare_content_mock`.
- `backend/tests/test_routes_batches.py`: replace test fixture `source_platform="mock"` with `source_platform="manual_text"` unless the test is explicitly checking another platform.

- [ ] **Step 10: Run focused backend tests for the demo removal**

Run from `backend/`:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_contract_export.py tests/test_constants_contract.py tests/test_extraction_schema.py tests/test_nodes.py tests/test_routes_batches.py
```

Expected: all selected tests pass or fail only because `FakeJobExtractionClient` still needs Task 3.

---

## Task 3: Move LLM Test Double Out of Production Code

**Files:**
- Create: `backend/tests/fakes.py`
- Modify: `backend/app/services/llm_client.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/tests/test_llm_client.py`
- Modify: `backend/tests/test_nodes.py`
- Modify: `backend/tests/test_extraction_graph.py`

- [ ] **Step 1: Search every fake client caller**

Run:
```powershell
rg -n "FakeJobExtractionClient|add_extract_response|add_repair_response|extract_calls|repair_calls" backend -S
```

Expected: only `backend/app/services/llm_client.py`, `backend/app/services/__init__.py`, and tests reference the production fake before edits.

- [ ] **Step 2: Add a test-only scripted LLM client**

Create `backend/tests/fakes.py`:
```python
"""Test-only doubles for external service boundaries."""

from __future__ import annotations

from typing import Any

from app.agents.schemas import JobPostExtract
from app.services.llm_client import JobExtractionClientProtocol


class ScriptedJobExtractionClient(JobExtractionClientProtocol):
    """Deterministic LLM client double confined to backend tests."""

    def __init__(self) -> None:
        self.extract_responses: list[Any] = []
        self.repair_responses: list[Any] = []
        self.extract_calls: list[dict[str, Any]] = []
        self.repair_calls: list[dict[str, Any]] = []
        self.default_extract_response: Any | None = None
        self.default_repair_response: Any | None = None

    def add_extract_response(self, response: Any) -> None:
        self.extract_responses.append(response)

    def add_repair_response(self, response: Any) -> None:
        self.repair_responses.append(response)

    async def extract_job(
        self,
        *,
        clean_text: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        self.extract_calls.append({
            "clean_text": clean_text,
            "source_url": source_url,
            "source_platform": source_platform,
        })
        response = self.extract_responses.pop(0) if self.extract_responses else self.default_extract_response
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        return _job_post_extract(source_url=source_url, source_platform=source_platform)

    async def repair_job(
        self,
        *,
        clean_text: str,
        invalid_output: str,
        validation_error: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        self.repair_calls.append({
            "clean_text": clean_text,
            "invalid_output": invalid_output,
            "validation_error": validation_error,
            "source_url": source_url,
            "source_platform": source_platform,
        })
        response = self.repair_responses.pop(0) if self.repair_responses else self.default_repair_response
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        return _job_post_extract(
            source_url=source_url,
            source_platform=source_platform,
            title="Repaired Test Engineer",
            input_tokens=120,
            output_tokens=60,
            estimated_cost_usd=0.00015,
            extraction_time_ms=15,
            extraction_notes="Repaired deterministic response",
        )


def _job_post_extract(
    *,
    source_url: str | None,
    source_platform: str,
    title: str = "Test Engineer",
    input_tokens: int = 100,
    output_tokens: int = 50,
    estimated_cost_usd: float = 0.0001,
    extraction_time_ms: int = 10,
    extraction_notes: str = "Deterministic response",
) -> JobPostExtract:
    job = JobPostExtract(
        title=title,
        company="Example Company",
        location="Remote",
        work_mode="remote",
        level="mid",
        employment_type="full-time",
        salary="100000-120000",
        responsibilities="Build production services.",
        requirements="Python and testing experience.",
        skills=["Python", "Testing"],
        source_url=source_url,
        source_platform=source_platform,
        jd_status="full_jd",
        should_score_similarity=True,
        extraction_notes=extraction_notes,
    )
    job._input_tokens = input_tokens
    job._output_tokens = output_tokens
    job._estimated_cost_usd = estimated_cost_usd
    job._extraction_time_ms = extraction_time_ms
    return job
```

- [ ] **Step 3: Remove production fake implementation**

Edit `backend/app/services/llm_client.py`:
- Delete `class FakeJobExtractionClient`.
- Remove `# Return a valid default ...` comments with it.
- Keep `JobExtractionClientProtocol`, `OpenAIJobExtractionClient`, `LLMProviderError`, and `LLMValidationError`.

Edit `backend/app/services/__init__.py`:
```python
from app.services.llm_client import (
    JobExtractionClientProtocol,
    LLMExtractionError,
    LLMProviderError,
    LLMValidationError,
    OpenAIJobExtractionClient,
)
```

Remove `"FakeJobExtractionClient"` from `__all__`.

- [ ] **Step 4: Update tests to use the test-only double**

Edit `backend/tests/test_nodes.py` and `backend/tests/test_extraction_graph.py`:
```python
from tests.fakes import ScriptedJobExtractionClient
```

Replace `FakeJobExtractionClient()` with `ScriptedJobExtractionClient()`. Replace expectations for `"Fake Software Engineer"` with `"Test Engineer"`.

Edit `backend/tests/test_extraction_graph.py` imports to pull production functions directly:
```python
from app.services.extraction_service import (
    extract_from_raw_text,
    extract_from_url,
    run_extraction_graph,
)
from app.services.llm_client import LLMProviderError, LLMValidationError
from tests.fakes import ScriptedJobExtractionClient
```

Edit `backend/tests/test_llm_client.py`:
- Remove the two tests that validate production fake behavior.
- Keep production `OpenAIJobExtractionClient` tests.
- Import `JobPostExtract` from `app.agents.schemas`.

- [ ] **Step 5: Run focused LLM and graph tests**

Run from `backend/`:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_llm_client.py tests/test_nodes.py tests/test_extraction_graph.py
```

Expected: all selected tests pass.

---

## Task 4: Regenerate Backend API Contract

**Files:**
- Modify: `shared/api-contract.json`
- Verify: `backend/scripts/export_api_contract.py`

- [ ] **Step 1: Export the contract after backend route/schema removal**

Run from `backend/`:
```powershell
.\.venv\Scripts\python.exe scripts/export_api_contract.py
```

Expected: `shared/api-contract.json` is rewritten and the script logs `Wrote shared\api-contract.json`.

- [ ] **Step 2: Block frontend cleanup if stale mock contract entries remain**

Run from repository root:
```powershell
rg -n "mock-load|MockLoadRequest|loadMockJobs|\"mock\"" shared/api-contract.json
```

Expected: no output. If there is output, fix backend owners and rerun Step 1 before touching frontend demo usage.

- [ ] **Step 3: Run contract export tests**

Run from `backend/`:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_contract_export.py
```

Expected: pass.

---

## Task 5: Remove Frontend Demo Client, UI, Types, and Tests

**Files:**
- Modify: `frontend/job-agent-ui/src/api/client.ts`
- Modify: `frontend/job-agent-ui/src/types/api.ts`
- Modify: `frontend/job-agent-ui/src/components/IngestionPanel.tsx`
- Modify: `frontend/job-agent-ui/src/test/IngestionPanel.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/apiClient.test.ts`
- Modify: `frontend/job-agent-ui/src/test/apiContract.test.ts`
- Modify: `frontend/job-agent-ui/src/test/activeBatch.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/ReviewPage.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/DashboardPage.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/JobCard.test.tsx`

- [ ] **Step 1: Remove the demo API client function**

Edit `frontend/job-agent-ui/src/api/client.ts`:
- Remove `MockLoadRequest` from the type import.
- Delete `loadMockJobs(...)`.
- Keep `searchJobs`, `parseJobUrl`, and `parseJobText`.

- [ ] **Step 2: Remove the demo type and runtime enum value**

Edit `frontend/job-agent-ui/src/types/api.ts`:
```ts
export type SourcePlatform = "tavily" | "manual_url" | "manual_text" | "job_board";
```

Delete:
```ts
export interface MockLoadRequest {
  role_profile_id: string;
  reset_existing_demo?: boolean;
}
```

Remove `"mock"` from `SOURCE_PLATFORMS`.

- [ ] **Step 3: Remove the Demo tab and reset UI**

Edit `frontend/job-agent-ui/src/components/IngestionPanel.tsx`:
```ts
import { Search, Link, FileText, Loader2, AlertCircle, AlertTriangle, CheckCircle } from "lucide-react";
import { searchJobs, parseJobUrl, parseJobText, ApiClientError } from "../api/client";

type TabType = "search" | "url" | "text";
```

Delete:
- `Database` icon import
- `loadMockJobs` import
- `resetExistingDemo` state
- `handleMockLoadSubmit`
- Demo tab button with `data-testid="tab-mock"`
- form with `data-testid="form-mock"`
- reset checkbox with `data-testid="input-reset-demo"`
- mock submit button with `data-testid="btn-mock-submit"`

- [ ] **Step 4: Update ingestion panel tests**

Edit `frontend/job-agent-ui/src/test/IngestionPanel.test.tsx`:
- Remove `loadMockJobs` import and mock export.
- In the tab switching test, verify only `search`, `url`, and `text`.
- Delete the test that triggers `loadMockJobs`.

- [ ] **Step 5: Update API client and contract tests**

Edit `frontend/job-agent-ui/src/test/apiClient.test.ts`:
- Remove `loadMockJobs` import.
- Delete the `describe("loadMockJobs", ...)` block.

Edit `frontend/job-agent-ui/src/test/apiContract.test.ts`:
- Remove `loadMockJobs` from `EXPECTED_ENDPOINTS`.
- Remove `"MockLoadRequest"` from `expectedSchemas`.

- [ ] **Step 6: Update active batch integration test to use real retained ingestion**

Edit `frontend/job-agent-ui/src/test/activeBatch.test.tsx`:
```ts
import {
  listRoleProfiles,
  searchJobs,
  parseJobUrl,
  parseJobText,
  getReviewJobs,
  getJobs,
  getBatchSummary
} from "../api/client";
```

In the API mock, remove `loadMockJobs`. Use `parseJobText` as the ingestion trigger:
```ts
vi.mocked(parseJobText).mockResolvedValue(mockIngestionResponse1);
fireEvent.click(screen.getByTestId("tab-text"));
fireEvent.change(screen.getByTestId("input-text"), {
  target: { value: "Role requirements with enough text for ingestion." },
});
fireEvent.click(screen.getByTestId("btn-text-submit"));
```

Expected call:
```ts
expect(parseJobText).toHaveBeenCalledWith({
  role_profile_id: "prof-1",
  raw_text: "Role requirements with enough text for ingestion.",
});
```

For the second profile, resolve `parseJobText` with `mockIngestionResponse2` and submit the same retained text path. Keep the localStorage isolation assertions unchanged.

- [ ] **Step 7: Replace demo-branded frontend fixture data with neutral retained values**

Edit `frontend/job-agent-ui/src/test/ReviewPage.test.tsx`, `frontend/job-agent-ui/src/test/DashboardPage.test.tsx`, and `frontend/job-agent-ui/src/test/JobCard.test.tsx` so test jobs use:
```ts
source_platform: "manual_text",
```

Keep Vitest mocks because they are test-only doubles.

- [ ] **Step 8: Run frontend typecheck and tests immediately**

Run from `frontend/job-agent-ui/`:
```powershell
npm run typecheck
npm test -- --run
```

Expected: both commands pass. If this fails because of stale contract or client usage, fix frontend references before continuing.

---

## Task 6: Remove Dead UI Assets, Obsolete Docs, Debug Comments, and Unused Dependencies

**Files:**
- Delete: `frontend/job-agent-ui/src/App.css`
- Delete: `frontend/job-agent-ui/src/assets/vite.svg`
- Delete: `frontend/job-agent-ui/src/assets/react.svg`
- Delete: `frontend/job-agent-ui/src/assets/hero.png`
- Delete: `frontend/job-agent-ui/public/icons.svg`
- Delete: `frontend/job-agent-ui/README.md`
- Delete: `docs/tasks/`
- Delete: `docs/reports/`
- Delete: `docs/review/`
- Delete: `docs/plans/`
- Modify: `frontend/job-agent-ui/src/components/AppShell.tsx`
- Modify: `frontend/job-agent-ui/src/App.tsx`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/agents/nodes.py`
- Modify: `backend/app/services/search_service.py`
- Modify: `backend/tests/test_extraction_graph.py`
- Modify: `backend/tests/test_nodes.py`
- Modify: `backend/requirements.txt`
- Modify: `README.md`

- [ ] **Step 1: Confirm asset and stylesheet references before deletion**

Run:
```powershell
rg -n "App\\.css|vite\\.svg|react\\.svg|hero\\.png|icons\\.svg" frontend/job-agent-ui -S
```

Expected: no live references except the files themselves. Keep `frontend/job-agent-ui/public/favicon.svg` because `index.html` references it.

- [ ] **Step 2: Delete unused UI assets and Vite boilerplate docs**

Run:
```powershell
git rm frontend/job-agent-ui/src/App.css frontend/job-agent-ui/src/assets/vite.svg frontend/job-agent-ui/src/assets/react.svg frontend/job-agent-ui/src/assets/hero.png frontend/job-agent-ui/public/icons.svg frontend/job-agent-ui/README.md
```

- [ ] **Step 3: Remove unreachable AppShell fallback UI**

Edit `frontend/job-agent-ui/src/components/AppShell.tsx`:
```ts
interface AppShellProps {
  sidebarContent: React.ReactNode;
  activeBatchId?: string | null;
  activeProfileId?: string | null;
  triggerMetricsRefresh?: () => void;
}
```

Render the sidebar content directly:
```tsx
{sidebarContent}
```

Delete the fallback panels containing `Placeholder: Profile Selection UI` and `Placeholder: Job Ingestion UI`.

- [ ] **Step 4: Remove temporary comments and development assertions**

Remove development narration comments from:
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/app/db/models.py`
- `backend/app/agents/nodes.py`
- `backend/app/services/extraction_service.py`
- `backend/app/api/routes_jobs.py`
- `frontend/job-agent-ui/src/App.tsx`
- `frontend/job-agent-ui/src/api/client.ts`
- tests where comments describe mocking mechanics instead of intent

Keep concise comments that explain non-obvious behavior, validation, or error handling.

- [ ] **Step 5: Remove unused Python production dependencies**

Edit `backend/requirements.txt` to:
```text
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
langchain-core>=0.2.0
langchain-openai>=0.1.0
langgraph>=0.2.0
qdrant-client>=1.9.0
tavily-python>=0.3.0
httpx>=0.27.0
trafilatura>=1.8.0
sqlalchemy>=2.0.0
aiosqlite>=0.20.0
```

Do not change `backend/requirements-dev.txt` unless verification proves a dev-only dependency is unused and unneeded.

- [ ] **Step 6: Delete historical execution docs**

Run:
```powershell
git rm -r docs/tasks docs/reports docs/review docs/plans
```

Keep:
- `docs/superpowers/specs/2026-06-30-production-cleanup-design.md`
- `docs/superpowers/plans/2026-06-30-production-cleanup-implementation-plan.md`

- [ ] **Step 7: Rewrite root README for retained production behavior**

Edit `README.md` so it documents:
- retained architecture
- retained ingestion paths: Tavily search, manual URL, manual text
- SQLite as durable state and Qdrant as derived vector index
- OpenAI extraction and embeddings
- setup, run, contract export, backend tests, frontend tests, and build commands
- no demo seed, mock-load endpoint, mock datasets, or phase-history references

- [ ] **Step 8: Run cleanup scans**

Run:
```powershell
rg -n "TO[D]O|FIX[M]E|console\\.log|logger\\.debug|print\\(|Placeholder:|seed_demo|demo_loader|mock-load|MockLoadRequest|loadMockJobs|reset_existing_demo|resetExistingDemo|FakeJobExtractionClient" backend frontend shared README.md -S
```

Expected: no runtime hits. Test-only `mock` or `vi.mock` references are allowed, but removed runtime names must be absent.

Run:
```powershell
rg -n '"mock"|source_platform.*mock|input_source.*mock' backend/app backend/scripts frontend/job-agent-ui/src shared README.md -S
```

Expected: no output outside test paths. If a retained test path contains neutral fixture doubles, keep it.

---

## Task 7: Full Verification and Final Report

**Files:**
- Modify only if verification finds broken references

- [ ] **Step 1: Backend static and contract verification**

Run from `backend/`:
```powershell
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe scripts/export_api_contract.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Expected: all commands pass.

- [ ] **Step 2: Backend live startup verification**

Run from `backend/` in a long-running shell:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another shell:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/
$openapi = Invoke-RestMethod http://127.0.0.1:8000/openapi.json
$openapi.paths.PSObject.Properties.Name | Select-String "mock-load"
```

Expected: root returns `{"status":"ok"}` and the mock-load search returns no output. Stop only the uvicorn process started for this verification.

- [ ] **Step 3: Frontend verification**

Run from `frontend/job-agent-ui/`:
```powershell
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm ls
```

Expected: all commands pass.

- [ ] **Step 4: Frontend live startup verification**

Run from `frontend/job-agent-ui/` in a long-running shell:
```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

In another shell:
```powershell
Invoke-WebRequest http://127.0.0.1:5173/ -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

Expected: status code `200`. Stop only the Vite process started for this verification.

- [ ] **Step 5: Repository integrity scan**

Run from repository root:
```powershell
git status --short
git diff --check
rg -n "mock-load|MockLoadRequest|loadMockJobs|FakeJobExtractionClient|seed_demo|demo_loader|reset_existing_demo|resetExistingDemo|TO[D]O|FIX[M]E|console\\.log|logger\\.debug|print\\(" backend frontend shared README.md -S
rg -n '"mock"|source_platform.*mock|input_source.*mock' backend/app backend/scripts frontend/job-agent-ui/src shared README.md -S
```

Expected: `git diff --check` passes. Runtime scans have no hits. Test-only mocks remain confined under test files and are disclosed in the final report.

- [ ] **Step 6: Produce the final report**

Report these sections:
1. Files removed.
2. Files modified.
3. Dependencies removed.
4. Remaining unresolved work.
5. Items retained because safe deletion could not be proven.

Include verification command outcomes. If any required command fails, do not claim completion; report the failing command and evidence.
