"""State schema for chat-agent orchestration."""

from __future__ import annotations

from typing import Any, TypedDict


class ChatAgentState(TypedDict, total=False):
    conversation_id: str
    role_profile_id: str
    user_message: str
    working_memory: str
    tool_results: list[dict[str, Any]]
    final_answer: str
    tool_calls: list[dict[str, Any]]
    error_reason: str | None
