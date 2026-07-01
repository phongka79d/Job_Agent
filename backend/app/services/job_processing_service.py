"""
Job Processing Service.

Provides mapping and persistence utilities to convert Plan 2 extraction state
into SQLite job payloads, checking validation requirements, and managing
the conversion lifecycle without external OpenAI or Qdrant calls.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants
from app.db.models import Application, JobPost, ProfileDocumentChunk, RoleProfile
from app.services.dedup_service import build_dedup_key, decide_duplicate_action
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.scoring_service import (
    build_embedding_text,
    build_role_query_text,
    build_role_query_text_with_cv_evidence,
    calculate_base_score,
    calculate_final_scores,
    calculate_level_score,
    calculate_location_score,
    calculate_skill_overlap_score,
    get_jd_confidence_multiplier,
)
from app.agents.schemas import JobAgentState

logger = logging.getLogger(__name__)
SCORING_FAILURE_REASON = "Scoring unavailable after SQLite persistence"
QDRANT_SIMILARITY_UNAVAILABLE_REASON = "Qdrant similarity unavailable for newly upserted job"
MANUAL_TRACKED_STATUS_TARGETS = (
    "applied",
    "interview",
    "rejected",
    "offer",
)


class InvalidStatusTransition(ValueError):
    """Raised when a job status mutation is not allowed."""


def _build_allowed_status_transitions() -> dict[str, frozenset[str]]:
    job_statuses = set(constants.JOB_STATUSES)
    application_statuses = set(constants.APPLICATION_STATUSES)
    tracked_statuses = set(constants.TRACKED_JOB_STATUSES)

    transitions = {
        "pending_review": frozenset({"saved", "ignored"}),
        "saved": frozenset({"applied", "rejected"}),
        "applied": frozenset({"interview", "rejected"}),
        "interview": frozenset({"rejected", "offer"}),
        "rejected": frozenset(),
        "offer": frozenset(),
        "ignored": frozenset(),
    }

    unknown_sources = set(transitions) - job_statuses
    unknown_targets = set().union(*transitions.values()) - job_statuses
    if unknown_sources or unknown_targets:
        raise ValueError(
            "ALLOWED_STATUS_TRANSITIONS contains statuses outside JOB_STATUSES"
        )

    manual_targets = set(MANUAL_TRACKED_STATUS_TARGETS)
    if not manual_targets <= application_statuses:
        raise ValueError("Manual status targets must be APPLICATION_STATUSES")
    if not manual_targets <= tracked_statuses:
        raise ValueError("Manual status targets must be TRACKED_JOB_STATUSES")
    if not application_statuses <= job_statuses:
        raise ValueError("APPLICATION_STATUSES must be valid JOB_STATUSES")

    return transitions


ALLOWED_STATUS_TRANSITIONS = _build_allowed_status_transitions()


@dataclass
class JobProcessingResult:
    """
    Result of the job processing pipeline execution.
    Matches the schema required by Plan 3.
    """
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    job_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _reset_score_fields(job_post: JobPost) -> None:
    job_post.embedding_similarity = None
    job_post.skill_overlap_score = None
    job_post.location_match_score = None
    job_post.level_match_score = None
    job_post.base_score = None
    job_post.jd_confidence_multiplier = None
    job_post.final_score = None
    job_post.final_score_percent = None


def _append_error_reason(existing: str | None, reason: str) -> str:
    if not existing:
        return reason
    if reason in existing:
        return existing
    return f"{existing}; {reason}"


def _parse_json_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except ValueError:
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return []


async def _load_active_cv_text_for_scoring(
    session: AsyncSession,
    role_profile: RoleProfile,
    *,
    max_chunks: int = 12,
) -> str | None:
    if role_profile.active_cv_document_id is None or role_profile.active_cv_version_id is None:
        return None
    result = await session.execute(
        select(ProfileDocumentChunk)
        .where(ProfileDocumentChunk.role_profile_id == role_profile.id)
        .where(ProfileDocumentChunk.document_id == role_profile.active_cv_document_id)
        .where(ProfileDocumentChunk.version_id == role_profile.active_cv_version_id)
        .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
        .limit(max_chunks)
    )
    chunks = list(result.scalars())
    if not chunks:
        return None
    return "\n\n".join(chunk.text for chunk in chunks)


async def _score_committed_job(
    session: AsyncSession,
    job_post: JobPost,
    role_profile: RoleProfile,
    embedding_service: Any,
    qdrant_service: Any,
) -> tuple[int, bool]:
    active_cv_text = await _load_active_cv_text_for_scoring(session, role_profile)
    role_query_text = build_role_query_text_with_cv_evidence(role_profile, active_cv_text)
    job_embedding_text = job_post.embedding_text or build_embedding_text(job_post)
    job_post.embedding_text = job_embedding_text

    try:
        role_vector = await embedding_service.embed_text(role_query_text)
        job_vector = await embedding_service.embed_text(job_embedding_text)
        upserted = await qdrant_service.upsert_scorable_job(job_post, job_vector)
        if not upserted:
            raise RuntimeError("Qdrant skipped scorable job upsert")

        embedding_similarity = await qdrant_service.query_job_similarity(
            role_vector,
            role_profile.id,
            job_post.id,
        )
    except Exception as exc:
        logger.warning(
            "Scorable job scoring failed after SQLite commit",
            extra={"job_id": job_post.id, "error_type": exc.__class__.__name__},
        )
        _reset_score_fields(job_post)
        job_post.error_reason = _append_error_reason(
            job_post.error_reason,
            SCORING_FAILURE_REASON,
        )
        await session.commit()
        return 0, False

    if embedding_similarity is None:
        _reset_score_fields(job_post)
        job_post.error_reason = _append_error_reason(
            job_post.error_reason,
            QDRANT_SIMILARITY_UNAVAILABLE_REASON,
        )
        await session.commit()
        return 1, False

    skill_overlap_score = calculate_skill_overlap_score(
        _parse_json_list(role_profile.skills),
        _parse_json_list(job_post.skills),
    )
    location_match_score = calculate_location_score(
        role_profile.location,
        job_post.location,
        role_profile.accept_remote,
        job_post.work_mode,
    )
    level_match_score = calculate_level_score(role_profile.level, job_post.level)
    jd_confidence_multiplier = get_jd_confidence_multiplier(job_post.jd_status)
    base_score = calculate_base_score(
        embedding_similarity,
        skill_overlap_score,
        location_match_score,
        level_match_score,
    )
    final_score, final_score_percent = calculate_final_scores(
        base_score,
        jd_confidence_multiplier,
    )

    job_post.embedding_similarity = embedding_similarity
    job_post.skill_overlap_score = skill_overlap_score
    job_post.location_match_score = location_match_score
    job_post.level_match_score = level_match_score
    job_post.base_score = base_score
    job_post.jd_confidence_multiplier = jd_confidence_multiplier
    job_post.final_score = final_score
    job_post.final_score_percent = final_score_percent
    await session.commit()
    return 1, True


def validate_extraction_state(state: Dict[str, Any]) -> None:
    """
    Validate required state keys and input source value.
    Raises ValueError if validation fails.
    """
    for key in ["batch_id", "role_profile_id", "input_source"]:
        if key not in state or not state[key]:
            raise ValueError(f"Missing required state key: {key}")

    if state["input_source"] not in constants.INPUT_SOURCES:
        raise ValueError(f"Invalid input_source: {state['input_source']}")

    # If parse_status indicates success, we expect extracted_job to be present
    parse_status = state.get("parse_status")
    if parse_status == "success":
        if "extracted_job" not in state or state["extracted_job"] is None:
            raise ValueError("extracted_job is required when parse_status is 'success'")


async def load_role_profile(db: AsyncSession, role_profile_id: str) -> RoleProfile:
    """
    Load the RoleProfile from SQLite by role_profile_id.
    Raises ValueError if the profile does not exist.
    """
    stmt = select(RoleProfile).where(RoleProfile.id == role_profile_id)
    result = await db.execute(stmt)
    role_profile = result.scalar_one_or_none()
    if not role_profile:
        raise ValueError(f"RoleProfile with id {role_profile_id} does not exist.")
    return role_profile


async def load_job_post(session: AsyncSession, job_id: str) -> JobPost:
    """Load a JobPost row by ID."""
    stmt = select(JobPost).where(JobPost.id == job_id)
    result = await session.execute(stmt)
    job_post = result.scalar_one_or_none()
    if not job_post:
        raise ValueError(f"JobPost with id {job_id} does not exist.")
    return job_post


def _validate_status_transition(current_status: str | None, next_status: str) -> None:
    if current_status not in ALLOWED_STATUS_TRANSITIONS:
        raise InvalidStatusTransition(
            f"Cannot transition from unknown status {current_status!r} to {next_status!r}."
        )
    if next_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise InvalidStatusTransition(
            f"Cannot transition job status from {current_status!r} to {next_status!r}."
        )


async def _load_application_for_job(
    session: AsyncSession,
    job_id: str,
) -> Application | None:
    stmt = select(Application).where(Application.job_post_id == job_id).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _sync_application_row(
    session: AsyncSession,
    job_id: str,
    status: str,
) -> None:
    application = await _load_application_for_job(session, job_id)
    if application:
        application.status = status
        return

    applied_at = datetime.now(timezone.utc) if status == "applied" else None
    session.add(
        Application(
            job_post_id=job_id,
            status=status,
            applied_at=applied_at,
        )
    )


async def approve_job(
    session: AsyncSession,
    job_id: str,
    qdrant_service: Any | None = None,
) -> JobPost:
    """Validate pending_review -> saved, update SQLite, then update Qdrant payload."""
    job_post = await load_job_post(session, job_id)
    _validate_status_transition(job_post.status, "saved")

    job_post.status = "saved"
    await session.commit()
    await (qdrant_service or QdrantService()).update_job_status_payload(job_id, "saved")
    return job_post


async def reject_job(
    session: AsyncSession,
    job_id: str,
    qdrant_service: Any | None = None,
) -> JobPost:
    """Validate pending_review -> ignored, update SQLite, then delete the Qdrant point."""
    job_post = await load_job_post(session, job_id)
    _validate_status_transition(job_post.status, "ignored")

    job_post.status = "ignored"
    await session.commit()
    await (qdrant_service or QdrantService()).delete_point_if_exists(job_id)
    return job_post


async def update_job_status(
    session: AsyncSession,
    job_id: str,
    status: str,
    qdrant_service: Any | None = None,
) -> JobPost:
    """Validate manual tracked transitions, update SQLite/applications, then update Qdrant."""
    if status not in MANUAL_TRACKED_STATUS_TARGETS:
        raise InvalidStatusTransition(
            f"Manual status update target must be one of {MANUAL_TRACKED_STATUS_TARGETS!r}."
        )

    job_post = await load_job_post(session, job_id)
    _validate_status_transition(job_post.status, status)

    job_post.status = status
    await _sync_application_row(session, job_id, status)
    await session.commit()
    await (qdrant_service or QdrantService()).update_job_status_payload(job_id, status)
    return job_post


def map_state_to_job_post(state: Dict[str, Any], role_profile: RoleProfile) -> JobPost:
    """
    Convert a JobAgentState and loaded RoleProfile into a JobPost database model instance.
    Sets default status to pending_review, computes the deduplication key, serializes skills,
    and derives whether the job should be similarity-scored.
    """
    validate_extraction_state(state)

    extracted_job = state.get("extracted_job") or {}

    # Extract job fields
    title = extracted_job.get("title")
    company = extracted_job.get("company")
    location = extracted_job.get("location")
    work_mode = extracted_job.get("work_mode")
    level = extracted_job.get("level")
    employment_type = extracted_job.get("employment_type")
    salary = extracted_job.get("salary")
    responsibilities = extracted_job.get("responsibilities")
    requirements = extracted_job.get("requirements")

    # Serialize skills to JSON string consistent with Phase 1
    skills_raw = extracted_job.get("skills")
    skills_str = None
    if skills_raw is not None:
        if isinstance(skills_raw, list):
            skills_str = json.dumps(skills_raw)
        elif isinstance(skills_raw, str):
            try:
                # Verify if it is already a valid JSON string
                json.loads(skills_raw)
                skills_str = skills_raw
            except ValueError:
                # Assume comma-separated values
                skills_str = json.dumps([s.strip() for s in skills_raw.split(",") if s.strip()])

    # Determine URL and Platform
    source_url = extracted_job.get("source_url") or state.get("source_url")
    
    # Try to map input_source to source_platform
    from app.agents.schemas import map_input_source_to_source_platform
    try:
        source_platform = map_input_source_to_source_platform(state["input_source"])
    except Exception:
        source_platform = extracted_job.get("source_platform") or state["input_source"]

    jd_status = extracted_job.get("jd_status") or state.get("jd_status") or "unclear"

    # Derive should_score_similarity (only full_jd and partial_jd are scorable)
    should_score_similarity = jd_status in ("full_jd", "partial_jd")

    # Build embedding text if scorable
    embedding_text = None
    if should_score_similarity:
        embedding_text = build_embedding_text(extracted_job)

    # Compute dedup key
    dedup_key = build_dedup_key(company, title)

    # Build JobPost ORM model
    job_post = JobPost(
        batch_id=state["batch_id"],
        role_profile_id=role_profile.id,
        title=title,
        company=company,
        location=location,
        work_mode=work_mode,
        level=level,
        employment_type=employment_type,
        salary=salary,
        responsibilities=responsibilities,
        requirements=requirements,
        skills=skills_str,
        source_url=source_url,
        source_platform=source_platform,
        parse_status=state.get("parse_status"),
        raw_content_hash=state.get("raw_content_hash"),
        dedup_key=dedup_key,
        jd_status=jd_status,
        extraction_status=state.get("extraction_status"),
        error_reason=state.get("error_reason"),
        should_score_similarity=should_score_similarity,
        embedding_text=embedding_text,
        
        # Keep all scoring fields null initially
        embedding_similarity=None,
        skill_overlap_score=None,
        location_match_score=None,
        level_match_score=None,
        base_score=None,
        jd_confidence_multiplier=None,
        final_score=None,
        final_score_percent=None,
        
        # All non-skipped, non-duplicate-metadata parsed jobs save as pending_review
        status="pending_review",
        
        # Token and cost metadata
        input_tokens=state.get("input_tokens"),
        output_tokens=state.get("output_tokens"),
        estimated_cost_usd=state.get("estimated_cost_usd"),
        extraction_time_ms=state.get("extraction_time_ms"),
    )

    return job_post


async def process_job_state(
    session: AsyncSession,
    state: JobAgentState,
    embedding_service: Any | None = None,
    qdrant_service: Any | None = None,
) -> JobProcessingResult:
    """
    Orchestrate the SQLite-first persistence and deduplication pipeline.

    Validates state, maps to a JobPost ORM model, checks for exact and dedup-key duplicates,
    handles duplicate metadata rows according to policy, catches IntegrityErrors,
    and runs scorable embedding/Qdrant scoring only after the SQLite row commits.
    """
    # 2.a. Validate the extraction state
    validate_extraction_state(state)

    # 2.b. Load the target role profile from SQLite
    role_profile = await load_role_profile(session, state["role_profile_id"])

    # Extract warnings
    warnings = []
    user_warning = state.get("user_warning")
    if user_warning:
        warnings.append(user_warning)

    # 2.c & 2.d. Convert state to JobPost model payload (dedup_key is computed internally)
    job_post = map_state_to_job_post(state, role_profile)

    # 2.e. Query SQLite database for exact duplicates by raw_content_hash.
    raw_hash = job_post.raw_content_hash
    if raw_hash:
        stmt = select(JobPost).where(JobPost.raw_content_hash == raw_hash)
        result = await session.execute(stmt)
        existing_job = result.scalars().first()
        if existing_job:
            return JobProcessingResult(
                skipped_exact_duplicates=1,
                job_ids=[existing_job.id],
                warnings=warnings,
            )

    # 2.f. Check duplicate by dedup_key (only if not None)
    dedup_key = job_post.dedup_key
    if dedup_key:
        # Query SQLite for the latest job with this dedup_key
        stmt = (
            select(JobPost)
            .where(JobPost.dedup_key == dedup_key)
            .order_by(JobPost.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        existing_job = result.scalars().first()

        # 2.g. Evaluate decide_duplicate_action
        if existing_job:
            action = decide_duplicate_action(existing_job.status)
            if action == "skip_duplicate":
                return JobProcessingResult(
                    skipped_dedup_key_duplicates=1,
                    job_ids=[existing_job.id],
                    warnings=warnings,
                )
            elif action == "mark_new_as_duplicate_ignored":
                # Create duplicate metadata JobPost
                job_post.status = "ignored"
                job_post.duplicate_of_job_id = existing_job.id
                job_post.should_score_similarity = False
                job_post.embedding_text = None
                _reset_score_fields(job_post)

                try:
                    session.add(job_post)
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    # Catch raw_content_hash IntegrityError, roll back, fetch the existing ID, and return
                    if raw_hash:
                        stmt_existing = select(JobPost).where(
                            JobPost.raw_content_hash == raw_hash
                        )
                        res_existing = await session.execute(stmt_existing)
                        existing_job_hash = res_existing.scalars().first()
                        existing_id = (
                            existing_job_hash.id if existing_job_hash else None
                        )
                    else:
                        existing_id = None
                    return JobProcessingResult(
                        skipped_exact_duplicates=1,
                        job_ids=[existing_id] if existing_id else [],
                        warnings=warnings,
                    )

                return JobProcessingResult(
                    inserted_duplicate_metadata=1,
                    job_ids=[job_post.id],
                    warnings=warnings,
                )

    # 2.h. If not a duplicate at all, add job_post
    try:
        session.add(job_post)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # Catch IntegrityError from unique constraints
        if raw_hash:
            stmt_existing = select(JobPost).where(
                JobPost.raw_content_hash == raw_hash
            )
            res_existing = await session.execute(stmt_existing)
            existing_job_hash = res_existing.scalars().first()
            existing_id = existing_job_hash.id if existing_job_hash else None
        else:
            existing_id = None
        return JobProcessingResult(
            skipped_exact_duplicates=1,
            job_ids=[existing_id] if existing_id else [],
            warnings=warnings,
        )

    qdrant_upserted = 0
    qdrant_synced = True
    if job_post.should_score_similarity:
        qdrant_upserted, qdrant_synced = await _score_committed_job(
            session,
            job_post,
            role_profile,
            embedding_service or EmbeddingService(),
            qdrant_service or QdrantService(),
        )

    return JobProcessingResult(
        inserted_jobs=1,
        qdrant_upserted=qdrant_upserted,
        qdrant_synced=qdrant_synced,
        job_ids=[job_post.id],
        warnings=warnings,
    )
