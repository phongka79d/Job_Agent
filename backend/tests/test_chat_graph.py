import pytest

from app.agents.chat_graph import run_chat_turn


@pytest.mark.asyncio
async def test_chat_turn_returns_final_answer_without_fake_production_client():
    result = await run_chat_turn(
        {
            "conversation_id": "conv-1",
            "role_profile_id": "profile-1",
            "user_message": "Summarize my pipeline",
            "working_memory": "No saved jobs yet.",
            "tool_results": [],
        },
        llm_client=None,
        tool_registry=None,
    )

    assert result["final_answer"]
    assert result["tool_calls"] == []


@pytest.mark.asyncio
async def test_chat_turn_requires_working_memory():
    result = await run_chat_turn(
        {
            "conversation_id": "conv-1",
            "role_profile_id": "profile-1",
            "user_message": "Find jobs",
            "working_memory": "",
            "tool_results": [],
        },
        llm_client=None,
        tool_registry=None,
    )

    assert "selected profile" in result["final_answer"]
    assert result["tool_calls"] == []
