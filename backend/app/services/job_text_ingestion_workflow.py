"""Raw job text ingestion workflow shared by API routes and agent tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.extraction_service import extract_from_raw_text
from app.services.job_processing_service import JobProcessingResult, process_job_state


@dataclass
class TextIngestionResult:
    batch_id: UUID
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    job_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def ingest_raw_job_text(
    session: AsyncSession,
    *,
    role_profile_id: str,
    raw_text: str,
    source_url: str | None = None,
    on_progress: Callable[[str], Awaitable[None] | None] | None = None,
) -> TextIngestionResult:
    batch_id = uuid4()

    await _emit_progress(on_progress, "Preparing pasted job text...")
    extraction_state = await extract_from_raw_text(
        batch_id=str(batch_id),
        role_profile_id=role_profile_id,
        raw_text=raw_text,
        source_url=source_url,
    )

    await _emit_progress(on_progress, "Extracting structured job data...")
    await _emit_progress(on_progress, "Scoring against the active profile...")

    try:
        processing_result = await process_job_state(session, extraction_state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _emit_progress(on_progress, "Saving job to Review Queue...")
    return _from_processing_result(batch_id, processing_result)


async def _emit_progress(
    callback: Callable[[str], Awaitable[None] | None] | None,
    message: str,
) -> None:
    if callback is None:
        return
    result = callback(message)
    if result is not None:
        await result


def _from_processing_result(
    batch_id: UUID,
    processing_result: JobProcessingResult,
) -> TextIngestionResult:
    return TextIngestionResult(
        batch_id=batch_id,
        inserted_jobs=processing_result.inserted_jobs,
        skipped_exact_duplicates=processing_result.skipped_exact_duplicates,
        skipped_dedup_key_duplicates=processing_result.skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=processing_result.inserted_duplicate_metadata,
        qdrant_upserted=processing_result.qdrant_upserted,
        qdrant_synced=processing_result.qdrant_synced,
        job_ids=list(processing_result.job_ids),
        warnings=list(processing_result.warnings),
    )
