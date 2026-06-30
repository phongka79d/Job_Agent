from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes_role_profiles import get_session
from app.main import app


@pytest.mark.asyncio
async def test_create_role_profile_returns_uuid_and_list_orders_newest_first(db_session):
    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first_response = await client.post(
                "/api/role-profiles",
                json={
                    "target_role": "Backend Intern",
                    "level": "intern",
                    "location": "Ha Noi",
                    "accept_remote": True,
                    "skills": ["python", "fastapi"],
                    "resume_text": "Python backend resume",
                },
            )
            second_response = await client.post(
                "/api/role-profiles",
                json={
                    "target_role": "AI Engineer Intern",
                    "level": "intern",
                    "location": "Remote",
                    "accept_remote": True,
                    "skills": ["python", "rag", "qdrant"],
                    "resume_text": "AI engineering resume",
                },
            )
            list_response = await client.get("/api/role-profiles")
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 201
    first_id = first_response.json()["id"]
    UUID(first_id)

    assert second_response.status_code == 201
    second_id = second_response.json()["id"]
    UUID(second_id)
    assert second_id != first_id

    assert list_response.status_code == 200
    profiles = list_response.json()["role_profiles"]
    assert [profile["id"] for profile in profiles] == [second_id, first_id]
    assert profiles[0]["skills"] == ["python", "rag", "qdrant"]
