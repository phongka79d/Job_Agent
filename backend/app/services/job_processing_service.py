"""
Job Processing Service.

Provides mapping and persistence utilities to convert Plan 2 extraction state
into SQLite job payloads, checking validation requirements, and managing
the conversion lifecycle without external OpenAI or Qdrant calls.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants
from app.db.models import JobPost, RoleProfile
from app.services.dedup_service import build_dedup_key, decide_duplicate_action
from app.services.scoring_service import build_embedding_text
from app.agents.schemas import JobAgentState


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
    session: AsyncSession, state: JobAgentState
) -> JobProcessingResult:
    """
    Orchestrate the SQLite-first persistence and deduplication pipeline.

    Validates state, maps to a JobPost ORM model, checks for exact and dedup-key duplicates,
    handles duplicate metadata rows according to policy, catches IntegrityErrors,
    and returns a JobProcessingResult without Qdrant/embedding integration.
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

                # Reset scoring/score fields to None
                job_post.embedding_similarity = None
                job_post.skill_overlap_score = None
                job_post.location_match_score = None
                job_post.level_match_score = None
                job_post.base_score = None
                job_post.jd_confidence_multiplier = None
                job_post.final_score = None
                job_post.final_score_percent = None

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

    return JobProcessingResult(
        inserted_jobs=1, job_ids=[job_post.id], warnings=warnings
    )
