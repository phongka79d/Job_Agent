from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import routes_jobs
from app.api.routes_role_profiles import get_session
from app.db.models import Base, JobPost, RoleProfile
from app.main import app
from app.services import job_search_workflow
from app.services.job_processing_service import InvalidStatusTransition, JobProcessingResult
from app.services.search_service import SearchServiceError, TavilySearchService


async def create_profile(db_session) -> RoleProfile:
    profile = RoleProfile(
        id=str(uuid4()),
        target_role="AI Engineer Intern",
        level="intern",
        location="Ha Noi",
        accept_remote=True,
        skills='["python", "fastapi", "qdrant"]',
        resume_text="AI engineering resume",
    )
    db_session.add(profile)
    await db_session.commit()
    return profile


async def create_job(
    db_session,
    profile: RoleProfile,
    *,
    batch_id: str | None = None,
    status: str = "pending_review",
    final_score: float | None = 0.8,
    title: str = "AI Engineer Intern",
    source_url: str | None = "https://example.test/job",
    source_platform: str = "manual_text",
    parse_status: str = "success",
    jd_status: str = "full_jd",
    extraction_status: str = "success",
    error_reason: str | None = None,
    duplicate_of_job_id: str | None = None,
    discovered_at: datetime | None = None,
) -> JobPost:
    job = JobPost(
        id=str(uuid4()),
        batch_id=batch_id or str(uuid4()),
        role_profile_id=profile.id,
        title=title,
        company="Example Co",
        location="Ha Noi",
        work_mode="remote",
        level="intern",
        employment_type="internship",
        salary=None,
        responsibilities="Build AI services",
        requirements="Python and FastAPI",
        skills='["python", "fastapi"]',
        source_url=source_url,
        source_platform=source_platform,
        parse_status=parse_status,
        duplicate_of_job_id=duplicate_of_job_id,
        jd_status=jd_status,
        extraction_status=extraction_status,
        error_reason=error_reason,
        should_score_similarity=True,
        embedding_similarity=0.8,
        skill_overlap_score=0.7,
        location_match_score=1.0,
        level_match_score=1.0,
        base_score=0.85,
        jd_confidence_multiplier=1.0,
        final_score=final_score,
        final_score_percent=None if final_score is None else final_score * 100,
        status=status,
        input_tokens=100,
        output_tokens=50,
        estimated_cost_usd=0.001,
        extraction_time_ms=500,
        discovered_at=discovered_at or datetime.now(timezone.utc),
    )
    db_session.add(job)
    await db_session.commit()
    return job


class FakeTavilyClient:
    def __init__(self, urls: list[str]):
        self.urls = urls
        self.max_results: int | None = None

    async def search(self, query: str, *, max_results: int, **kwargs):
        self.max_results = max_results
        return {
            "results": [
                {"url": url, "title": f"Job {index}", "content": "job result"}
                for index, url in enumerate(self.urls)
            ]
        }


@pytest.mark.asyncio
async def test_parse_text_returns_standard_ingestion_response_with_loaded_job(
    monkeypatch,
    db_session,
):
    profile = await create_profile(db_session)
    calls = []

    async def fake_extract_from_raw_text(**kwargs):
        calls.append(("extract", kwargs))
        return {
            "batch_id": kwargs["batch_id"],
            "role_profile_id": kwargs["role_profile_id"],
            "input_source": "manual_text",
            "raw_text": kwargs["raw_text"],
            "source_url": kwargs["source_url"],
            "parse_status": "success",
            "extracted_job": {"title": "AI Engineer Intern"},
            "extraction_status": "success",
        }

    async def fake_process_job_state(session, state):
        calls.append(("process", state))
        job = await create_job(
            session,
            profile,
            batch_id=state["batch_id"],
            title="AI Engineer Intern",
            source_url=state["source_url"],
            source_platform="manual_text",
            parse_status="success",
            status="pending_review",
        )
        return JobProcessingResult(
            inserted_jobs=1,
            qdrant_upserted=1,
            qdrant_synced=True,
            job_ids=[job.id],
        )

    monkeypatch.setattr(routes_jobs, "extract_from_raw_text", fake_extract_from_raw_text)
    monkeypatch.setattr(routes_jobs, "process_job_state", fake_process_job_state)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/parse-text",
                json={
                    "role_profile_id": profile.id,
                    "raw_text": "AI Engineer Intern role using Python and FastAPI",
                    "source_url": "https://example.test/manual",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted_jobs"] == 1
    assert payload["skipped_exact_duplicates"] == 0
    assert payload["skipped_dedup_key_duplicates"] == 0
    assert payload["inserted_duplicate_metadata"] == 0
    assert payload["qdrant_upserted"] == 1
    assert payload["qdrant_synced"] is True
    assert payload["warnings"] == []
    assert len(payload["jobs"]) == 1
    assert payload["jobs"][0]["status"] == "pending_review"
    assert payload["jobs"][0]["title"] == "AI Engineer Intern"
    assert calls[0][0] == "extract"
    assert calls[1][0] == "process"


@pytest.mark.asyncio
async def test_parse_url_manual_input_warning_and_loaded_job(monkeypatch, db_session):
    profile = await create_profile(db_session)
    warning = "This page could not be parsed reliably. Please paste the JD text manually."

    async def fake_extract_from_url(**kwargs):
        return {
            "batch_id": kwargs["batch_id"],
            "role_profile_id": kwargs["role_profile_id"],
            "input_source": kwargs["input_source"],
            "source_url": kwargs["source_url"],
            "parse_status": "needs_manual_input",
            "jd_status": "unclear",
            "extracted_job": {"title": "Low Content Page"},
            "extraction_status": "failed",
            "error_reason": "Low readable content",
            "user_warning": warning,
        }

    async def fake_process_job_state(session, state):
        job = await create_job(
            session,
            profile,
            batch_id=state["batch_id"],
            title="Low Content Page",
            source_url=state["source_url"],
            source_platform="manual_url",
            parse_status="needs_manual_input",
            jd_status="unclear",
            extraction_status="failed",
            error_reason="Low readable content",
            status="pending_review",
            final_score=None,
        )
        return JobProcessingResult(
            inserted_jobs=1,
            job_ids=[job.id],
            warnings=[state["user_warning"]],
        )

    monkeypatch.setattr(routes_jobs, "extract_from_url", fake_extract_from_url)
    monkeypatch.setattr(routes_jobs, "process_job_state", fake_process_job_state)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/parse-url",
                json={
                    "role_profile_id": profile.id,
                    "source_url": "https://example.test/low-content",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted_jobs"] == 1
    assert payload["warnings"] == [warning]
    assert payload["jobs"][0]["parse_status"] == "needs_manual_input"
    assert payload["jobs"][0]["error_reason"] == "Low readable content"


@pytest.mark.asyncio
async def test_search_respects_max_urls_and_continues_after_url_parse_failure(
    monkeypatch,
    db_session,
):
    profile = await create_profile(db_session)
    urls = [f"https://example.test/job-{index}" for index in range(12)]
    fake_client = FakeTavilyClient(urls)
    processed_urls = []

    async def fake_extract_from_url(**kwargs):
        processed_urls.append(kwargs["source_url"])
        if kwargs["source_url"].endswith("job-1"):
            raise RuntimeError("simulated parse failure")
        return {
            "batch_id": kwargs["batch_id"],
            "role_profile_id": kwargs["role_profile_id"],
            "input_source": kwargs["input_source"],
            "source_url": kwargs["source_url"],
            "parse_status": "success",
            "extracted_job": {"title": f"Parsed {kwargs['source_url']}"},
            "extraction_status": "success",
        }

    async def fake_process_job_state(session, state):
        job = await create_job(
            session,
            profile,
            batch_id=state["batch_id"],
            title=f"Parsed {state['source_url']}",
            source_url=state["source_url"],
            source_platform="tavily",
            status="pending_review",
        )
        return JobProcessingResult(
            inserted_jobs=1,
            qdrant_upserted=1,
            qdrant_synced=True,
            job_ids=[job.id],
        )

    monkeypatch.setattr(
        job_search_workflow,
        "search_service",
        TavilySearchService(client=fake_client),
    )
    monkeypatch.setattr(job_search_workflow, "extract_from_url", fake_extract_from_url)
    monkeypatch.setattr(job_search_workflow, "process_job_state", fake_process_job_state)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/search",
                json={
                    "role_profile_id": profile.id,
                    "query": "AI Engineer Intern FastAPI",
                    "max_urls": 10,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert fake_client.max_results == 10
    assert len(processed_urls) == 10
    assert "https://example.test/job-10" not in processed_urls
    assert "https://example.test/job-11" not in processed_urls
    assert payload["inserted_jobs"] == 9
    assert payload["qdrant_upserted"] == 9
    assert len(payload["jobs"]) == 9
    assert payload["warnings"] == [
        "Failed to process search result URL: https://example.test/job-1"
    ]
    assert all(job["source_platform"] == "tavily" for job in payload["jobs"])


@pytest.mark.asyncio
async def test_search_tavily_failure_returns_502_without_processing(
    monkeypatch,
    db_session,
):
    profile = await create_profile(db_session)
    calls = []

    class FailingSearchService:
        async def search_jobs(self, query: str, max_urls: int):
            raise SearchServiceError("Tavily search failed")

    async def fake_extract_from_url(**kwargs):
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(job_search_workflow, "search_service", FailingSearchService())
    monkeypatch.setattr(job_search_workflow, "extract_from_url", fake_extract_from_url)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/jobs/search",
                json={
                    "role_profile_id": profile.id,
                    "query": "AI Engineer Intern FastAPI",
                    "max_urls": 3,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Tavily search failed"
    assert calls == []


def test_no_background_infrastructure_tables_are_introduced():
    table_names = set(Base.metadata.tables)
    forbidden_table_names = {
        "queues",
        "queue",
        "workers",
        "worker",
        "cron_jobs",
        "background_jobs",
        "background_job",
        "search_runs",
    }

    assert table_names.isdisjoint(forbidden_table_names)


@pytest.mark.asyncio
async def test_review_queue_excludes_duplicates_and_orders_by_score(db_session):
    profile = await create_profile(db_session)
    original = await create_job(db_session, profile, final_score=0.7, title="Original")
    duplicate = await create_job(
        db_session,
        profile,
        final_score=0.99,
        title="Duplicate",
        duplicate_of_job_id=original.id,
    )
    best = await create_job(db_session, profile, final_score=0.95, title="Best")
    null_score = await create_job(db_session, profile, final_score=None, title="Null")
    saved = await create_job(db_session, profile, status="saved", final_score=1.0)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/jobs/review",
                params={"role_profile_id": profile.id},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    job_ids = [job["id"] for job in response.json()["jobs"]]
    assert job_ids == [best.id, original.id, null_score.id]
    assert duplicate.id not in job_ids
    assert saved.id not in job_ids


@pytest.mark.asyncio
async def test_dashboard_saved_and_tracked_filters_exclude_duplicates_and_order_by_score(db_session):
    profile = await create_profile(db_session)
    saved_low = await create_job(db_session, profile, status="saved", final_score=0.4)
    saved_high = await create_job(db_session, profile, status="saved", final_score=0.9)
    applied = await create_job(db_session, profile, status="applied", final_score=0.8)
    interview = await create_job(db_session, profile, status="interview", final_score=0.7)
    rejected = await create_job(db_session, profile, status="rejected", final_score=0.6)
    offer = await create_job(db_session, profile, status="offer", final_score=0.5)
    duplicate = await create_job(
        db_session,
        profile,
        status="saved",
        final_score=1.0,
        duplicate_of_job_id=saved_high.id,
    )
    pending = await create_job(db_session, profile, status="pending_review", final_score=0.95)
    ignored = await create_job(db_session, profile, status="ignored", final_score=0.94)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            saved_response = await client.get(
                "/api/jobs",
                params={"role_profile_id": profile.id, "status": "saved"},
            )
            tracked_response = await client.get(
                "/api/jobs",
                params={"role_profile_id": profile.id, "status": "tracked"},
            )
    finally:
        app.dependency_overrides.clear()

    assert saved_response.status_code == 200
    saved_ids = [job["id"] for job in saved_response.json()["jobs"]]
    assert saved_ids == [saved_high.id, saved_low.id]
    assert duplicate.id not in saved_ids

    assert tracked_response.status_code == 200
    tracked_ids = [job["id"] for job in tracked_response.json()["jobs"]]
    assert tracked_ids == [
        saved_high.id,
        applied.id,
        interview.id,
        rejected.id,
        offer.id,
        saved_low.id,
    ]
    assert duplicate.id not in tracked_ids
    assert pending.id not in tracked_ids
    assert ignored.id not in tracked_ids


@pytest.mark.asyncio
async def test_job_detail_returns_200_or_404(db_session):
    profile = await create_profile(db_session)
    job = await create_job(db_session, profile, status="saved")

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            found_response = await client.get(f"/api/jobs/{job.id}")
            missing_response = await client.get(f"/api/jobs/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert found_response.status_code == 200
    assert found_response.json()["id"] == job.id
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_status_routes_delegate_to_plan_three_status_helpers(monkeypatch, db_session):
    profile = await create_profile(db_session)
    approve_target = await create_job(db_session, profile, status="pending_review")
    reject_target = await create_job(db_session, profile, status="pending_review")
    manual_target = await create_job(db_session, profile, status="saved")
    calls = []

    async def fake_approve(session, job_id):
        calls.append(("approve", session, job_id))
        approve_target.status = "saved"
        return approve_target

    async def fake_reject(session, job_id):
        calls.append(("reject", session, job_id))
        reject_target.status = "ignored"
        return reject_target

    async def fake_update(session, job_id, status):
        calls.append(("update", session, job_id, status))
        manual_target.status = status
        return manual_target

    monkeypatch.setattr(routes_jobs, "approve_job", fake_approve)
    monkeypatch.setattr(routes_jobs, "reject_job", fake_reject)
    monkeypatch.setattr(routes_jobs, "update_job_status", fake_update)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            approve_response = await client.post(f"/api/jobs/{approve_target.id}/approve")
            reject_response = await client.post(f"/api/jobs/{reject_target.id}/reject")
            update_response = await client.patch(
                f"/api/jobs/{manual_target.id}/status",
                json={"status": "applied"},
            )
    finally:
        app.dependency_overrides.clear()

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "saved"
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "ignored"
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "applied"
    assert calls == [
        ("approve", db_session, approve_target.id),
        ("reject", db_session, reject_target.id),
        ("update", db_session, manual_target.id, "applied"),
    ]


@pytest.mark.asyncio
async def test_status_routes_return_400_for_invalid_transitions(monkeypatch, db_session):
    profile = await create_profile(db_session)
    job = await create_job(db_session, profile, status="saved")

    async def invalid_update(session, job_id, status):
        raise InvalidStatusTransition("invalid transition")

    monkeypatch.setattr(routes_jobs, "update_job_status", invalid_update)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"/api/jobs/{job.id}/status",
                json={"status": "applied"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid transition"


@pytest.mark.asyncio
async def test_manual_status_update_rejects_ignored_before_service_call(monkeypatch, db_session):
    profile = await create_profile(db_session)
    job = await create_job(db_session, profile, status="pending_review")
    calls = []

    async def fake_update(session, job_id, status):
        calls.append((job_id, status))
        return job

    monkeypatch.setattr(routes_jobs, "update_job_status", fake_update)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"/api/jobs/{job.id}/status",
                json={"status": "ignored"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert calls == []
