"""Search ingestion workflow shared by API routes and agent tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import JobAgentState
from app.services.extraction_service import extract_from_url
from app.services.job_processing_service import JobProcessingResult, process_job_state
from app.services.search_service import SearchServiceError, search_service


@dataclass
class SearchIngestionResult:
    batch_id: UUID
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    job_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def ingest_search_jobs(
    session: AsyncSession,
    *,
    role_profile_id: str,
    query: str,
    max_urls: int | None,
    on_progress: Callable[[str], Awaitable[None]] | None = None,
) -> SearchIngestionResult:
    batch_id = uuid4()

    if on_progress:
        await on_progress("Connecting to Tavily to search job pages...")

    try:
        search_results = await search_service.search_jobs(query, max_urls=max_urls)
    except SearchServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "Search provider failed",
        ) from exc

    total = len(search_results)
    if on_progress:
        await on_progress(f"Found {total} recruiting pages. Extracting job data...")

    result = SearchIngestionResult(batch_id=batch_id)

    for idx, search_result in enumerate(search_results):
        if on_progress:
            domain = urlparse(search_result.url).netloc or "web"
            await on_progress(f"Analyzing listing {idx + 1}/{total} from {domain}...")
        try:
            extraction_state = await extract_from_url(
                batch_id=str(batch_id),
                role_profile_id=role_profile_id,
                source_url=search_result.url,
                input_source="tavily",
            )
            processing_result = await _process_ingested_state(
                session,
                extraction_state,
            )
        except HTTPException:
            raise
        except Exception:
            result.warnings.append(f"Failed to process search result URL: {search_result.url}")
            continue

        _merge_processing_result(result, processing_result)

    return result


async def _process_ingested_state(
    session: AsyncSession,
    extraction_state: JobAgentState,
) -> JobProcessingResult:
    try:
        return await process_job_state(session, extraction_state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


def _merge_processing_result(
    target: SearchIngestionResult,
    processing_result: JobProcessingResult,
) -> None:
    target.inserted_jobs += processing_result.inserted_jobs
    target.skipped_exact_duplicates += processing_result.skipped_exact_duplicates
    target.skipped_dedup_key_duplicates += processing_result.skipped_dedup_key_duplicates
    target.inserted_duplicate_metadata += processing_result.inserted_duplicate_metadata
    target.qdrant_upserted += processing_result.qdrant_upserted
    target.qdrant_synced = target.qdrant_synced and processing_result.qdrant_synced
    target.job_ids.extend(processing_result.job_ids)
    target.warnings.extend(processing_result.warnings)
