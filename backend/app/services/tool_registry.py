"""Agent tool registry wrapping existing production services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.services.job_search_workflow import ingest_search_jobs


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
    def __init__(self, overrides: dict[str, ToolHandler] | None = None) -> None:
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
        for name, handler in (overrides or {}).items():
            if name not in self._tools:
                raise ValueError(f"Cannot override unknown tool: {name}")
            definition = self._tools[name]
            self._tools[name] = ToolDefinition(
                name=definition.name,
                description=definition.description,
                requires_confirmation=definition.requires_confirmation,
                handler=handler,
            )

    def list_tools(self) -> dict[str, ToolDefinition]:
        return dict(self._tools)

    async def execute(self, request: ToolRequest) -> ToolResult:
        tool = self._tools.get(request.name)
        if tool is None:
            raise ValueError(f"Unknown tool: {request.name}")
        return await tool.handler(request)


def build_retrieve_profile_documents_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        chunks = await retrieval_service.retrieve(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            query=str(request.arguments.get("query", "")),
            limit=int(request.arguments.get("limit", 5)),
        )
        content = "\n\n".join(chunk.text for chunk in chunks)
        return ToolResult(
            content=content,
            result_summary=f"Retrieved {len(chunks)} profile document chunks",
            safe_payload={"chunk_count": len(chunks)},
        )

    return handler


def build_search_jobs_handler(
    session: object,
    *,
    search_workflow: Callable[..., Awaitable[object]] = ingest_search_jobs,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        query = str(request.arguments.get("query", "")).strip()
        if not query:
            raise ValueError("search_jobs requires a query")

        result = await search_workflow(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            query=query,
            max_urls=request.arguments.get("max_urls"),
        )
        inserted_jobs = int(getattr(result, "inserted_jobs", 0))
        skipped_duplicates = int(getattr(result, "skipped_exact_duplicates", 0)) + int(
            getattr(result, "skipped_dedup_key_duplicates", 0)
        )
        warnings = list(getattr(result, "warnings", []))
        summary = f"Đã đưa {inserted_jobs} job vào Review Queue."
        if skipped_duplicates:
            summary = f"{summary} Bỏ qua {skipped_duplicates} job trùng."
        if warnings:
            summary = f"{summary} Có {len(warnings)} cảnh báo khi xử lý."

        return ToolResult(
            content=summary,
            result_summary=summary,
            safe_payload={
                "inserted_jobs": inserted_jobs,
                "skipped_duplicates": skipped_duplicates,
                "warning_count": len(warnings),
                "review_queue_path": "/review",
            },
        )

    return handler
