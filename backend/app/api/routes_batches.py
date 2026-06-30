"""Batch API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, func, select

from app.api.routes_role_profiles import SessionDep
from app.api.schemas import BatchSummaryResponse
from app.db.models import JobPost


router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("/{batch_id}/summary", response_model=BatchSummaryResponse)
async def get_batch_summary(
    batch_id: UUID,
    session: SessionDep,
) -> BatchSummaryResponse:
    result = await session.execute(
        select(
            func.count(JobPost.id).label("total_parsed_jobs"),
            func.coalesce(
                func.sum(
                    case(
                        (JobPost.should_score_similarity.is_(True), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("scorable_jobs"),
            func.coalesce(
                func.sum(
                    case(
                        (JobPost.extraction_status == "failed", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("failed_extractions"),
            func.coalesce(func.sum(JobPost.input_tokens), 0).label(
                "total_input_tokens"
            ),
            func.coalesce(func.sum(JobPost.output_tokens), 0).label(
                "total_output_tokens"
            ),
            func.coalesce(func.sum(JobPost.estimated_cost_usd), 0.0).label(
                "estimated_cost_usd"
            ),
            func.avg(JobPost.extraction_time_ms).label(
                "average_extraction_time_ms"
            ),
        ).where(JobPost.batch_id == str(batch_id))
    )
    row = result.one()
    total_parsed_jobs = int(row.total_parsed_jobs)
    if total_parsed_jobs == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="batch not found",
        )

    total_input_tokens = int(row.total_input_tokens)
    total_output_tokens = int(row.total_output_tokens)
    return BatchSummaryResponse(
        batch_id=batch_id,
        total_parsed_jobs=total_parsed_jobs,
        scorable_jobs=int(row.scorable_jobs),
        failed_extractions=int(row.failed_extractions),
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_input_tokens + total_output_tokens,
        estimated_cost_usd=float(row.estimated_cost_usd),
        average_extraction_time_ms=(
            None
            if row.average_extraction_time_ms is None
            else float(row.average_extraction_time_ms)
        ),
    )
