"""Chat-agent orchestration entrypoints."""

from __future__ import annotations

from app.agents.chat_state import ChatAgentState


async def run_chat_turn(
    state: ChatAgentState,
    *,
    llm_client: object | None,
    tool_registry: object | None,
) -> ChatAgentState:
    if not state.get("working_memory"):
        return {
            **state,
            "final_answer": "I need a selected profile and conversation memory before I can help.",
            "tool_calls": [],
        }
    return {
        **state,
        "final_answer": "I can help with your job search, profile comparison, and application pipeline.",
        "tool_calls": [],
    }
