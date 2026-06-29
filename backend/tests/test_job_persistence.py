import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import JobAgentState
from app.db.models import JobPost
from app.services.job_processing_service import (
    QDRANT_SIMILARITY_UNAVAILABLE_REASON,
    SCORING_FAILURE_REASON,
    process_job_state,
)
from tests.conftest import FakeEmbeddingService, FakeQdrantService


def make_state(
    role_profile_id: str,
    *,
    raw_content_hash: str,
    title: str | None = "Backend Engineer",
    company: str | None = "Acme",
    jd_status: str = "full_jd",
    user_warning: str | None = None,
) -> JobAgentState:
    state: JobAgentState = {
        "batch_id": "batch-persistence",
        "role_profile_id": role_profile_id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": raw_content_hash,
        "jd_status": jd_status,
        "extracted_job": {
            "title": title,
            "company": company,
            "location": "San Francisco",
            "work_mode": "hybrid",
            "level": "junior",
            "responsibilities": "Build APIs",
            "requirements": "Python and FastAPI",
            "skills": ["python", "fastapi"],
            "jd_status": jd_status,
        },
    }
    if user_warning:
        state["user_warning"] = user_warning
    return state


async def count_jobs(db_session: AsyncSession) -> int:
    return await db_session.scalar(select(func.count()).select_from(JobPost))


@pytest.mark.asyncio
async def test_exact_duplicate_skips_insert_and_provider_calls(
    db_session: AsyncSession,
    test_role_profile,
):
    state = make_state(test_role_profile.id, raw_content_hash="hash-exact")

    first = await process_job_state(
        db_session,
        state,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )
    embedding_service = FakeEmbeddingService()
    qdrant_service = FakeQdrantService()

    second = await process_job_state(
        db_session,
        state,
        embedding_service,
        qdrant_service,
    )

    assert first.inserted_jobs == 1
    assert second.inserted_jobs == 0
    assert second.skipped_exact_duplicates == 1
    assert second.job_ids == first.job_ids
    assert await count_jobs(db_session) == 1
    assert embedding_service.calls == []
    assert qdrant_service.upserted_job_ids == []
    assert qdrant_service.queried_job_ids == []


@pytest.mark.asyncio
async def test_pending_review_dedup_key_duplicate_skips_insert_and_provider_calls(
    db_session: AsyncSession,
    test_role_profile,
):
    first_state = make_state(test_role_profile.id, raw_content_hash="hash-pending-1")
    second_state = make_state(test_role_profile.id, raw_content_hash="hash-pending-2")

    first = await process_job_state(
        db_session,
        first_state,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )
    embedding_service = FakeEmbeddingService()
    qdrant_service = FakeQdrantService()

    second = await process_job_state(
        db_session,
        second_state,
        embedding_service,
        qdrant_service,
    )

    assert second.inserted_jobs == 0
    assert second.skipped_dedup_key_duplicates == 1
    assert second.job_ids == first.job_ids
    assert await count_jobs(db_session) == 1
    assert embedding_service.calls == []
    assert qdrant_service.upserted_job_ids == []


@pytest.mark.asyncio
async def test_tracked_dedup_key_duplicate_inserts_ignored_metadata_without_qdrant(
    db_session: AsyncSession,
    test_role_profile,
):
    first_state = make_state(test_role_profile.id, raw_content_hash="hash-tracked-1")
    second_state = make_state(test_role_profile.id, raw_content_hash="hash-tracked-2")
    first = await process_job_state(
        db_session,
        first_state,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )
    job = await db_session.get(JobPost, first.job_ids[0])
    job.status = "saved"
    await db_session.commit()

    embedding_service = FakeEmbeddingService()
    qdrant_service = FakeQdrantService()
    second = await process_job_state(
        db_session,
        second_state,
        embedding_service,
        qdrant_service,
    )

    assert second.inserted_duplicate_metadata == 1
    assert second.inserted_jobs == 0
    assert await count_jobs(db_session) == 2
    duplicate = await db_session.get(JobPost, second.job_ids[0])
    assert duplicate.status == "ignored"
    assert duplicate.duplicate_of_job_id == first.job_ids[0]
    assert duplicate.should_score_similarity is False
    assert duplicate.embedding_text is None
    assert duplicate.final_score is None
    assert embedding_service.calls == []
    assert qdrant_service.upserted_job_ids == []


@pytest.mark.asyncio
async def test_ignored_dedup_key_duplicate_skips_insert(
    db_session: AsyncSession,
    test_role_profile,
):
    first_state = make_state(test_role_profile.id, raw_content_hash="hash-ignored-1")
    second_state = make_state(test_role_profile.id, raw_content_hash="hash-ignored-2")
    first = await process_job_state(
        db_session,
        first_state,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )
    job = await db_session.get(JobPost, first.job_ids[0])
    job.status = "ignored"
    await db_session.commit()

    second = await process_job_state(
        db_session,
        second_state,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )

    assert second.skipped_dedup_key_duplicates == 1
    assert second.job_ids == first.job_ids
    assert await count_jobs(db_session) == 1


@pytest.mark.asyncio
async def test_missing_company_or_title_has_null_dedup_key_and_does_not_collide(
    db_session: AsyncSession,
    test_role_profile,
):
    missing_company = make_state(
        test_role_profile.id,
        raw_content_hash="hash-missing-company",
        company=None,
        jd_status="unclear",
    )
    missing_title = make_state(
        test_role_profile.id,
        raw_content_hash="hash-missing-title",
        title=None,
        jd_status="unclear",
    )

    first = await process_job_state(
        db_session,
        missing_company,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )
    second = await process_job_state(
        db_session,
        missing_title,
        FakeEmbeddingService(),
        FakeQdrantService(),
    )

    assert first.inserted_jobs == 1
    assert second.inserted_jobs == 1
    assert first.job_ids != second.job_ids
    result = await db_session.execute(select(JobPost).order_by(JobPost.created_at))
    jobs = result.scalars().all()
    assert [job.dedup_key for job in jobs] == [None, None]
    assert [job.status for job in jobs] == ["pending_review", "pending_review"]


@pytest.mark.asyncio
async def test_scorable_job_commits_before_embedding_and_qdrant(
    db_session: AsyncSession,
    test_role_profile,
):
    embedding_service = FakeEmbeddingService(db_session)
    qdrant_service = FakeQdrantService(db_session=db_session)

    result = await process_job_state(
        db_session,
        make_state(test_role_profile.id, raw_content_hash="hash-scorable-order"),
        embedding_service,
        qdrant_service,
    )

    assert result.inserted_jobs == 1
    assert embedding_service.row_count_at_first_call == 1
    assert qdrant_service.row_count_at_first_upsert == 1
    assert qdrant_service.upserted_job_ids == result.job_ids


@pytest.mark.asyncio
async def test_non_scorable_job_commits_with_null_scores_and_no_provider_calls(
    db_session: AsyncSession,
    test_role_profile,
):
    embedding_service = FakeEmbeddingService()
    qdrant_service = FakeQdrantService()

    result = await process_job_state(
        db_session,
        make_state(
            test_role_profile.id,
            raw_content_hash="hash-non-scorable",
            jd_status="no_jd",
        ),
        embedding_service,
        qdrant_service,
    )

    job = await db_session.get(JobPost, result.job_ids[0])
    assert result.inserted_jobs == 1
    assert job.status == "pending_review"
    assert job.should_score_similarity is False
    assert job.embedding_text is None
    assert job.embedding_similarity is None
    assert job.final_score is None
    assert embedding_service.calls == []
    assert qdrant_service.upserted_job_ids == []
    assert qdrant_service.queried_job_ids == []


@pytest.mark.asyncio
async def test_embedding_failure_after_commit_leaves_pending_review_null_scores(
    db_session: AsyncSession,
    test_role_profile,
):
    embedding_service = FakeEmbeddingService(db_session, fail=True)
    qdrant_service = FakeQdrantService()

    result = await process_job_state(
        db_session,
        make_state(test_role_profile.id, raw_content_hash="hash-embedding-failure"),
        embedding_service,
        qdrant_service,
    )

    job = await db_session.get(JobPost, result.job_ids[0])
    assert result.inserted_jobs == 1
    assert result.qdrant_upserted == 0
    assert result.qdrant_synced is False
    assert embedding_service.row_count_at_first_call == 1
    assert job.status == "pending_review"
    assert job.embedding_similarity is None
    assert job.final_score is None
    assert job.error_reason == SCORING_FAILURE_REASON
    assert "fake provider failure" not in job.error_reason
    assert qdrant_service.upserted_job_ids == []


@pytest.mark.asyncio
async def test_qdrant_similarity_unavailable_keeps_committed_row_with_null_scores(
    db_session: AsyncSession,
    test_role_profile,
):
    result = await process_job_state(
        db_session,
        make_state(test_role_profile.id, raw_content_hash="hash-qdrant-unavailable"),
        FakeEmbeddingService(),
        FakeQdrantService(similarity=None),
    )

    job = await db_session.get(JobPost, result.job_ids[0])
    assert result.inserted_jobs == 1
    assert result.qdrant_upserted == 1
    assert result.qdrant_synced is False
    assert job.status == "pending_review"
    assert job.embedding_similarity is None
    assert job.final_score is None
    assert job.error_reason == QDRANT_SIMILARITY_UNAVAILABLE_REASON


@pytest.mark.asyncio
async def test_job_processing_result_warnings_include_user_warning(
    db_session: AsyncSession,
    test_role_profile,
):
    result = await process_job_state(
        db_session,
        make_state(
            test_role_profile.id,
            raw_content_hash="hash-warning",
            user_warning="Needs manual review.",
            jd_status="unclear",
        ),
        FakeEmbeddingService(),
        FakeQdrantService(),
    )

    assert result.warnings == ["Needs manual review."]
