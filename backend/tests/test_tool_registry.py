import pytest

from app.services.tool_registry import ToolRegistry, ToolRequest, ToolResult


@pytest.mark.asyncio
async def test_registry_exposes_safe_tool_metadata():
    registry = ToolRegistry()

    tools = registry.list_tools()

    assert "search_jobs" in tools
    assert tools["search_jobs"].requires_confirmation is False
    assert "api_key" not in tools["search_jobs"].description.lower()


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

    assert result.content == "Đã đưa 3 job vào Review Queue. Bỏ qua 1 job trùng."
    assert result.result_summary == "Đã đưa 3 job vào Review Queue. Bỏ qua 1 job trùng."
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
