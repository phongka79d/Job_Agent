# Chat Pasted Job Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users paste a job description directly into Agent Chat and see a visible `extract_job_from_text` tool run through existing LLM extraction, scoring, persistence, Qdrant sync, and Review Queue flow.

**Architecture:** Reuse the existing `/api/jobs/parse-text` production pipeline by moving raw-text ingestion into a focused service. Add a real `extract_job_from_text` tool handler to the existing tool registry, then route likely pasted job text through that tool in chat with visible SSE progress events. Keep chat route orchestration thin and keep frontend API calls in existing clients.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, LangGraph extraction workflow, SQLite, Qdrant, React, TypeScript, Vitest, oxlint.

---

## Source Spec

- `docs/superpowers/specs/2026-07-01-chat-pasted-job-extraction-design.md`

## File Structure

- Create `backend/app/services/job_text_ingestion_workflow.py`
  - Owns raw job text ingestion for both API route and chat tool.
  - Calls `extract_from_raw_text(...)` and `process_job_state(...)`.
  - Returns sanitized ingestion counts, warnings, `batch_id`, and inserted `job_ids`.

- Modify `backend/app/api/routes_jobs.py`
  - Keep route behavior unchanged.
  - Replace route-local parse-text processing with the new service.

- Modify `backend/app/services/tool_registry.py`
  - Add `build_extract_job_from_text_handler(...)`.
  - Wire it to the existing `extract_job_from_text` tool definition.
  - Keep safe payload free of raw pasted text and provider internals.

- Modify `backend/app/api/routes_chat.py`
  - Add deterministic pasted-job detection.
  - Add `extract_job_from_text` to `build_tool_registry(...)`.
  - Route search intent first, pasted-job intent second, normal chat last.
  - Stream visible tool progress events.

- Modify frontend chat tests and `frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx`
  - Allow Review Queue navigation for `extract_job_from_text`, not only `search_jobs`.
  - Keep visible tool call timeline behavior.

- Modify/add tests:
  - `backend/tests/test_job_text_ingestion_workflow.py`
  - `backend/tests/test_tool_registry.py`
  - `backend/tests/test_routes_jobs.py`
  - `backend/tests/test_routes_chat.py`
  - `frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx`

---

### Task 1: Extract Shared Raw Text Ingestion Service

**Files:**
- Create: `backend/app/services/job_text_ingestion_workflow.py`
- Modify: `backend/app/api/routes_jobs.py`
- Test: `backend/tests/test_job_text_ingestion_workflow.py`
- Test: `backend/tests/test_routes_jobs.py`

- [ ] **Step 1: Write failing service tests**

Create `backend/tests/test_job_text_ingestion_workflow.py`:

```python
from uuid import UUID

import pytest

from app.agents.schemas import JobAgentState


@pytest.mark.asyncio
async def test_ingest_raw_job_text_delegates_to_extraction_and_processing(monkeypatch):
    from app.services import job_text_ingestion_workflow as workflow

    calls = []

    async def extract_double(*, batch_id, role_profile_id, raw_text, source_url=None):
        calls.append(
            {
                "batch_id": batch_id,
                "role_profile_id": role_profile_id,
                "raw_text": raw_text,
                "source_url": source_url,
            }
        )
        return JobAgentState(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            input_source="manual_text",
            source_url=source_url,
            raw_text=raw_text,
            cleaned_text=raw_text,
        )

    class ProcessingResult:
        inserted_jobs = 1
        skipped_exact_duplicates = 2
        skipped_dedup_key_duplicates = 3
        inserted_duplicate_metadata = 0
        qdrant_upserted = 1
        qdrant_synced = True
        job_ids = ["job-1"]
        warnings = ["minor warning"]

    async def process_double(session, state):
        assert session == "session"
        assert state["raw_text"] == "Senior AI Engineer\nRequirements: Python"
        return ProcessingResult()

    monkeypatch.setattr(workflow, "extract_from_raw_text", extract_double)
    monkeypatch.setattr(workflow, "process_job_state", process_double)

    result = await workflow.ingest_raw_job_text(
        "session",
        role_profile_id="profile-1",
        raw_text="Senior AI Engineer\nRequirements: Python",
        source_url="https://example.com/job",
    )

    assert isinstance(result.batch_id, UUID)
    assert calls == [
        {
            "batch_id": str(result.batch_id),
            "role_profile_id": "profile-1",
            "raw_text": "Senior AI Engineer\nRequirements: Python",
            "source_url": "https://example.com/job",
        }
    ]
    assert result.inserted_jobs == 1
    assert result.skipped_exact_duplicates == 2
    assert result.skipped_dedup_key_duplicates == 3
    assert result.qdrant_upserted == 1
    assert result.qdrant_synced is True
    assert result.job_ids == ["job-1"]
    assert result.warnings == ["minor warning"]


@pytest.mark.asyncio
async def test_ingest_raw_job_text_emits_progress(monkeypatch):
    from app.services import job_text_ingestion_workflow as workflow

    progress = []

    async def extract_double(**kwargs):
        return JobAgentState(
            batch_id=kwargs["batch_id"],
            role_profile_id=kwargs["role_profile_id"],
            input_source="manual_text",
            raw_text=kwargs["raw_text"],
            cleaned_text=kwargs["raw_text"],
        )

    class ProcessingResult:
        inserted_jobs = 0
        skipped_exact_duplicates = 0
        skipped_dedup_key_duplicates = 0
        inserted_duplicate_metadata = 0
        qdrant_upserted = 0
        qdrant_synced = True
        job_ids = []
        warnings = []

    async def process_double(session, state):
        return ProcessingResult()

    monkeypatch.setattr(workflow, "extract_from_raw_text", extract_double)
    monkeypatch.setattr(workflow, "process_job_state", process_double)

    await workflow.ingest_raw_job_text(
        object(),
        role_profile_id="profile-1",
        raw_text="Responsibilities: build ML systems. Requirements: Python.",
        on_progress=progress.append,
    )

    assert progress == [
        "Preparing pasted job text...",
        "Extracting structured job data...",
        "Scoring against the active profile...",
        "Saving job to Review Queue...",
    ]
```

- [ ] **Step 2: Run service tests and verify they fail**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_job_text_ingestion_workflow.py -q
```

Expected: fail because `app.services.job_text_ingestion_workflow` does not exist.

- [ ] **Step 3: Implement shared workflow service**

Create `backend/app/services/job_text_ingestion_workflow.py`:

```python
"""Raw job text ingestion workflow shared by API routes and agent tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.extraction_service import extract_from_raw_text
from app.services.job_processing_service import JobProcessingResult, process_job_state


@dataclass
class TextIngestionResult:
    batch_id: UUID
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    job_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def ingest_raw_job_text(
    session: AsyncSession,
    *,
    role_profile_id: str,
    raw_text: str,
    source_url: str | None = None,
    on_progress: Callable[[str], Awaitable[None] | None] | None = None,
) -> TextIngestionResult:
    batch_id = uuid4()

    await _emit_progress(on_progress, "Preparing pasted job text...")
    extraction_state = await extract_from_raw_text(
        batch_id=str(batch_id),
        role_profile_id=role_profile_id,
        raw_text=raw_text,
        source_url=source_url,
    )

    await _emit_progress(on_progress, "Extracting structured job data...")
    await _emit_progress(on_progress, "Scoring against the active profile...")

    try:
        processing_result = await process_job_state(session, extraction_state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _emit_progress(on_progress, "Saving job to Review Queue...")
    return _from_processing_result(batch_id, processing_result)


async def _emit_progress(
    callback: Callable[[str], Awaitable[None] | None] | None,
    message: str,
) -> None:
    if callback is None:
        return
    result = callback(message)
    if result is not None:
        await result


def _from_processing_result(
    batch_id: UUID,
    processing_result: JobProcessingResult,
) -> TextIngestionResult:
    return TextIngestionResult(
        batch_id=batch_id,
        inserted_jobs=processing_result.inserted_jobs,
        skipped_exact_duplicates=processing_result.skipped_exact_duplicates,
        skipped_dedup_key_duplicates=processing_result.skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=processing_result.inserted_duplicate_metadata,
        qdrant_upserted=processing_result.qdrant_upserted,
        qdrant_synced=processing_result.qdrant_synced,
        job_ids=list(processing_result.job_ids),
        warnings=list(processing_result.warnings),
    )
```

- [ ] **Step 4: Run service tests and verify they pass**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_job_text_ingestion_workflow.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Refactor parse-text route to reuse service**

Modify imports in `backend/app/api/routes_jobs.py`:

```python
from app.services.extraction_service import extract_from_url
from app.services.job_text_ingestion_workflow import ingest_raw_job_text
```

Replace `parse_job_text(...)` body with:

```python
@router.post("/parse-text", response_model=IngestionResponse)
async def parse_job_text(
    request: ParseJobTextRequest,
    session: SessionDep,
) -> IngestionResponse:
    source_url = str(request.source_url) if request.source_url is not None else None
    result = await ingest_raw_job_text(
        session,
        role_profile_id=str(request.role_profile_id),
        raw_text=request.raw_text,
        source_url=source_url,
    )

    return await _build_ingestion_response(
        session,
        result.batch_id,
        result.job_ids,
        inserted_jobs=result.inserted_jobs,
        skipped_exact_duplicates=result.skipped_exact_duplicates,
        skipped_dedup_key_duplicates=result.skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=result.inserted_duplicate_metadata,
        qdrant_upserted=result.qdrant_upserted,
        qdrant_synced=result.qdrant_synced,
        warnings=result.warnings,
    )
```

- [ ] **Step 6: Run route regression tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_jobs.py -q
```

Expected: all `test_routes_jobs.py` tests pass.

- [ ] **Step 7: Commit Task 1**

```powershell
git add backend/app/services/job_text_ingestion_workflow.py backend/app/api/routes_jobs.py backend/tests/test_job_text_ingestion_workflow.py backend/tests/test_routes_jobs.py
git commit -m "refactor: share raw job text ingestion workflow"
```

---

### Task 2: Add Real `extract_job_from_text` Tool Handler

**Files:**
- Modify: `backend/app/services/tool_registry.py`
- Test: `backend/tests/test_tool_registry.py`

- [ ] **Step 1: Write failing tool handler tests**

Append to `backend/tests/test_tool_registry.py`:

```python
@pytest.mark.asyncio
async def test_extract_job_from_text_handler_delegates_to_text_workflow():
    from app.services.tool_registry import build_extract_job_from_text_handler

    progress_messages = []
    calls = []

    async def workflow(session, *, role_profile_id, raw_text, source_url=None, on_progress=None):
        calls.append(
            {
                "session": session,
                "role_profile_id": role_profile_id,
                "raw_text": raw_text,
                "source_url": source_url,
                "on_progress": on_progress,
            }
        )
        if on_progress:
            await on_progress("Extracting structured job data...")

        class Result:
            batch_id = "batch-1"
            inserted_jobs = 1
            skipped_exact_duplicates = 0
            skipped_dedup_key_duplicates = 1
            inserted_duplicate_metadata = 0
            warnings = ["warning"]
            job_ids = ["job-1"]

        return Result()

    session = object()
    handler = build_extract_job_from_text_handler(session, text_workflow=workflow)

    result = await handler(
        ToolRequest(
            name="extract_job_from_text",
            arguments={
                "raw_text": "Senior AI Engineer\nResponsibilities: build AI tools.",
                "source_url": "https://example.com/job",
            },
            context={
                "role_profile_id": "profile-1",
                "on_progress": progress_messages.append,
            },
        )
    )

    assert calls[0]["session"] is session
    assert calls[0]["role_profile_id"] == "profile-1"
    assert calls[0]["raw_text"].startswith("Senior AI Engineer")
    assert calls[0]["source_url"] == "https://example.com/job"
    assert progress_messages == ["Extracting structured job data..."]
    assert result.content == "Added 1 job to Review Queue. Skipped 1 duplicate jobs. Encountered 1 processing warnings."
    assert result.result_summary == result.content
    assert result.safe_payload == {
        "inserted_jobs": 1,
        "skipped_duplicates": 1,
        "warning_count": 1,
        "review_queue_path": "/review",
        "job_ids": ["job-1"],
        "batch_id": "batch-1",
    }
    assert "Senior AI Engineer" not in str(result.safe_payload)


@pytest.mark.asyncio
async def test_extract_job_from_text_handler_requires_raw_text():
    from app.services.tool_registry import build_extract_job_from_text_handler

    handler = build_extract_job_from_text_handler(object())

    with pytest.raises(ValueError, match="extract_job_from_text requires raw_text"):
        await handler(
            ToolRequest(
                name="extract_job_from_text",
                arguments={"raw_text": "   "},
                context={"role_profile_id": "profile-1"},
            )
        )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_tool_registry.py -q
```

Expected: fail because `build_extract_job_from_text_handler` does not exist.

- [ ] **Step 3: Implement handler**

Modify `backend/app/services/tool_registry.py`.

Add import:

```python
from app.services.job_text_ingestion_workflow import ingest_raw_job_text
```

Add helper near `build_search_jobs_handler(...)`:

```python
def _safe_ingestion_summary(
    *,
    inserted_jobs: int,
    skipped_duplicates: int,
    warning_count: int,
) -> str:
    summary = f"Added {inserted_jobs} jobs to Review Queue."
    if skipped_duplicates:
        summary = f"{summary} Skipped {skipped_duplicates} duplicate jobs."
    if warning_count:
        summary = f"{summary} Encountered {warning_count} processing warnings."
    return summary
```

Update `build_search_jobs_handler(...)` to call `_safe_ingestion_summary(...)` instead of building duplicate summary logic.

Add:

```python
def build_extract_job_from_text_handler(
    session: object,
    *,
    text_workflow: Callable[..., Awaitable[object]] = ingest_raw_job_text,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        raw_text = str(request.arguments.get("raw_text", "")).strip()
        if not raw_text:
            raise ValueError("extract_job_from_text requires raw_text")

        kwargs = {}
        source_url = request.arguments.get("source_url")
        if source_url:
            kwargs["source_url"] = str(source_url)
        progress_callback = request.context.get("on_progress")
        if progress_callback is not None:
            kwargs["on_progress"] = progress_callback

        result = await text_workflow(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            raw_text=raw_text,
            **kwargs,
        )
        inserted_jobs = int(getattr(result, "inserted_jobs", 0))
        skipped_duplicates = int(getattr(result, "skipped_exact_duplicates", 0)) + int(
            getattr(result, "skipped_dedup_key_duplicates", 0)
        )
        warnings = list(getattr(result, "warnings", []))
        job_ids = list(getattr(result, "job_ids", []))
        summary = _safe_ingestion_summary(
            inserted_jobs=inserted_jobs,
            skipped_duplicates=skipped_duplicates,
            warning_count=len(warnings),
        )

        return ToolResult(
            content=summary,
            result_summary=summary,
            safe_payload={
                "inserted_jobs": inserted_jobs,
                "skipped_duplicates": skipped_duplicates,
                "warning_count": len(warnings),
                "review_queue_path": "/review",
                "job_ids": job_ids,
                "batch_id": str(getattr(result, "batch_id", "")),
            },
        )

    return handler
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_tool_registry.py -q
```

Expected: all `test_tool_registry.py` tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add backend/app/services/tool_registry.py backend/tests/test_tool_registry.py
git commit -m "feat: add extract job from text tool"
```

---

### Task 3: Route Pasted Job Text Through Visible Chat Tool Calls

**Files:**
- Modify: `backend/app/api/routes_chat.py`
- Test: `backend/tests/test_routes_chat.py`

- [ ] **Step 1: Write pasted job chat route test**

Append to `backend/tests/test_routes_chat.py`:

```python
@pytest.mark.asyncio
async def test_stream_pasted_job_text_calls_extract_text_tool_and_persists_visible_event(
    client,
    db_session,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    pasted_job = (
        "Senior AI Engineer\n"
        "Company: Example Labs\n"
        "Location: Hanoi\n"
        "Responsibilities: build LLM evaluation workflows and retrieval systems.\n"
        "Requirements: Python, FastAPI, LangGraph, vector databases, and applied ML experience.\n"
        "Benefits: hybrid work and training budget.\n"
        "Apply by sending your CV."
    )
    progress_messages = []

    async def text_handler(request: ToolRequest) -> ToolResult:
        assert request.name == "extract_job_from_text"
        assert request.context["role_profile_id"] == role_profile.id
        assert request.arguments["raw_text"] == pasted_job
        assert "on_progress" in request.context
        await request.context["on_progress"]("Extracting structured job data...")
        progress_messages.append("called")
        return ToolResult(
            content="Added 1 job to Review Queue.",
            result_summary="Added 1 job to Review Queue.",
            safe_payload={
                "inserted_jobs": 1,
                "review_queue_path": "/review",
                "job_ids": ["job-1"],
            },
        )

    def build_registry(session):
        assert session is db_session
        return ToolRegistry(overrides={"extract_job_from_text": text_handler})

    monkeypatch.setattr(routes_chat, "build_tool_registry", build_registry)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={"role_profile_id": role_profile.id, "title": "Session"},
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": pasted_job},
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": message_response.json()["message"]["id"]},
    )

    assert response.status_code == 200
    assert "event: tool_call_started" in response.text
    assert "event: tool_call_progress" in response.text
    assert "event: tool_call_completed" in response.text
    assert "Called 1 tool: Extract job from text." in response.text
    assert "Senior AI Engineer" not in response.text
    assert progress_messages == ["called"]

    calls = (
        await db_session.execute(
            select(AgentToolCall).where(
                AgentToolCall.conversation_id == conversation["id"]
            )
        )
    ).scalars().all()
    assert len(calls) == 1
    assert calls[0].tool_name == "extract_job_from_text"
    assert calls[0].status == "success"
    assert calls[0].input_summary == f"Pasted job text, {len(pasted_job)} characters"
    assert calls[0].result_summary == "Added 1 job to Review Queue."
    assert json.loads(calls[0].safe_payload_json) == {
        "inserted_jobs": 1,
        "review_queue_path": "/review",
        "job_ids": ["job-1"],
    }

    messages_response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/messages"
    )
    messages = messages_response.json()["messages"]
    assert messages[1]["content"] == (
        "Called 1 tool: Extract job from text. "
        "Added 1 job to Review Queue. Open Review Queue to inspect and approve it."
    )
```

- [ ] **Step 2: Write non-job fallback test**

Append to `backend/tests/test_routes_chat.py`:

```python
@pytest.mark.asyncio
async def test_stream_short_non_job_message_does_not_call_extract_text_tool(
    client,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    llm_client = ChatLLMDouble(answer="I can help with that.")
    monkeypatch.setattr(routes_chat, "chat_llm_client", llm_client, raising=False)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={"role_profile_id": role_profile.id, "title": "Session"},
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Can you compare my pipeline?"},
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": message_response.json()["message"]["id"]},
    )

    assert response.status_code == 200
    assert "extract_job_from_text" not in response.text
    assert "I can help with that." in response.text
    assert llm_client.calls
```

- [ ] **Step 3: Run route tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_chat.py -q
```

Expected: pasted-job test fails because chat route does not detect or execute `extract_job_from_text`.

- [ ] **Step 4: Implement deterministic pasted job heuristic**

Modify `backend/app/api/routes_chat.py`.

Add import:

```python
from app.services.tool_registry import (
    ToolRegistry,
    ToolRequest,
    build_extract_job_from_text_handler,
    build_search_jobs_handler,
)
```

Add constants and function near `_is_search_jobs_intent(...)`:

```python
PASTED_JOB_MIN_LENGTH = 240
PASTED_JOB_SIGNALS = (
    "responsibilities",
    "requirements",
    "qualifications",
    "skills",
    "company",
    "location",
    "salary",
    "benefits",
    "apply",
    "job description",
    "about the role",
    "what you will do",
)


def _is_pasted_job_text_intent(content: str) -> bool:
    normalized = content.casefold()
    if len(normalized) < PASTED_JOB_MIN_LENGTH:
        return False
    signal_count = sum(1 for signal in PASTED_JOB_SIGNALS if signal in normalized)
    return signal_count >= 3
```

- [ ] **Step 5: Register text tool**

Update `build_tool_registry(...)` in `backend/app/api/routes_chat.py`:

```python
def build_tool_registry(session: SessionDep) -> ToolRegistry:
    return ToolRegistry(
        overrides={
            "search_jobs": build_search_jobs_handler(session),
            "extract_job_from_text": build_extract_job_from_text_handler(session),
        }
    )
```

- [ ] **Step 6: Add small route helper to stream any tool execution**

Add helper inside `stream_conversation_events(...)` before `event_generator()` or as a nested helper inside `event_generator()`:

```python
async def _run_tool_with_progress(
    *,
    session: SessionDep,
    tool_call,
    request: ToolRequest,
):
    queue = asyncio.Queue()

    async def progress_callback(message: str):
        await queue.put(
            _sse_event(
                "tool_call_progress",
                {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.tool_name,
                    "message": message,
                },
            )
        )

    request.context["on_progress"] = progress_callback

    async def run_tool():
        try:
            result = await build_tool_registry(session).execute(request)
            await queue.put(result)
        except Exception as exc:
            await queue.put(exc)

    task = asyncio.create_task(run_tool())
    tool_result = None
    while not task.done() or not queue.empty():
        try:
            item = await asyncio.wait_for(queue.get(), timeout=0.1)
            if isinstance(item, str):
                yield item
            elif isinstance(item, Exception):
                raise item
            else:
                tool_result = item
        except asyncio.TimeoutError:
            continue

    if tool_result is None:
        raise RuntimeError(f"{request.name} failed without returning result")
    yield tool_result
```

If the existing search code already has equivalent queue logic, refactor it to use this helper instead of duplicating it for the text tool.

- [ ] **Step 7: Add pasted-job branch after search branch**

In `event_generator()`, keep search branch first. Add `elif _is_pasted_job_text_intent(user_message.content):` before normal chat:

```python
elif _is_pasted_job_text_intent(user_message.content):
    tool_call = await agent_event_service.create_tool_call(
        session,
        conversation_id=str(conversation_id),
        tool_name="extract_job_from_text",
        input_summary=f"Pasted job text, {len(user_message.content)} characters",
        safe_payload={"character_count": len(user_message.content)},
    )
    tool_call = await agent_event_service.mark_running(session, tool_call.id)
    yield _sse_event(
        "tool_call_started",
        {
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.tool_name,
            "status": tool_call.status,
            "input_summary": tool_call.input_summary,
        },
    )
    try:
        result_stream = _run_tool_with_progress(
            session=session,
            tool_call=tool_call,
            request=ToolRequest(
                name="extract_job_from_text",
                arguments={"raw_text": user_message.content},
                context={
                    "role_profile_id": conversation.role_profile_id,
                    "conversation_id": str(conversation_id),
                },
            ),
        )
        tool_result = None
        async for item in result_stream:
            if isinstance(item, str):
                yield item
            else:
                tool_result = item
        if tool_result is None:
            raise RuntimeError("extract_job_from_text failed without returning result")
    except Exception:
        logger.exception("extract_job_from_text tool failed")
        tool_call = await agent_event_service.mark_failed(
            session,
            tool_call.id,
            error_message="Job text extraction failed. Check the pasted text and provider settings.",
        )
        assistant_content = (
            "Called 1 tool: Extract job from text, but extraction failed. "
            "Check that the pasted text contains a real job description and try again."
        )
        agent_metadata_source = "chat_agent_tool_error"
        yield _sse_event(
            "tool_call_failed",
            {
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.tool_name,
                "status": tool_call.status,
                "error_message": tool_call.error_message,
            },
        )
    else:
        tool_call = await agent_event_service.mark_success(
            session,
            tool_call.id,
            result_summary=tool_result.result_summary,
            safe_payload=tool_result.safe_payload,
        )
        assistant_content = (
            "Called 1 tool: Extract job from text. "
            f"{tool_result.result_summary} Open Review Queue to inspect and approve it."
        )
        agent_metadata_source = "chat_agent_tool"
        yield _sse_event(
            "tool_call_completed",
            {
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.tool_name,
                "status": tool_call.status,
                "result_summary": tool_call.result_summary,
                "safe_payload": tool_result.safe_payload,
            },
        )
```

- [ ] **Step 8: Run chat route tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_chat.py -q
```

Expected: all route chat tests pass.

- [ ] **Step 9: Commit Task 3**

```powershell
git add backend/app/api/routes_chat.py backend/tests/test_routes_chat.py
git commit -m "feat: route pasted job text through chat tool"
```

---

### Task 4: Frontend Review Queue Navigation for Text Tool

**Files:**
- Modify: `frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx`
- Test: `frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx`

- [ ] **Step 1: Write failing frontend test**

In `frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx`, add a tool-call fixture:

```ts
const textExtractionToolCall: AgentToolCall = {
  id: "tool-text-1",
  conversation_id: "conv-1",
  assistant_message_id: null,
  tool_name: "extract_job_from_text",
  status: "success",
  input_summary: "Pasted job text, 280 characters",
  result_summary: "Added 1 job to Review Queue.",
  safe_payload_json: "{\"inserted_jobs\":1,\"review_queue_path\":\"/review\"}",
  error_message: null,
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:01Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:01Z",
};
```

Add test:

```ts
it("navigates to review queue after pasted job text extraction succeeds", async () => {
  vi.mocked(useOutletContext).mockReturnValue({
    activeProfileId: "profile-1",
    triggerMetricsRefresh: vi.fn(),
  });
  vi.mocked(createConversation).mockResolvedValue({
    id: "conv-1",
    role_profile_id: "profile-1",
    title: "Job paste session",
    status: "active",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  });
  vi.mocked(sendChatMessage).mockResolvedValue({
    message: {
      id: "msg-1",
      conversation_id: "conv-1",
      role: "user",
      content: "Senior AI Engineer\nResponsibilities: build AI systems.",
      token_count: null,
      metadata_json: null,
      created_at: "2026-01-01T00:00:00Z",
    },
    stream_url: "/stream",
  });
  vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);
  vi.mocked(listAgentToolCalls).mockResolvedValue([textExtractionToolCall]);

  render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

  fireEvent.change(screen.getByLabelText("Message"), {
    target: { value: "Senior AI Engineer\nResponsibilities: build AI systems." },
  });
  fireEvent.click(screen.getByRole("button", { name: /send message/i }));

  await waitFor(() => {
    expect(screen.getByText("extract_job_from_text")).toBeInTheDocument();
    expect(screen.getByText("Added 1 job to Review Queue.")).toBeInTheDocument();
    expect(navigate).toHaveBeenCalledWith("/review");
  });
});
```

- [ ] **Step 2: Run frontend test and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/ChatWorkspacePage.test.tsx
```

Expected: fail because `shouldOpenReviewQueue(...)` only accepts `search_jobs`.

- [ ] **Step 3: Update Review Queue navigation predicate**

In `frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx`, replace:

```ts
if (toolCall.tool_name !== "search_jobs" || toolCall.status !== "success") {
  return false;
}
```

with:

```ts
const opensReviewQueue = new Set(["search_jobs", "extract_job_from_text"]);
if (!opensReviewQueue.has(toolCall.tool_name) || toolCall.status !== "success") {
  return false;
}
```

- [ ] **Step 4: Run frontend test and verify pass**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/ChatWorkspacePage.test.tsx
```

Expected: `ChatWorkspacePage.test.tsx` passes.

- [ ] **Step 5: Commit Task 4**

```powershell
git add frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx
git commit -m "feat(ui): open review queue after pasted job extraction"
```

---

### Task 5: Final Verification and Safety Sweep

**Files:**
- Modify only if verification reveals stale references or test breakage.

- [ ] **Step 1: Run backend verification**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Expected:

- compileall exits `0`
- pytest reports all tests passed
- pip check reports `No broken requirements found.`

- [ ] **Step 2: Run frontend verification**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Expected:

- lint exits `0`; existing warnings are acceptable if unchanged
- typecheck exits `0`
- tests pass
- build exits `0`

- [ ] **Step 3: Scan for unsafe runtime leakage and non-English user-facing copy introduced by this feature**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
rg -n "api_key|OPENAI_API_KEY|raw_text|prompt|Called 1 tool|Extract job from text|Đang|Tìm|việc|công cụ" backend\app frontend\job-agent-ui\src
```

Expected:

- no API key or provider payload is included in frontend-safe payloads
- `raw_text` appears only as backend internal argument/request field, not in frontend tool summaries or `safe_payload`
- new runtime strings are English
- old hidden Vietnamese intent keywords may remain only in deterministic detection compatibility code

- [ ] **Step 4: Review final diff**

```powershell
git diff --check
git status --short
git diff --stat
```

Expected:

- no whitespace errors
- only scoped files changed
- no deleted production architecture files
- no demo/mock runtime data introduced

- [ ] **Step 5: Commit final cleanup if needed**

Only if Step 1-4 required cleanup edits:

```powershell
git add backend/app/services/job_text_ingestion_workflow.py backend/app/api/routes_jobs.py backend/app/services/tool_registry.py backend/app/api/routes_chat.py backend/tests/test_job_text_ingestion_workflow.py backend/tests/test_tool_registry.py backend/tests/test_routes_jobs.py backend/tests/test_routes_chat.py frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx
git commit -m "test: verify pasted job chat extraction"
```

---

## Self-Review Notes

- Spec coverage:
  - Chat paste detection: Task 3.
  - Visible tool call states/progress: Task 3 backend SSE and existing frontend timeline.
  - Reuse existing extraction/scoring/Qdrant path: Task 1 and Task 2.
  - Review Queue navigation: Task 4.
  - English runtime copy and no secret/raw payload leakage: Task 5.

- Scope:
  - No new UI form.
  - No new ingestion architecture.
  - No OCR.
  - No demo/mock runtime data.

- Type consistency:
  - Tool name is consistently `extract_job_from_text`.
  - Safe payload consistently uses `inserted_jobs`, `skipped_duplicates`, `warning_count`, `review_queue_path`, optional `job_ids`, optional `batch_id`.
