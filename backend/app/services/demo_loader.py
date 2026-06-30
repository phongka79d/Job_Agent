"""Demo fixture loading and safe mock-data reset helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import (
    JobAgentState,
    JobPostExtract,
    score_placeholder_update,
    validate_extraction_status,
    validate_input_source,
    validate_jd_status,
    validate_parse_status,
    validate_source_platform_value,
)
from app.db.models import Application, JobPost, RoleProfile
from app.services.extraction_service import clean_text_content, compute_content_hash
from app.services.qdrant_service import QdrantService


MOCK_INPUT_SOURCE = "mock"
MOCK_SOURCE_PLATFORM = "mock"
DEMO_ROLE_TARGET_ROLE = "AI Engineer Intern"
SCORABLE_JD_STATUSES = frozenset(("full_jd", "partial_jd"))


class DemoFixtureError(ValueError):
    """Raised when demo fixture JSON cannot be converted safely."""


@dataclass(frozen=True)
class DemoResetResult:
    """Counts returned by the safe demo reset helper."""

    deleted_applications: int
    deleted_qdrant_vectors: int
    deleted_job_posts: int
    deleted_role_profiles: int


class MockJobFixture(BaseModel):
    """Validated mock JSON shape before conversion to JobAgentState."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    company: str | None = None
    location: str | None = None
    work_mode: str = "unknown"
    level: str = "unknown"
    employment_type: str = "unknown"
    salary: str | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    skills: list[str] = Field(default_factory=list)
    raw_text: str = Field(min_length=1)
    source_url: str | None = None
    jd_status: str
    parse_status: str
    extraction_status: str | None = None
    extraction_notes: str | None = None
    input_tokens: int | None = 0
    output_tokens: int | None = 0
    estimated_cost_usd: float | None = 0.0
    extraction_time_ms: int | None = 0

    @field_validator("jd_status")
    @classmethod
    def validate_fixture_jd_status(cls, value: str) -> str:
        return validate_jd_status(value)

    @field_validator("parse_status")
    @classmethod
    def validate_fixture_parse_status(cls, value: str) -> str:
        return validate_parse_status(value)

    @field_validator("extraction_status")
    @classmethod
    def validate_fixture_extraction_status(cls, value: str | None) -> str | None:
        return validate_extraction_status(value)


def load_mock_fixture_states(
    fixture_paths: Iterable[Path | str],
    *,
    batch_id: str,
    role_profile_id: str,
) -> list[JobAgentState]:
    """Load one or more mock JSON fixture files and return Plan 3 states."""

    states: list[JobAgentState] = []
    for fixture_path in fixture_paths:
        for item in load_mock_fixture_items(fixture_path):
            states.append(
                fixture_to_state(
                    item,
                    batch_id=batch_id,
                    role_profile_id=role_profile_id,
                )
            )
    return states


def load_mock_fixture_items(fixture_path: Path | str) -> list[MockJobFixture]:
    """Load and validate mock JSON fixture items from a local file."""

    path = Path(fixture_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DemoFixtureError(f"Unable to read mock fixture: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DemoFixtureError(f"Invalid mock fixture JSON: {path}") from exc

    if not isinstance(payload, list):
        raise DemoFixtureError(f"Mock fixture must contain a JSON list: {path}")

    try:
        return [MockJobFixture.model_validate(item) for item in payload]
    except ValueError as exc:
        raise DemoFixtureError(f"Invalid mock fixture item in {path}: {exc}") from exc


def fixture_to_state(
    fixture: MockJobFixture | dict[str, Any],
    *,
    batch_id: str,
    role_profile_id: str,
) -> JobAgentState:
    """Convert a validated mock fixture to a complete Plan 3 JobAgentState."""

    item = (
        fixture
        if isinstance(fixture, MockJobFixture)
        else MockJobFixture.model_validate(fixture)
    )
    input_source = validate_input_source(MOCK_INPUT_SOURCE)
    source_platform = validate_source_platform_value(MOCK_SOURCE_PLATFORM)

    clean_text = clean_text_content(item.raw_text)
    if clean_text is None:
        raise DemoFixtureError("Mock fixture raw_text must produce non-empty clean_text")

    should_score_similarity = item.jd_status in SCORABLE_JD_STATUSES
    extracted_job = JobPostExtract(
        title=item.title,
        company=item.company,
        location=item.location,
        work_mode=item.work_mode,
        level=item.level,
        employment_type=item.employment_type,
        salary=item.salary,
        responsibilities=item.responsibilities,
        requirements=item.requirements,
        skills=item.skills,
        source_url=item.source_url,
        source_platform=source_platform,
        jd_status=item.jd_status,
        should_score_similarity=should_score_similarity,
        extraction_notes=item.extraction_notes,
    ).model_dump()

    base_state: JobAgentState = {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": input_source,
    }
    return {
        **score_placeholder_update(base_state),
        "source_url": item.source_url,
        "raw_text": item.raw_text,
        "clean_text": clean_text,
        "raw_content_hash": compute_content_hash(clean_text),
        "parse_status": item.parse_status,
        "extracted_job": extracted_job,
        "jd_status": item.jd_status,
        "should_score_similarity": should_score_similarity,
        "extraction_status": item.extraction_status,
        "error_reason": None,
        "user_warning": None,
        "input_tokens": item.input_tokens,
        "output_tokens": item.output_tokens,
        "estimated_cost_usd": item.estimated_cost_usd,
        "extraction_time_ms": item.extraction_time_ms,
    }


async def reset_mock_demo_data(
    session: AsyncSession,
    *,
    preserve_role_profile_id: str | None = None,
    qdrant_service: QdrantService | None = None,
) -> DemoResetResult:
    """Delete only mock-owned rows, matching vectors, and safe demo profile rows."""

    mock_job_ids = await _load_mock_job_ids(session)
    deleted_applications = 0
    deleted_qdrant_vectors = 0
    deleted_job_posts = 0
    deleted_role_profiles = 0

    if mock_job_ids:
        applications_result = await session.execute(
            delete(Application).where(Application.job_post_id.in_(mock_job_ids))
        )
        deleted_applications = applications_result.rowcount or 0

        vector_service = qdrant_service or QdrantService()
        for job_id in mock_job_ids:
            await vector_service.delete_point_if_exists(job_id)
            deleted_qdrant_vectors += 1

        job_posts_result = await session.execute(
            delete(JobPost).where(JobPost.id.in_(mock_job_ids))
        )
        deleted_job_posts = job_posts_result.rowcount or 0
        await session.flush()

    deleted_role_profiles = await _delete_safe_demo_role_profiles(
        session,
        preserve_role_profile_id=preserve_role_profile_id,
    )
    await session.commit()

    return DemoResetResult(
        deleted_applications=deleted_applications,
        deleted_qdrant_vectors=deleted_qdrant_vectors,
        deleted_job_posts=deleted_job_posts,
        deleted_role_profiles=deleted_role_profiles,
    )


async def _load_mock_job_ids(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(JobPost.id).where(JobPost.source_platform == MOCK_SOURCE_PLATFORM)
    )
    return list(result.scalars())


async def _delete_safe_demo_role_profiles(
    session: AsyncSession,
    *,
    preserve_role_profile_id: str | None,
) -> int:
    result = await session.execute(
        select(RoleProfile).where(RoleProfile.target_role == DEMO_ROLE_TARGET_ROLE)
    )
    deleted = 0
    for role_profile in result.scalars():
        if role_profile.id == preserve_role_profile_id:
            continue
        if await _has_non_mock_jobs(session, role_profile.id):
            continue
        await session.delete(role_profile)
        deleted += 1
    return deleted


async def _has_non_mock_jobs(session: AsyncSession, role_profile_id: str) -> bool:
    result = await session.execute(
        select(JobPost.id)
        .where(
            JobPost.role_profile_id == role_profile_id,
            or_(
                JobPost.source_platform.is_(None),
                JobPost.source_platform != MOCK_SOURCE_PLATFORM,
            ),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
