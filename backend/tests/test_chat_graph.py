import pytest

from app.agents.chat_graph import run_chat_turn


class ChatLLMDouble:
    def __init__(self) -> None:
        self.calls = []

    async def generate_reply(self, *, user_message: str, working_memory: str) -> str:
        self.calls.append(
            {
                "user_message": user_message,
                "working_memory": working_memory,
            }
        )
        return f"LLM answer for: {user_message}"


@pytest.mark.asyncio
async def test_chat_turn_uses_llm_client_for_final_answer():
    llm_client = ChatLLMDouble()

    result = await run_chat_turn(
        {
            "conversation_id": "conv-1",
            "role_profile_id": "profile-1",
            "user_message": "Summarize my pipeline",
            "working_memory": "No saved jobs yet.",
            "tool_results": [],
        },
        llm_client=llm_client,
        tool_registry=None,
    )

    assert result["final_answer"] == "LLM answer for: Summarize my pipeline"
    assert result["tool_calls"] == []
    assert llm_client.calls == [
        {
            "user_message": "Summarize my pipeline",
            "working_memory": "No saved jobs yet.",
        }
    ]


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
