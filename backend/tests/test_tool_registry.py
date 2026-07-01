import pytest

from app.services.tool_registry import ToolRegistry, ToolRequest


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
