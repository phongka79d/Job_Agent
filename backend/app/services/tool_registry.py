"""Agent tool registry wrapping existing production services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolRequest:
    name: str
    arguments: dict[str, Any]
    context: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    content: str
    result_summary: str
    safe_payload: dict[str, Any]


ToolHandler = Callable[[ToolRequest], Awaitable[ToolResult]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    requires_confirmation: bool
    handler: ToolHandler


async def _not_wired(request: ToolRequest) -> ToolResult:
    return ToolResult(
        content=f"Tool {request.name} is registered but not connected to execution yet.",
        result_summary=f"{request.name} is registered",
        safe_payload={"tool_name": request.name},
    )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {
            "search_jobs": ToolDefinition(
                name="search_jobs",
                description="Search for jobs using the configured search provider and persist extracted results.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "extract_job_from_url": ToolDefinition(
                name="extract_job_from_url",
                description="Extract one public job posting from a URL and persist it for review.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "extract_job_from_text": ToolDefinition(
                name="extract_job_from_text",
                description="Extract one job from user-provided text and persist it for review.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "update_job_status": ToolDefinition(
                name="update_job_status",
                description="Change a saved job application status after user confirmation.",
                requires_confirmation=True,
                handler=_not_wired,
            ),
            "retrieve_profile_documents": ToolDefinition(
                name="retrieve_profile_documents",
                description="Retrieve relevant chunks from uploaded profile PDFs.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
        }

    def list_tools(self) -> dict[str, ToolDefinition]:
        return dict(self._tools)

    async def execute(self, request: ToolRequest) -> ToolResult:
        tool = self._tools.get(request.name)
        if tool is None:
            raise ValueError(f"Unknown tool: {request.name}")
        return await tool.handler(request)
