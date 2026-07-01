import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.routes_role_profiles import get_session
from app.db.models import RoleProfile
from app.main import app


@pytest_asyncio.fixture
async def role_profile(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def client(db_session):
    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_conversation_returns_persisted_conversation(
    client,
    role_profile,
):
    response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Hanoi search",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["role_profile_id"] == role_profile.id
    assert data["title"] == "Hanoi search"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_append_user_message_returns_stream_url(client, role_profile):
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Session",
        },
    )
    conversation = conversation_response.json()

    response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Find AI Engineer Intern jobs in Hanoi"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["message"]["role"] == "user"
    assert data["stream_url"].startswith(
        f"/api/chat/conversations/{conversation['id']}/stream"
    )
