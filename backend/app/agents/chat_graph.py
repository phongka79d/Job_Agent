"""Chat-agent orchestration entrypoints."""

from __future__ import annotations

from app.agents.chat_state import ChatAgentState
from app.services.chat_llm_client import ChatLLMClientProtocol, ChatLLMProviderError


async def run_chat_turn(
    state: ChatAgentState,
    *,
    llm_client: ChatLLMClientProtocol | None,
    tool_registry: object | None,
) -> ChatAgentState:
    if not state.get("working_memory"):
        return {
            **state,
            "final_answer": "I need a selected profile and conversation memory before I can help.",
            "tool_calls": [],
        }
    if llm_client is None:
        raise ChatLLMProviderError("Chat LLM client is not configured.")

    final_answer = await llm_client.generate_reply(
        user_message=state["user_message"],
        working_memory=state["working_memory"],
    )
    return {
        **state,
        "final_answer": final_answer,
        "tool_calls": [],
    }
