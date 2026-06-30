from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes_role_profiles import get_session
from app.db.models import JobPost, RoleProfile
from app.main import app


@pytest.mark.asyncio
async def test_batch_summary_aggregates_stored_fields_and_unknown_batch_returns_404(db_session):
    batch_id = str(uuid4())
    other_batch_id = str(uuid4())
    profile = RoleProfile(
        id=str(uuid4()),
        target_role="AI Engineer Intern",
        level="intern",
        location="Ha Noi",
        accept_remote=True,
        skills='["python", "fastapi"]',
        resume_text="AI resume",
    )
    db_session.add(profile)
    await db_session.commit()

    jobs = [
        JobPost(
            id=str(uuid4()),
            batch_id=batch_id,
            role_profile_id=profile.id,
            title="Scorable",
            company="Example Co",
            source_platform="mock",
            parse_status="success",
            jd_status="full_jd",
            extraction_status="success",
            should_score_similarity=True,
            final_score=0.9,
            status="pending_review",
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.01,
            extraction_time_ms=1000,
            discovered_at=datetime.now(timezone.utc),
        ),
        JobPost(
            id=str(uuid4()),
            batch_id=batch_id,
            role_profile_id=profile.id,
            title="Failed",
            company="Example Co",
            source_platform="mock",
            parse_status="failed",
            jd_status="unclear",
            extraction_status="failed",
            should_score_similarity=False,
            final_score=None,
            status="ignored",
            input_tokens=None,
            output_tokens=25,
            estimated_cost_usd=None,
            extraction_time_ms=None,
            discovered_at=datetime.now(timezone.utc),
        ),
        JobPost(
            id=str(uuid4()),
            batch_id=batch_id,
            role_profile_id=profile.id,
            title="Second Scorable",
            company="Example Co",
            source_platform="mock",
            parse_status="success",
            jd_status="partial_jd",
            extraction_status="success",
            should_score_similarity=True,
            final_score=0.7,
            status="saved",
            input_tokens=40,
            output_tokens=None,
            estimated_cost_usd=0.02,
            extraction_time_ms=3000,
            discovered_at=datetime.now(timezone.utc),
        ),
        JobPost(
            id=str(uuid4()),
            batch_id=other_batch_id,
            role_profile_id=profile.id,
            title="Other Batch",
            company="Example Co",
            source_platform="mock",
            parse_status="success",
            jd_status="full_jd",
            extraction_status="success",
            should_score_similarity=True,
            final_score=1.0,
            status="saved",
            input_tokens=999,
            output_tokens=999,
            estimated_cost_usd=9.99,
            extraction_time_ms=999,
            discovered_at=datetime.now(timezone.utc),
        ),
    ]
    db_session.add_all(jobs)
    await db_session.commit()

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/batches/{batch_id}/summary")
            missing_response = await client.get(f"/api/batches/{uuid4()}/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    summary = response.json()
    assert summary == {
        "batch_id": batch_id,
        "total_parsed_jobs": 3,
        "scorable_jobs": 2,
        "failed_extractions": 1,
        "total_input_tokens": 140,
        "total_output_tokens": 75,
        "total_tokens": 215,
        "estimated_cost_usd": 0.03,
        "average_extraction_time_ms": 2000.0,
    }
    assert missing_response.status_code == 404
