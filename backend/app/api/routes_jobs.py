"""Job API routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.routes_role_profiles import SessionDep
from app.api.schemas import (
    IngestionResponse,
    JobListResponse,
    JobResponse,
    ParseJobTextRequest,
    ParseJobUrlRequest,
    SearchJobsRequest,
    StatusMutationResponse,
    StatusUpdateRequest,
)
from app.agents.schemas import JobAgentState
from app.core import constants
from app.db.models import JobPost
from app.services.extraction_service import extract_from_raw_text, extract_from_url
from app.services.job_text_ingestion_workflow import ingest_raw_job_text
from app.services.job_search_workflow import ingest_search_jobs
from app.services.job_processing_service import (
    InvalidStatusTransition,
    JobProcessingResult,
    approve_job,
    process_job_state,
    reject_job,
    update_job_status,
)


DEFAULT_JOB_QUERY_LIMIT = 50
MAX_JOB_QUERY_LIMIT = 100
DASHBOARD_STATUSES = (*constants.JOB_STATUSES, "tracked")

LimitQuery = Annotated[
    int,
    Query(ge=1, le=MAX_JOB_QUERY_LIMIT),
]

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _mutate_job_status(
    mutation: Callable[[], Awaitable[JobPost]],
) -> JobPost:
    try:
        return await mutation()
    except InvalidStatusTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


async def _load_jobs_by_ids(session: SessionDep, job_ids: list[str]) -> list[JobPost]:
    if not job_ids:
        return []

    result = await session.execute(select(JobPost).where(JobPost.id.in_(job_ids)))
    jobs_by_id = {job.id: job for job in result.scalars()}
    return [jobs_by_id[job_id] for job_id in job_ids if job_id in jobs_by_id]


async def _build_ingestion_response(
    session: SessionDep,
    batch_id: UUID,
    job_ids: list[str],
    *,
    inserted_jobs: int,
    skipped_exact_duplicates: int,
    skipped_dedup_key_duplicates: int,
    inserted_duplicate_metadata: int,
    qdrant_upserted: int,
    qdrant_synced: bool,
    warnings: list[str],
) -> IngestionResponse:
    jobs = await _load_jobs_by_ids(session, job_ids)
    return IngestionResponse(
        batch_id=batch_id,
        inserted_jobs=inserted_jobs,
        skipped_exact_duplicates=skipped_exact_duplicates,
        skipped_dedup_key_duplicates=skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=inserted_duplicate_metadata,
        qdrant_upserted=qdrant_upserted,
        qdrant_synced=qdrant_synced,
        jobs=jobs,
        warnings=warnings,
    )


async def _process_ingested_state(
    session: SessionDep,
    batch_id: UUID,
    extraction_state: JobAgentState,
) -> JobProcessingResult:
    try:
        return await process_job_state(session, extraction_state)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


async def _process_single_ingested_state(
    session: SessionDep,
    batch_id: UUID,
    extraction_state: JobAgentState,
) -> IngestionResponse:
    processing_result = await _process_ingested_state(session, batch_id, extraction_state)

    return await _build_ingestion_response(
        session,
        batch_id,
        processing_result.job_ids,
        inserted_jobs=processing_result.inserted_jobs,
        skipped_exact_duplicates=processing_result.skipped_exact_duplicates,
        skipped_dedup_key_duplicates=processing_result.skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=processing_result.inserted_duplicate_metadata,
        qdrant_upserted=processing_result.qdrant_upserted,
        qdrant_synced=processing_result.qdrant_synced,
        warnings=processing_result.warnings,
    )


@router.post("/parse-text", response_model=IngestionResponse)
async def parse_job_text(
    request: ParseJobTextRequest,
    session: SessionDep,
) -> IngestionResponse:
    source_url = str(request.source_url) if request.source_url is not None else None
    result = await ingest_raw_job_text(
        session,
        role_profile_id=str(request.role_profile_id),
        raw_text=request.raw_text,
        source_url=source_url,
    )

    return await _build_ingestion_response(
        session,
        result.batch_id,
        result.job_ids,
        inserted_jobs=result.inserted_jobs,
        skipped_exact_duplicates=result.skipped_exact_duplicates,
        skipped_dedup_key_duplicates=result.skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=result.inserted_duplicate_metadata,
        qdrant_upserted=result.qdrant_upserted,
        qdrant_synced=result.qdrant_synced,
        warnings=result.warnings,
    )


@router.post("/parse-url", response_model=IngestionResponse)
async def parse_job_url(
    request: ParseJobUrlRequest,
    session: SessionDep,
) -> IngestionResponse:
    source_url = str(request.source_url)
    parsed_url = urlparse(source_url)
    if parsed_url.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_url must use http or https",
        )

    batch_id = uuid4()

    extraction_state = await extract_from_url(
        batch_id=str(batch_id),
        role_profile_id=str(request.role_profile_id),
        source_url=source_url,
        input_source="manual_url",
    )
    return await _process_single_ingested_state(session, batch_id, extraction_state)


@router.post("/search", response_model=IngestionResponse)
async def search_jobs(
    request: SearchJobsRequest,
    session: SessionDep,
) -> IngestionResponse:
    result = await ingest_search_jobs(
        session,
        role_profile_id=str(request.role_profile_id),
        query=request.query,
        max_urls=request.max_urls,
    )

    return await _build_ingestion_response(
        session,
        result.batch_id,
        result.job_ids,
        inserted_jobs=result.inserted_jobs,
        skipped_exact_duplicates=result.skipped_exact_duplicates,
        skipped_dedup_key_duplicates=result.skipped_dedup_key_duplicates,
        inserted_duplicate_metadata=result.inserted_duplicate_metadata,
        qdrant_upserted=result.qdrant_upserted,
        qdrant_synced=result.qdrant_synced,
        warnings=result.warnings,
    )


@router.get("/review", response_model=JobListResponse)
async def list_review_jobs(
    role_profile_id: UUID,
    session: SessionDep,
    limit: LimitQuery = DEFAULT_JOB_QUERY_LIMIT,
) -> JobListResponse:
    result = await session.execute(
        select(JobPost)
        .where(
            JobPost.role_profile_id == str(role_profile_id),
            JobPost.status == "pending_review",
            JobPost.duplicate_of_job_id.is_(None),
        )
        .order_by(
            JobPost.final_score.is_(None),
            JobPost.final_score.desc(),
            JobPost.discovered_at.desc(),
        )
        .limit(limit)
    )
    return JobListResponse(jobs=list(result.scalars()))


@router.get("", response_model=JobListResponse)
async def list_dashboard_jobs(
    role_profile_id: UUID,
    session: SessionDep,
    status_filter: Annotated[str, Query(alias="status")] = "saved",
    limit: LimitQuery = DEFAULT_JOB_QUERY_LIMIT,
) -> JobListResponse:
    if status_filter not in DASHBOARD_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {DASHBOARD_STATUSES}",
        )

    statuses = (
        constants.TRACKED_JOB_STATUSES
        if status_filter == "tracked"
        else (status_filter,)
    )
    result = await session.execute(
        select(JobPost)
        .where(
            JobPost.role_profile_id == str(role_profile_id),
            JobPost.status.in_(statuses),
            JobPost.duplicate_of_job_id.is_(None),
        )
        .order_by(
            JobPost.final_score.is_(None),
            JobPost.final_score.desc(),
        )
        .limit(limit)
    )
    return JobListResponse(jobs=list(result.scalars()))


@router.get("/{id}", response_model=JobResponse)
async def get_job(id: UUID, session: SessionDep) -> JobPost:
    result = await session.execute(
        select(JobPost).where(JobPost.id == str(id)).limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job not found",
        )
    return job


@router.post("/{id}/approve", response_model=StatusMutationResponse)
async def approve_job_route(id: UUID, session: SessionDep) -> JobPost:
    job_id = str(id)
    return await _mutate_job_status(lambda: approve_job(session, job_id))


@router.post("/{id}/reject", response_model=StatusMutationResponse)
async def reject_job_route(id: UUID, session: SessionDep) -> JobPost:
    job_id = str(id)
    return await _mutate_job_status(lambda: reject_job(session, job_id))


@router.patch("/{id}/status", response_model=StatusMutationResponse)
async def update_job_status_route(
    id: UUID,
    request: StatusUpdateRequest,
    session: SessionDep,
) -> JobPost:
    if request.status == "ignored":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="manual status update cannot set ignored",
        )

    job_id = str(id)
    return await _mutate_job_status(
        lambda: update_job_status(session, job_id, request.status)
    )
