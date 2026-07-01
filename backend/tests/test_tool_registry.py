import pytest

from app.services.tool_registry import ToolRegistry, ToolRequest, ToolResult


@pytest.mark.asyncio
async def test_registry_exposes_safe_tool_metadata():
    registry = ToolRegistry()

    tools = registry.list_tools()

    assert "search_jobs" in tools
    assert tools["search_jobs"].requires_confirmation is False
    assert "api_key" not in tools["search_jobs"].description.lower()
    for tool_name in [
        "list_profile_cvs",
        "get_active_profile_cv",
        "view_profile_cv_metadata",
        "retrieve_profile_cv_chunks",
        "analyze_cv_structure",
    ]:
        assert tool_name in tools
        assert tools[tool_name].requires_confirmation is False
        assert "api_key" not in tools[tool_name].description.lower()


@pytest.mark.asyncio
async def test_unknown_tool_fails_cleanly():
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="Unknown tool"):
        await registry.execute(ToolRequest(name="missing", arguments={}, context={}))


@pytest.mark.asyncio
async def test_tool_result_exposes_summary_not_secret_payload():
    async def handler(request):
        return ToolResult(
            content="Found jobs",
            result_summary="Found 3 jobs",
            safe_payload={"inserted_jobs": 3},
        )

    registry = ToolRegistry(overrides={"search_jobs": handler})
    result = await registry.execute(
        ToolRequest(
            name="search_jobs",
            arguments={"query": "AI Engineer Intern Hanoi"},
            context={"role_profile_id": "profile-1"},
        )
    )

    assert result.result_summary == "Found 3 jobs"
    assert "api" not in str(result.safe_payload).lower()


def test_registry_rejects_unknown_tool_override():
    async def handler(request):
        return ToolResult(content="", result_summary="", safe_payload={})

    with pytest.raises(ValueError, match="Cannot override unknown tool"):
        ToolRegistry(overrides={"missing": handler})


@pytest.mark.asyncio
async def test_search_jobs_handler_delegates_to_search_workflow():
    from app.services.tool_registry import build_search_jobs_handler

    calls = []

    async def workflow(session, *, role_profile_id, query, max_urls):
        calls.append(
            {
                "session": session,
                "role_profile_id": role_profile_id,
                "query": query,
                "max_urls": max_urls,
            }
        )

        class Result:
            inserted_jobs = 3
            skipped_exact_duplicates = 1
            skipped_dedup_key_duplicates = 0
            inserted_duplicate_metadata = 0
            warnings = []

        return Result()

    session = object()
    handler = build_search_jobs_handler(
        session,
        search_workflow=workflow,
    )

    result = await handler(
        ToolRequest(
            name="search_jobs",
            arguments={"query": "AI Engineer Intern Hanoi", "max_urls": 4},
            context={"role_profile_id": "profile-1"},
        )
    )

    assert result.content == "Added 3 jobs to Review Queue. Skipped 1 duplicate jobs."
    assert result.result_summary == "Added 3 jobs to Review Queue. Skipped 1 duplicate jobs."
    assert result.safe_payload == {
        "inserted_jobs": 3,
        "skipped_duplicates": 1,
        "warning_count": 0,
        "review_queue_path": "/review",
    }
    assert calls == [
        {
            "session": session,
            "role_profile_id": "profile-1",
            "query": "AI Engineer Intern Hanoi",
            "max_urls": 4,
        }
    ]


@pytest.mark.asyncio
async def test_extract_job_from_text_handler_delegates_to_text_workflow():
    from app.services.tool_registry import build_extract_job_from_text_handler

    progress_messages = []
    calls = []

    async def progress_cb(message):
        progress_messages.append(message)

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
                "on_progress": progress_cb,
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


@pytest.mark.asyncio
async def test_profile_cv_tool_handlers_return_sanitized_payloads():
    from app.services.tool_registry import (
        build_analyze_cv_structure_handler,
        build_get_active_profile_cv_handler,
        build_list_profile_cvs_handler,
        build_retrieve_profile_cv_chunks_handler,
        build_view_profile_cv_metadata_handler,
    )

    class Document:
        id = "doc-1"
        original_filename = "cv.pdf"
        status = "ready"
        chunk_count = 2
        active_version_id = "version-1"

    class Version:
        id = "version-1"
        version_number = 1
        source_type = "original_upload"
        extraction_status = "ready"
        structure_status = "not_extracted"
        structure_confidence = None

    class Chunk:
        text = "Private full CV text with Python and FastAPI"
        id = "chunk-1"
        chunk_index = 0

    class Item:
        chunk = Chunk()
        score_source = "sqlite_keyword"

    class Result:
        document = Document()
        version = Version()
        chunks = [Item()]
        used_fallback = True

    class Retrieval:
        async def list_profile_cvs(self, session, *, role_profile_id):
            return [Document()]

        async def get_active_cv(self, session, *, role_profile_id):
            return Document(), Version()

        async def retrieve_active_cv_chunks(self, session, *, role_profile_id, query, limit):
            return Result()

    session = object()
    request = ToolRequest(
        name="retrieve_profile_cv_chunks",
        arguments={"query": "Python", "limit": 3},
        context={"role_profile_id": "profile-1"},
    )

    retrieve_result = await build_retrieve_profile_cv_chunks_handler(Retrieval(), session)(request)
    assert "Private full CV text" in retrieve_result.content
    assert "Private full CV text" not in str(retrieve_result.safe_payload)
    assert retrieve_result.safe_payload == {
        "document_id": "doc-1",
        "version_id": "version-1",
        "chunk_count": 1,
        "used_fallback": True,
    }

    list_result = await build_list_profile_cvs_handler(Retrieval(), session)(request)
    assert list_result.safe_payload["documents"][0]["document_id"] == "doc-1"

    active_result = await build_get_active_profile_cv_handler(Retrieval(), session)(request)
    assert active_result.safe_payload["document_id"] == "doc-1"

    metadata_result = await build_view_profile_cv_metadata_handler(Retrieval(), session)(request)
    assert metadata_result.safe_payload["document_id"] == "doc-1"

    structure_result = await build_analyze_cv_structure_handler(Retrieval(), session)(request)
    assert structure_result.safe_payload["structure_status"] == "not_extracted"
