"""Agent tool registry wrapping existing production services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import json
from typing import Any

from app.services.job_search_workflow import ingest_search_jobs
from app.services.job_text_ingestion_workflow import ingest_raw_job_text
from app.services.profile_cv_draft_service import CreateCvDraftRequest, CreateCvSuggestionRequest
from app.services.profile_cv_export_service import ExportCvDraftRequest


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
            "list_profile_cvs": ToolDefinition(
                name="list_profile_cvs",
                description="List uploaded profile CV PDFs and active-version metadata.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "get_active_profile_cv": ToolDefinition(
                name="get_active_profile_cv",
                description="Return safe metadata for the active profile CV source of truth.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "view_profile_cv_metadata": ToolDefinition(
                name="view_profile_cv_metadata",
                description="Return safe metadata for a profile CV document and its active version.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "retrieve_profile_cv_chunks": ToolDefinition(
                name="retrieve_profile_cv_chunks",
                description="Retrieve relevant active CV chunks for backend AI reasoning.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "analyze_cv_structure": ToolDefinition(
                name="analyze_cv_structure",
                description="Report extracted CV structure reliability metadata without editing the PDF.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "retrieve_profile_documents": ToolDefinition(
                name="retrieve_profile_documents",
                description="Retrieve relevant chunks from uploaded profile PDFs.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "suggest_cv_improvements": ToolDefinition(
                name="suggest_cv_improvements",
                description="Store a grounded CV improvement suggestion without editing the PDF.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "create_cv_edit_draft": ToolDefinition(
                name="create_cv_edit_draft",
                description="Create an editable CV draft from approved wording-only suggestions.",
                requires_confirmation=True,
                handler=_not_wired,
            ),
            "preview_cv_edit_draft": ToolDefinition(
                name="preview_cv_edit_draft",
                description="Preview an editable CV draft without exporting or activating it.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "export_cv_draft_to_pdf": ToolDefinition(
                name="export_cv_draft_to_pdf",
                description="Export an approved CV edit draft into a real PDF version without activating it.",
                requires_confirmation=True,
                handler=_not_wired,
            ),
            "set_active_cv_version": ToolDefinition(
                name="set_active_cv_version",
                description="Set a profile CV version as the active source of truth after confirmation.",
                requires_confirmation=True,
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
    return build_retrieve_profile_cv_chunks_handler(retrieval_service, session)


def _document_safe_payload(document: object) -> dict[str, Any]:
    return {
        "document_id": str(getattr(document, "id", "")),
        "filename": str(getattr(document, "original_filename", "")),
        "status": str(getattr(document, "status", "")),
        "chunk_count": int(getattr(document, "chunk_count", 0) or 0),
        "active_version_id": (
            str(getattr(document, "active_version_id"))
            if getattr(document, "active_version_id", None)
            else None
        ),
    }


def _version_safe_payload(version: object) -> dict[str, Any]:
    return {
        "version_id": str(getattr(version, "id", "")),
        "version_number": int(getattr(version, "version_number", 0) or 0),
        "source_type": str(getattr(version, "source_type", "")),
        "extraction_status": str(getattr(version, "extraction_status", "")),
        "structure_status": str(getattr(version, "structure_status", "")),
        "structure_confidence": getattr(version, "structure_confidence", None),
    }


def build_list_profile_cvs_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        documents = await retrieval_service.list_profile_cvs(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
        )
        safe_documents = [_document_safe_payload(document) for document in documents]
        return ToolResult(
            content=f"Found {len(safe_documents)} uploaded profile CVs.",
            result_summary=f"Found {len(safe_documents)} profile CVs",
            safe_payload={"documents": safe_documents},
        )

    return handler


def build_suggest_cv_improvements_handler(
    draft_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        suggestion = await draft_service.create_suggestion(
            session,
            CreateCvSuggestionRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                document_id=str(request.context["document_id"]),
                version_id=str(request.context["version_id"]),
                job_id=request.arguments.get("job_id"),
                requirement=str(request.arguments["requirement"]),
                current_cv_evidence=str(request.arguments["current_cv_evidence"]),
                missing_or_weak_evidence=str(request.arguments["missing_or_weak_evidence"]),
                proposed_edit=str(request.arguments["proposed_edit"]),
                edit_kind=str(request.arguments["edit_kind"]),  # type: ignore[arg-type]
                risk_level=str(request.arguments["risk_level"]),  # type: ignore[arg-type]
                requires_confirmation=True,
            ),
        )
        return ToolResult(
            content="Stored 1 grounded CV improvement suggestion.",
            result_summary="Stored 1 CV suggestion",
            safe_payload={
                "suggestion_id": suggestion.id,
                "status": suggestion.status,
                "edit_kind": suggestion.edit_kind,
                "risk_level": suggestion.risk_level,
            },
        )

    return handler


def build_create_cv_edit_draft_handler(
    draft_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        draft = await draft_service.create_draft(
            session,
            CreateCvDraftRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                document_id=str(request.context["document_id"]),
                base_version_id=str(request.context["version_id"]),
                title=str(request.arguments.get("title", "CV edit draft")),
                suggestion_ids=[str(value) for value in request.arguments.get("suggestion_ids", [])],
                confirmed=bool(request.arguments.get("confirmed", False)),
                created_by="ai",
            ),
        )
        return ToolResult(
            content="Created a CV edit draft. Original PDF was not modified.",
            result_summary=f"Created CV draft: {draft.title}",
            safe_payload={
                "draft_id": draft.id,
                "status": draft.status,
                "title": draft.title,
                "structure_status": draft.structure_status_at_creation,
            },
        )

    return handler


def build_preview_cv_edit_draft_handler(
    draft_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        preview = await draft_service.preview_draft(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            draft_id=str(request.arguments["draft_id"]),
        )
        return ToolResult(
            content=json.dumps(preview, separators=(",", ":")),
            result_summary=f"Previewed CV draft: {preview['title']}",
            safe_payload={
                "draft_id": preview["draft_id"],
                "status": preview["status"],
                "structure_status": preview["structure_status"],
                "edit_count": len(preview.get("edits", [])),
                "has_template_recommendation": bool(preview.get("recommendation")),
            },
        )

    return handler


def build_get_active_profile_cv_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        active = await retrieval_service.get_active_cv(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
        )
        if active is None:
            return ToolResult(
                content="No active profile CV is selected.",
                result_summary="No active profile CV",
                safe_payload={"has_active_cv": False},
            )
        document, version = active
        return ToolResult(
            content=(
                "Active profile CV is available. "
                "Use retrieve_profile_cv_chunks to read relevant extracted text."
            ),
            result_summary=f"Active CV: {document.original_filename}",
            safe_payload={
                "has_active_cv": True,
                **_document_safe_payload(document),
                **_version_safe_payload(version),
            },
        )

    return handler


def build_view_profile_cv_metadata_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        return await build_get_active_profile_cv_handler(retrieval_service, session)(request)

    return handler


def build_retrieve_profile_cv_chunks_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        result = await retrieval_service.retrieve_active_cv_chunks(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            query=str(request.arguments.get("query", "")),
            limit=int(request.arguments.get("limit", 5)),
        )
        content = "\n\n".join(item.chunk.text for item in result.chunks)
        if result.document is None or result.version is None:
            return ToolResult(
                content="No active profile CV is selected.",
                result_summary="No active profile CV",
                safe_payload={"has_active_cv": False, "chunk_count": 0},
            )
        return ToolResult(
            content=content,
            result_summary=f"Retrieved {len(result.chunks)} active CV chunks",
            safe_payload={
                "document_id": result.document.id,
                "version_id": result.version.id,
                "chunk_count": len(result.chunks),
                "used_fallback": result.used_fallback,
            },
        )

    return handler


def build_analyze_cv_structure_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        active = await retrieval_service.get_active_cv(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
        )
        if active is None:
            return ToolResult(
                content="No active profile CV is selected.",
                result_summary="No active profile CV",
                safe_payload={"has_active_cv": False},
            )
        document, version = active
        structure_status = str(getattr(version, "structure_status", "not_extracted"))
        return ToolResult(
            content=(
                "CV structure status is "
                f"{structure_status}. Structure-preserving editing is not part of Phase 2."
            ),
            result_summary=f"CV structure: {structure_status}",
            safe_payload={
                "has_active_cv": True,
                "document_id": document.id,
                "version_id": version.id,
                "structure_status": structure_status,
                "structure_confidence": getattr(version, "structure_confidence", None),
            },
        )

    return handler


def _safe_ingestion_summary(
    *,
    inserted_jobs: int,
    skipped_duplicates: int,
    warning_count: int,
) -> str:
    job_word = "job" if inserted_jobs == 1 else "jobs"
    summary = f"Added {inserted_jobs} {job_word} to Review Queue."
    if skipped_duplicates:
        summary = f"{summary} Skipped {skipped_duplicates} duplicate jobs."
    if warning_count:
        summary = f"{summary} Encountered {warning_count} processing warnings."
    return summary


def build_search_jobs_handler(
    session: object,
    *,
    search_workflow: Callable[..., Awaitable[object]] = ingest_search_jobs,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        query = str(request.arguments.get("query", "")).strip()
        if not query:
            raise ValueError("search_jobs requires a query")

        kwargs = {}
        progress_callback = request.context.get("on_progress")
        if progress_callback is not None:
            kwargs["on_progress"] = progress_callback

        result = await search_workflow(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            query=query,
            max_urls=request.arguments.get("max_urls"),
            **kwargs,
        )
        inserted_jobs = int(getattr(result, "inserted_jobs", 0))
        skipped_duplicates = int(getattr(result, "skipped_exact_duplicates", 0)) + int(
            getattr(result, "skipped_dedup_key_duplicates", 0)
        )
        warnings = list(getattr(result, "warnings", []))
        summary = _safe_ingestion_summary(
            inserted_jobs=inserted_jobs,
            skipped_duplicates=skipped_duplicates,
            warning_count=len(warnings),
        )

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


def build_extract_job_from_text_handler(
    session: object,
    *,
    text_workflow: Callable[..., Awaitable[object]] = ingest_raw_job_text,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        raw_text = str(request.arguments.get("raw_text", "")).strip()
        if not raw_text:
            raise ValueError("extract_job_from_text requires raw_text")

        kwargs = {}
        source_url = request.arguments.get("source_url")
        if source_url:
            kwargs["source_url"] = str(source_url)
        progress_callback = request.context.get("on_progress")
        if progress_callback is not None:
            kwargs["on_progress"] = progress_callback

        result = await text_workflow(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            raw_text=raw_text,
            **kwargs,
        )
        inserted_jobs = int(getattr(result, "inserted_jobs", 0))
        skipped_duplicates = int(getattr(result, "skipped_exact_duplicates", 0)) + int(
            getattr(result, "skipped_dedup_key_duplicates", 0)
        )
        warnings = list(getattr(result, "warnings", []))
        job_ids = list(getattr(result, "job_ids", []))
        summary = _safe_ingestion_summary(
            inserted_jobs=inserted_jobs,
            skipped_duplicates=skipped_duplicates,
            warning_count=len(warnings),
        )

        return ToolResult(
            content=summary,
            result_summary=summary,
            safe_payload={
                "inserted_jobs": inserted_jobs,
                "skipped_duplicates": skipped_duplicates,
                "warning_count": len(warnings),
                "review_queue_path": "/review",
                "job_ids": job_ids,
                "batch_id": str(getattr(result, "batch_id", "")),
            },
        )

    return handler


def build_export_cv_draft_to_pdf_handler(
    export_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        version = await export_service.export_draft_to_pdf(
            session,
            ExportCvDraftRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                document_id=str(request.context["document_id"]),
                draft_id=str(request.arguments["draft_id"]),
                confirmed=bool(request.arguments.get("confirmed", False)),
                created_by="ai",
            ),
        )
        return ToolResult(
            content="Exported the CV draft as a new PDF version. The active CV was not changed.",
            result_summary=f"Exported CV draft as PDF version {version.version_number}",
            safe_payload={
                "document_id": version.document_id,
                "version_id": version.id,
                "version_number": version.version_number,
                "source_type": version.source_type,
                "extraction_status": version.extraction_status,
                "structure_status": version.structure_status,
                "structure_confidence": version.structure_confidence,
            },
        )

    return handler


def build_set_active_cv_version_handler(
    document_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        version = await document_service.set_active_version(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            document_id=str(request.context["document_id"]),
            version_id=str(request.arguments["version_id"]),
            confirmed=bool(request.arguments.get("confirmed", False)),
        )
        return ToolResult(
            content="Set the selected CV version as the active profile CV source of truth.",
            result_summary=f"Set CV version {version.version_number} active",
            safe_payload={
                "document_id": version.document_id,
                "version_id": version.id,
                "version_number": version.version_number,
                "source_type": version.source_type,
                "extraction_status": version.extraction_status,
                "structure_status": version.structure_status,
                "structure_confidence": version.structure_confidence,
            },
        )

    return handler
