import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, func, select

from app.db.models import Application, Base, RoleProfile, JobPost
from app.agents.schemas import JobAgentState
from app.services.job_processing_service import (
    ALLOWED_STATUS_TRANSITIONS,
    InvalidStatusTransition,
    approve_job,
    process_job_state,
    reject_job,
    update_job_status,
)


class FakeEmbeddingService:
    def __init__(self, db_session: AsyncSession | None = None):
        self.calls: list[str] = []
        self.db_session = db_session
        self.row_count_at_first_call: int | None = None

    async def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.db_session and self.row_count_at_first_call is None:
            result = await self.db_session.execute(select(JobPost))
            self.row_count_at_first_call = len(result.scalars().all())
        return [1.0, 0.0, 0.0]


class FakeQdrantService:
    def __init__(self, similarity: float | None = 0.8):
        self.similarity = similarity
        self.upserted_job_ids: list[str] = []
        self.queried_job_ids: list[str] = []
        self.status_payload_updates: list[tuple[str, str]] = []
        self.deleted_job_ids: list[str] = []

    async def upsert_scorable_job(self, job: JobPost, vector: list[float]) -> bool:
        self.upserted_job_ids.append(job.id)
        assert job.status == "pending_review"
        return True

    async def query_job_similarity(
        self,
        query_vector: list[float],
        role_profile_id: str,
        job_id: str,
    ) -> float | None:
        self.queried_job_ids.append(job_id)
        return self.similarity

    async def update_job_status_payload(self, job_id: str, status: str) -> None:
        self.status_payload_updates.append((job_id, status))

    async def delete_point_if_exists(self, job_id: str) -> None:
        self.deleted_job_ids.append(job_id)


@pytest_asyncio.fixture
async def db_session():
    # Use in-memory SQLite for isolated test environment
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_role_profile(db_session: AsyncSession):
    # Insert a dummy RoleProfile
    profile = RoleProfile(
        id="rp-test-id",
        target_role="Software Engineer",
        level="junior",
        location="San Francisco",
        accept_remote=True,
        skills='["python", "fastapi"]',
        resume_text="Experienced developer",
    )
    db_session.add(profile)
    await db_session.commit()
    return profile


async def create_job_post(
    db_session: AsyncSession,
    role_profile: RoleProfile,
    status: str,
) -> JobPost:
    job_post = JobPost(
        batch_id="batch-status",
        role_profile_id=role_profile.id,
        title="Backend Engineer",
        company="Acme",
        jd_status="full_jd",
        source_platform="manual_text",
        should_score_similarity=True,
        status=status,
    )
    db_session.add(job_post)
    await db_session.commit()
    return job_post


@pytest.mark.asyncio
async def test_process_job_state_new_insert(db_session: AsyncSession, test_role_profile):
    embedding_service = FakeEmbeddingService(db_session)
    qdrant_service = FakeQdrantService(similarity=0.8)
    state: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-unique-123",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "work_mode": "hybrid",
            "level": "junior",
            "responsibilities": "Coding",
            "requirements": "Python knowledge",
            "skills": ["python", "fastapi"],
            "jd_status": "full_jd",
        },
        "user_warning": "Warning about formatting",
    }

    result = await process_job_state(db_session, state, embedding_service, qdrant_service)
    assert result.inserted_jobs == 1
    assert result.skipped_exact_duplicates == 0
    assert result.qdrant_upserted == 1
    assert result.qdrant_synced is True
    assert len(result.job_ids) == 1
    assert "Warning about formatting" in result.warnings
    assert embedding_service.row_count_at_first_call == 1
    assert len(embedding_service.calls) == 2
    assert qdrant_service.upserted_job_ids == result.job_ids
    assert qdrant_service.queried_job_ids == result.job_ids

    # Query the job post to verify fields
    stmt = select(JobPost).where(JobPost.id == result.job_ids[0])
    db_res = await db_session.execute(stmt)
    job = db_res.scalar_one()
    assert job.status == "pending_review"
    assert job.title == "Software Engineer"
    assert job.company == "Google"
    assert job.raw_content_hash == "hash-unique-123"
    assert job.should_score_similarity is True
    assert job.dedup_key is not None
    assert job.embedding_similarity == 0.8
    assert job.skill_overlap_score == 1.0
    assert job.location_match_score == 1.0
    assert job.level_match_score == 1.0
    assert job.base_score == pytest.approx(0.89)
    assert job.final_score == pytest.approx(0.89)
    assert job.final_score_percent == pytest.approx(89.0)


@pytest.mark.asyncio
async def test_process_job_state_exact_duplicate(db_session: AsyncSession, test_role_profile):
    state: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-unique-123",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "skills": ["python"],
            "jd_status": "full_jd",
        },
    }

    # Insert first time
    res1 = await process_job_state(
        db_session, state, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res1.inserted_jobs == 1

    # Insert second time with same raw_content_hash
    res2 = await process_job_state(
        db_session, state, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res2.inserted_jobs == 0
    assert res2.skipped_exact_duplicates == 1
    assert res2.job_ids == res1.job_ids


@pytest.mark.asyncio
async def test_process_job_state_dedup_key_skip(db_session: AsyncSession, test_role_profile):
    state1: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-1",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "skills": ["python"],
            "jd_status": "full_jd",
        },
    }

    # Second state has different raw_content_hash, but same company/title (dedup_key)
    state2: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-2",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": "Google",
            "location": "New York",
            "skills": ["python"],
            "jd_status": "full_jd",
        },
    }

    res1 = await process_job_state(
        db_session, state1, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res1.inserted_jobs == 1

    # The existing job status is pending_review, so decide_duplicate_action returns "skip_duplicate"
    res2 = await process_job_state(
        db_session, state2, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res2.inserted_jobs == 0
    assert res2.skipped_dedup_key_duplicates == 1
    assert res2.job_ids == res1.job_ids


@pytest.mark.asyncio
async def test_process_job_state_dedup_key_ignored_metadata(db_session: AsyncSession, test_role_profile):
    state1: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-1",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": "Google",
            "location": "San Francisco",
            "skills": ["python"],
            "jd_status": "full_jd",
        },
    }

    res1 = await process_job_state(
        db_session, state1, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res1.inserted_jobs == 1

    # Transition the first job to active state, e.g. "saved"
    stmt = select(JobPost).where(JobPost.id == res1.job_ids[0])
    db_res = await db_session.execute(stmt)
    job = db_res.scalar_one()
    job.status = "saved"
    await db_session.commit()

    # Second state has different raw_content_hash, but same company/title (dedup_key)
    state2: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-2",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": "Google",
            "location": "New York",
            "skills": ["python"],
            "jd_status": "full_jd",
        },
    }

    # The existing job status is saved, so decide_duplicate_action returns "mark_new_as_duplicate_ignored"
    res2 = await process_job_state(
        db_session, state2, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res2.inserted_jobs == 0
    assert res2.inserted_duplicate_metadata == 1
    assert len(res2.job_ids) == 1
    assert res2.job_ids[0] != res1.job_ids[0]

    # Verify the duplicate metadata job fields
    stmt2 = select(JobPost).where(JobPost.id == res2.job_ids[0])
    db_res2 = await db_session.execute(stmt2)
    dup_job = db_res2.scalar_one()
    assert dup_job.status == "ignored"
    assert dup_job.duplicate_of_job_id == res1.job_ids[0]
    assert dup_job.should_score_similarity is False
    assert dup_job.embedding_text is None
    assert dup_job.final_score is None


@pytest.mark.asyncio
async def test_process_job_state_integrity_error_rollback(db_session: AsyncSession, test_role_profile):
    state1: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-collision",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Software Engineer",
            "company": None,
            "location": "San Francisco",
            "skills": ["python"],
            "jd_status": "full_jd",
        },
    }

    # Add the first job
    res1 = await process_job_state(
        db_session, state1, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res1.inserted_jobs == 1

    from unittest.mock import patch
    
    original_execute = db_session.execute
    call_count = 0
    
    async def mock_execute(statement, *args, **kwargs):
        nonlocal call_count
        stmt_str = str(statement)
        if "raw_content_hash" in stmt_str and "INSERT" not in stmt_str:
            call_count += 1
            if call_count == 1:
                # The initial check: return empty to bypass it
                class EmptyResult:
                    def scalars(self):
                        class EmptyScalars:
                            def first(self):
                                return None
                        return EmptyScalars()
                return EmptyResult()
        # Otherwise run original
        return await original_execute(statement, *args, **kwargs)

    db_session.execute = mock_execute
    
    res2 = await process_job_state(
        db_session, state1, FakeEmbeddingService(), FakeQdrantService()
    )
    assert res2.inserted_jobs == 0
    assert res2.skipped_exact_duplicates == 1
    assert res2.job_ids == res1.job_ids


@pytest.mark.asyncio
async def test_process_job_state_qdrant_similarity_unavailable_keeps_committed_row(
    db_session: AsyncSession, test_role_profile
):
    state: JobAgentState = {
        "batch_id": "batch-1",
        "role_profile_id": test_role_profile.id,
        "input_source": "manual_text",
        "parse_status": "success",
        "raw_content_hash": "hash-qdrant-miss",
        "jd_status": "full_jd",
        "extracted_job": {
            "title": "Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "work_mode": "remote",
            "level": "junior",
            "responsibilities": "Build APIs",
            "requirements": "Python and FastAPI",
            "skills": ["python", "fastapi"],
            "jd_status": "full_jd",
        },
    }

    result = await process_job_state(
        db_session,
        state,
        FakeEmbeddingService(),
        FakeQdrantService(similarity=None),
    )

    assert result.inserted_jobs == 1
    assert result.qdrant_upserted == 1
    assert result.qdrant_synced is False

    stmt = select(JobPost).where(JobPost.id == result.job_ids[0])
    db_res = await db_session.execute(stmt)
    job = db_res.scalar_one()
    assert job.status == "pending_review"
    assert job.embedding_text is not None
    assert job.embedding_similarity is None
    assert job.final_score is None
    assert "Qdrant similarity unavailable for newly upserted job" in job.error_reason


def test_allowed_status_transitions_are_importable():
    assert ALLOWED_STATUS_TRANSITIONS["pending_review"] == frozenset(
        {"saved", "ignored"}
    )
    assert ALLOWED_STATUS_TRANSITIONS["saved"] == frozenset({"applied", "rejected"})
    assert ALLOWED_STATUS_TRANSITIONS["ignored"] == frozenset()


@pytest.mark.asyncio
async def test_approve_job_updates_sqlite_then_qdrant_payload(
    db_session: AsyncSession, test_role_profile
):
    job = await create_job_post(db_session, test_role_profile, "pending_review")
    qdrant_service = FakeQdrantService()

    updated_job = await approve_job(db_session, job.id, qdrant_service)

    assert updated_job.status == "saved"
    assert qdrant_service.status_payload_updates == [(job.id, "saved")]
    assert qdrant_service.deleted_job_ids == []


@pytest.mark.asyncio
async def test_reject_job_updates_sqlite_then_deletes_qdrant_point(
    db_session: AsyncSession, test_role_profile
):
    job = await create_job_post(db_session, test_role_profile, "pending_review")
    qdrant_service = FakeQdrantService()

    updated_job = await reject_job(db_session, job.id, qdrant_service)

    assert updated_job.status == "ignored"
    assert qdrant_service.deleted_job_ids == [job.id]
    assert qdrant_service.status_payload_updates == []


@pytest.mark.asyncio
async def test_invalid_status_transition_fails_before_mutation(
    db_session: AsyncSession, test_role_profile
):
    job = await create_job_post(db_session, test_role_profile, "pending_review")
    qdrant_service = FakeQdrantService()

    with pytest.raises(InvalidStatusTransition):
        await update_job_status(db_session, job.id, "applied", qdrant_service)

    refreshed = await db_session.get(JobPost, job.id)
    application_count = await db_session.scalar(
        select(func.count()).select_from(Application).where(
            Application.job_post_id == job.id
        )
    )
    assert refreshed.status == "pending_review"
    assert application_count == 0
    assert qdrant_service.status_payload_updates == []
    assert qdrant_service.deleted_job_ids == []


@pytest.mark.asyncio
async def test_update_job_status_creates_one_application_and_preserves_applied_at(
    db_session: AsyncSession, test_role_profile
):
    job = await create_job_post(db_session, test_role_profile, "saved")
    qdrant_service = FakeQdrantService()

    await update_job_status(db_session, job.id, "applied", qdrant_service)
    result = await db_session.execute(
        select(Application).where(Application.job_post_id == job.id)
    )
    application = result.scalar_one()
    applied_at = application.applied_at
    assert application.status == "applied"
    assert applied_at is not None

    await update_job_status(db_session, job.id, "interview", qdrant_service)
    result = await db_session.execute(
        select(Application).where(Application.job_post_id == job.id)
    )
    applications = result.scalars().all()

    assert len(applications) == 1
    assert applications[0].status == "interview"
    assert applications[0].applied_at == applied_at
    assert qdrant_service.status_payload_updates == [
        (job.id, "applied"),
        (job.id, "interview"),
    ]


@pytest.mark.asyncio
async def test_saved_to_rejected_creates_application_without_applied_at(
    db_session: AsyncSession, test_role_profile
):
    job = await create_job_post(db_session, test_role_profile, "saved")
    qdrant_service = FakeQdrantService()

    await update_job_status(db_session, job.id, "rejected", qdrant_service)

    result = await db_session.execute(
        select(Application).where(Application.job_post_id == job.id)
    )
    application = result.scalar_one()
    assert application.status == "rejected"
    assert application.applied_at is None
    assert qdrant_service.status_payload_updates == [(job.id, "rejected")]
    assert qdrant_service.deleted_job_ids == []
