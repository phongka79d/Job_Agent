"""Job API routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.routes_role_profiles import SessionDep
from app.api.schemas import (
    JobListResponse,
    JobResponse,
    StatusMutationResponse,
    StatusUpdateRequest,
)
from app.core import constants
from app.db.models import JobPost
from app.services.job_processing_service import (
    InvalidStatusTransition,
    approve_job,
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
