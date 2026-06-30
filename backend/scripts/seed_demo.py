"""Seed local demo data through the real backend processing pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.models import RoleProfile
from app.db.session import async_session_maker, init_db
from app.services.demo_loader import (
    DEMO_ROLE_TARGET_ROLE,
    load_mock_fixture_states,
    reset_mock_demo_data,
)
from app.services.job_processing_service import JobProcessingResult, process_job_state
from app.services.qdrant_service import QdrantService


REPOSITORY_ROOT = BACKEND_ROOT.parent
DEMO_FIXTURE_PATHS = (
    REPOSITORY_ROOT / "mock_data" / "demo_jobs.json",
    REPOSITORY_ROOT / "mock_data" / "messy_social_posts.json",
)
DEMO_ROLE_LEVEL = "intern"
DEMO_ROLE_LOCATION = "Ha Noi"
DEMO_ROLE_ACCEPT_REMOTE = True
DEMO_ROLE_SKILLS = ["python", "rag", "langchain", "fastapi", "qdrant"]
DEMO_ROLE_RESUME = (
    "Portfolio demo profile for an AI Engineer Intern focused on Python, "
    "RAG, LangChain, FastAPI, SQLite, and Qdrant."
)


@dataclass
class SeedSummary:
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    job_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def skipped_jobs(self) -> int:
        return self.skipped_exact_duplicates + self.skipped_dedup_key_duplicates

    @property
    def inserted_rows(self) -> int:
        return self.inserted_jobs + self.inserted_duplicate_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the local SQLite/Qdrant demo dataset from mock fixtures.",
        epilog=(
            "Post-seed demo mode uses persisted SQLite rows and local Qdrant vectors; "
            "it does not require Tavily, LLM extraction, URL fetching, or browser scraping. "
            "First-time seed generation requires local Qdrant and OpenAI embedding access."
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete only mock-owned demo rows/vectors before seeding.",
    )
    return parser.parse_args()


async def ensure_seed_dependencies(qdrant_service: QdrantService) -> None:
    api_key = settings.OPENAI_API_KEY.get_secret_value()
    if not api_key or api_key == "your-openai-api-key":
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. First-time demo seed requires "
            "OpenAI embedding access."
        )
    await qdrant_service.ensure_collection()


async def get_or_create_demo_role_profile(session: AsyncSession) -> RoleProfile:
    result = await session.execute(
        select(RoleProfile)
        .where(
            RoleProfile.target_role == DEMO_ROLE_TARGET_ROLE,
            RoleProfile.level == DEMO_ROLE_LEVEL,
            RoleProfile.location == DEMO_ROLE_LOCATION,
        )
        .order_by(RoleProfile.created_at.desc(), RoleProfile.id.desc())
        .limit(1)
    )
    role_profile = result.scalar_one_or_none()
    if role_profile is not None:
        return role_profile

    role_profile = RoleProfile(
        target_role=DEMO_ROLE_TARGET_ROLE,
        level=DEMO_ROLE_LEVEL,
        location=DEMO_ROLE_LOCATION,
        accept_remote=DEMO_ROLE_ACCEPT_REMOTE,
        skills=json.dumps(DEMO_ROLE_SKILLS),
        resume_text=DEMO_ROLE_RESUME,
    )
    session.add(role_profile)
    await session.commit()
    await session.refresh(role_profile)
    return role_profile


async def process_demo_states(
    session: AsyncSession,
    *,
    batch_id: str,
    role_profile_id: str,
    qdrant_service: QdrantService,
) -> tuple[SeedSummary, int, int]:
    states = load_mock_fixture_states(
        DEMO_FIXTURE_PATHS,
        batch_id=batch_id,
        role_profile_id=role_profile_id,
    )
    scorable_jobs = sum(
        1 for state in states if bool(state.get("should_score_similarity"))
    )
    need_review_social_jobs = len(states) - scorable_jobs
    summary = SeedSummary()

    for state in states:
        result = await process_job_state(
            session,
            state,
            qdrant_service=qdrant_service,
        )
        add_processing_result(summary, result)

    return summary, scorable_jobs, need_review_social_jobs


def add_processing_result(summary: SeedSummary, result: JobProcessingResult) -> None:
    summary.inserted_jobs += result.inserted_jobs
    summary.skipped_exact_duplicates += result.skipped_exact_duplicates
    summary.skipped_dedup_key_duplicates += result.skipped_dedup_key_duplicates
    summary.inserted_duplicate_metadata += result.inserted_duplicate_metadata
    summary.qdrant_upserted += result.qdrant_upserted
    summary.qdrant_synced = summary.qdrant_synced and result.qdrant_synced
    summary.job_ids.extend(result.job_ids)
    summary.warnings.extend(result.warnings)


def validate_seed_summary(
    summary: SeedSummary,
    *,
    scorable_jobs: int,
) -> None:
    if summary.skipped_jobs:
        return
    if summary.qdrant_upserted != scorable_jobs or not summary.qdrant_synced:
        raise RuntimeError(
            "Demo seed inserted SQLite rows but did not create all expected "
            "Qdrant vectors. Check local Qdrant and OpenAI embedding access."
        )


def print_seed_summary(
    summary: SeedSummary,
    *,
    role_profile: RoleProfile,
    scorable_jobs: int,
    need_review_social_jobs: int,
) -> None:
    print("Seed completed.")
    print(f"Role profile: {role_profile.target_role}")
    print(f"Inserted jobs: {summary.inserted_rows}")
    print(f"Scorable jobs: {scorable_jobs}")
    print(f"Need-review/social jobs: {need_review_social_jobs}")
    print(f"Local Qdrant vectors upserted: {summary.qdrant_upserted}")
    if summary.skipped_jobs:
        print(f"Skipped duplicate jobs: {summary.skipped_jobs}")
    for warning in summary.warnings:
        print(f"Warning: {warning}")


async def seed_demo(reset: bool) -> SeedSummary:
    await init_db()
    qdrant_service = QdrantService()
    await ensure_seed_dependencies(qdrant_service)

    async with async_session_maker() as session:
        if reset:
            await reset_mock_demo_data(session, qdrant_service=qdrant_service)

        role_profile = await get_or_create_demo_role_profile(session)
        batch_id = str(uuid4())
        summary, scorable_jobs, need_review_social_jobs = await process_demo_states(
            session,
            batch_id=batch_id,
            role_profile_id=role_profile.id,
            qdrant_service=qdrant_service,
        )
        validate_seed_summary(summary, scorable_jobs=scorable_jobs)
        print_seed_summary(
            summary,
            role_profile=role_profile,
            scorable_jobs=scorable_jobs,
            need_review_social_jobs=need_review_social_jobs,
        )
        return summary


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(seed_demo(reset=args.reset))
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
