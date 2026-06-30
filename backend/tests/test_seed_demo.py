from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import routes_jobs
from app.api.routes_role_profiles import get_session
from app.db.models import Application, JobPost, RoleProfile
from app.main import app
from app.services import demo_loader
from app.services.demo_loader import (
    DEMO_ROLE_TARGET_ROLE,
    MOCK_SOURCE_PLATFORM,
    SCORABLE_JD_STATUSES,
    load_mock_fixture_states,
    reset_mock_demo_data,
)
from app.services.job_processing_service import JobProcessingResult
from scripts import seed_demo
from tests.conftest import FakeQdrantService


async def create_role_profile(
    db_session: AsyncSession,
    *,
    target_role: str = DEMO_ROLE_TARGET_ROLE,
) -> RoleProfile:
    profile = RoleProfile(
        id=str(uuid4()),
        target_role=target_role,
        level="intern",
        location="Ha Noi",
    )
    db_session.add(profile)
    await db_session.commit()
    return profile


async def create_job_post(
    db_session: AsyncSession,
    profile: RoleProfile,
    *,
    source_platform: str = MOCK_SOURCE_PLATFORM,
    title: str = "AI Engineer Intern",
    status: str = "pending_review",
) -> JobPost:
    job = JobPost(
        id=str(uuid4()),
        batch_id=str(uuid4()),
        role_profile_id=profile.id,
        title=title,
        company=f"{title} Co",
        source_platform=source_platform,
        raw_content_hash=f"hash-{uuid4()}",
        jd_status="full_jd",
        should_score_similarity=True,
        status=status,
    )
    db_session.add(job)
    await db_session.commit()
    return job


async def create_application(db_session: AsyncSession, job: JobPost) -> Application:
    application = Application(
        id=str(uuid4()),
        job_post_id=job.id,
        status="applied",
    )
    db_session.add(application)
    await db_session.commit()
    return application


def test_actual_demo_fixtures_validate_through_loader():
    batch_id = str(uuid4())
    role_profile_id = str(uuid4())

    states = load_mock_fixture_states(
        seed_demo.DEMO_FIXTURE_PATHS,
        batch_id=batch_id,
        role_profile_id=role_profile_id,
    )

    scorable_states = [
        state for state in states if state["should_score_similarity"] is True
    ]
    need_review_social_states = [
        state for state in states if state["should_score_similarity"] is False
    ]

    assert len(states) == 12
    assert len(scorable_states) == 10
    assert len(need_review_social_states) == 2
    assert {state["batch_id"] for state in states} == {batch_id}
    assert {state["role_profile_id"] for state in states} == {role_profile_id}

    for state in states:
        extracted_job = state["extracted_job"]
        assert state["input_source"] == "mock"
        assert extracted_job["source_platform"] == "mock"
        assert state["clean_text"]
        assert state["raw_content_hash"]
        assert state["embedding_text"] is None
        assert state["embedding_similarity"] is None
        assert state["final_score"] is None
        assert extracted_job["should_score_similarity"] is (
            state["jd_status"] in SCORABLE_JD_STATUSES
        )


def mock_state(batch_id: str, role_profile_id: str, title: str) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": "mock",
        "parse_status": "success",
        "raw_content_hash": f"hash-{uuid4()}",
        "jd_status": "full_jd",
        "should_score_similarity": True,
        "extracted_job": {"title": title, "source_platform": "mock"},
    }


@pytest.mark.asyncio
async def test_reset_deletes_mock_applications_and_jobs_only(db_session):
    profile = await create_role_profile(db_session)
    mock_job = await create_job_post(db_session, profile, source_platform="mock")
    non_mock_job = await create_job_post(
        db_session,
        profile,
        source_platform="manual_text",
        title="Manual Job",
    )
    mock_application = await create_application(db_session, mock_job)
    non_mock_application = await create_application(db_session, non_mock_job)
    qdrant_service = FakeQdrantService()

    result = await reset_mock_demo_data(
        db_session,
        qdrant_service=qdrant_service,
    )

    assert result.deleted_applications == 1
    assert result.deleted_qdrant_vectors == 1
    assert result.deleted_job_posts == 1
    assert result.deleted_role_profiles == 0
    assert qdrant_service.deleted_job_ids == [mock_job.id]
    assert await db_session.get(JobPost, mock_job.id) is None
    assert await db_session.get(Application, mock_application.id) is None
    assert await db_session.get(JobPost, non_mock_job.id) is not None
    assert await db_session.get(Application, non_mock_application.id) is not None
    assert await db_session.get(RoleProfile, profile.id) is not None


@pytest.mark.asyncio
async def test_mock_load_reset_preserves_active_role_profile(monkeypatch, db_session):
    profile = await create_role_profile(db_session)
    calls = []

    async def fake_reset(session, *, preserve_role_profile_id=None, qdrant_service=None):
        calls.append(("reset", preserve_role_profile_id, qdrant_service))
        return demo_loader.DemoResetResult(0, 0, 0, 0)

    def fake_load(paths, *, batch_id, role_profile_id):
        calls.append(("load", tuple(paths), batch_id, role_profile_id))
        return [mock_state(batch_id, role_profile_id, "Mock Route Job")]

    async def fake_process(session, state):
        calls.append(("process", state["batch_id"], state["role_profile_id"]))
        job = await create_job_post(
            session,
            profile,
            source_platform="mock",
            title="Mock Route Job",
        )
        return JobProcessingResult(
            inserted_jobs=1,
            qdrant_upserted=1,
            qdrant_synced=True,
            job_ids=[job.id],
        )

    monkeypatch.setattr(routes_jobs, "reset_mock_demo_data", fake_reset)
    monkeypatch.setattr(routes_jobs, "load_mock_fixture_states", fake_load)
    monkeypatch.setattr(routes_jobs, "process_job_state", fake_process)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/mock-load",
                json={
                    "role_profile_id": profile.id,
                    "reset_existing_demo": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["inserted_jobs"] == 1
    assert calls[0] == ("reset", profile.id, None)
    assert calls[1][0] == "load"
    assert calls[1][3] == profile.id
    assert calls[2][0] == "process"
    assert calls[2][2] == profile.id


@pytest.mark.asyncio
async def test_seed_uses_shared_loader_and_plan_three_processing(monkeypatch, db_session):
    calls = []

    def fake_load(paths, *, batch_id, role_profile_id):
        calls.append(("load", tuple(paths), batch_id, role_profile_id))
        return [mock_state(batch_id, role_profile_id, "Seed Job")]

    async def fake_process(session, state, *, qdrant_service):
        calls.append(("process", state["batch_id"], state["role_profile_id"], qdrant_service))
        return JobProcessingResult(
            inserted_jobs=1,
            qdrant_upserted=1,
            qdrant_synced=True,
            job_ids=[str(uuid4())],
        )

    monkeypatch.setattr(seed_demo, "load_mock_fixture_states", fake_load)
    monkeypatch.setattr(seed_demo, "process_job_state", fake_process)

    qdrant_service = FakeQdrantService()
    summary, scorable_jobs, need_review_social_jobs = await seed_demo.process_demo_states(
        db_session,
        batch_id="seed-batch",
        role_profile_id="seed-profile",
        qdrant_service=qdrant_service,
    )

    assert summary.inserted_jobs == 1
    assert summary.qdrant_upserted == 1
    assert scorable_jobs == 1
    assert need_review_social_jobs == 0
    assert calls == [
        ("load", seed_demo.DEMO_FIXTURE_PATHS, "seed-batch", "seed-profile"),
        ("process", "seed-batch", "seed-profile", qdrant_service),
    ]


def test_seed_help_documents_first_time_and_post_seed_offline_expectations():
    source = (seed_demo.BACKEND_ROOT / "scripts" / "seed_demo.py").read_text(
        encoding="utf-8"
    )

    assert "does not require Tavily" in source
    assert "LLM extraction" in source
    assert "URL fetching" in source
    assert "First-time seed generation requires local Qdrant" in source
    assert "OpenAI embedding access" in source


def test_seed_and_mock_load_do_not_bypass_plan_three_boundaries():
    sources = [
        (seed_demo.BACKEND_ROOT / "scripts" / "seed_demo.py").read_text(encoding="utf-8"),
        (routes_jobs.REPOSITORY_ROOT / "backend" / "app" / "api" / "routes_jobs.py").read_text(
            encoding="utf-8"
        ),
    ]

    for source in sources:
        assert "load_mock_fixture_states" in source
        assert "process_job_state" in source
        assert "insert(JobPost" not in source
        assert "QdrantService().upsert" not in source
        assert ".upsert_scorable_job" not in source
    assert "JobPost(" not in sources[0]


def test_phase_four_did_not_introduce_out_of_scope_infrastructure():
    table_names = set(JobPost.metadata.tables)
    forbidden_tables = {
        "queues", "queue", "workers", "worker", "cron_jobs",
        "background_jobs", "background_job", "search_runs",
    }
    forbidden_files = []
    for source_root in (
        routes_jobs.REPOSITORY_ROOT / "backend" / "app",
        routes_jobs.REPOSITORY_ROOT / "backend" / "scripts",
        routes_jobs.REPOSITORY_ROOT / "shared",
    ):
        if source_root.exists():
            for pattern in ("**/*celery*", "**/*redis*", "**/*playwright*"):
                forbidden_files.extend(source_root.glob(pattern))

    assert table_names.isdisjoint(forbidden_tables)
    assert forbidden_files == []
