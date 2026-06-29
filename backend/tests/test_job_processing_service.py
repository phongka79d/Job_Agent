import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, select

from app.db.models import Base, RoleProfile, JobPost
from app.agents.schemas import JobAgentState
from app.services.job_processing_service import process_job_state, JobProcessingResult


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


@pytest.mark.asyncio
async def test_process_job_state_new_insert(db_session: AsyncSession, test_role_profile):
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

    result = await process_job_state(db_session, state)
    assert result.inserted_jobs == 1
    assert result.skipped_exact_duplicates == 0
    assert len(result.job_ids) == 1
    assert "Warning about formatting" in result.warnings

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
    # All score fields should be None
    assert job.final_score is None


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
    res1 = await process_job_state(db_session, state)
    assert res1.inserted_jobs == 1

    # Insert second time with same raw_content_hash
    res2 = await process_job_state(db_session, state)
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

    res1 = await process_job_state(db_session, state1)
    assert res1.inserted_jobs == 1

    # The existing job status is pending_review, so decide_duplicate_action returns "skip_duplicate"
    res2 = await process_job_state(db_session, state2)
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

    res1 = await process_job_state(db_session, state1)
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
    res2 = await process_job_state(db_session, state2)
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
    res1 = await process_job_state(db_session, state1)
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
    
    res2 = await process_job_state(db_session, state1)
    assert res2.inserted_jobs == 0
    assert res2.skipped_exact_duplicates == 1
    assert res2.job_ids == res1.job_ids
