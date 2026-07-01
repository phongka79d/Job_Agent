from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.routes_role_profiles import get_session
from app.db.models import RoleProfile
from app.main import app
from app.services.agent_event_service import AgentEventService


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


@pytest.mark.asyncio
async def test_stream_conversation_events_returns_placeholder_sse(client, role_profile):
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Session",
        },
    )
    conversation = conversation_response.json()
    after_message_id = uuid4()

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": after_message_id},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == (
        "event: message_started\n"
        f'data: {{"conversation_id":"{conversation["id"]}",'
        f'"after_message_id":"{after_message_id}"}}\n\n'
        "event: message_completed\n"
        f'data: {{"conversation_id":"{conversation["id"]}",'
        f'"after_message_id":"{after_message_id}"}}\n\n'
    )


@pytest.mark.asyncio
async def test_list_tool_calls_returns_serialized_calls_in_order(
    client,
    db_session,
    role_profile,
):
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Session",
        },
    )
    conversation = conversation_response.json()
    service = AgentEventService()
    first = await service.create_tool_call(
        db_session,
        conversation_id=conversation["id"],
        tool_name="search_jobs",
        input_summary="Search jobs in Hanoi",
        safe_payload={"query": "AI Engineer Intern Hanoi"},
    )
    first = await service.mark_running(db_session, first.id)
    second = await service.create_tool_call(
        db_session,
        conversation_id=conversation["id"],
        tool_name="parse_job",
        input_summary="Parse selected job URL",
        safe_payload={},
    )
    second = await service.mark_success(
        db_session,
        second.id,
        result_summary="Parsed full job description",
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/tool-calls"
    )

    assert response.status_code == 200
    data = response.json()
    assert [tool_call["id"] for tool_call in data["tool_calls"]] == [
        first.id,
        second.id,
    ]
    assert data["tool_calls"][0]["conversation_id"] == conversation["id"]
    assert data["tool_calls"][0]["assistant_message_id"] is None
    assert data["tool_calls"][0]["tool_name"] == "search_jobs"
    assert data["tool_calls"][0]["status"] == "running"
    assert data["tool_calls"][0]["safe_payload_json"] == (
        '{"query":"AI Engineer Intern Hanoi"}'
    )
    assert data["tool_calls"][1]["tool_name"] == "parse_job"
    assert data["tool_calls"][1]["status"] == "success"
    assert data["tool_calls"][1]["result_summary"] == "Parsed full job description"
    assert data["tool_calls"][1]["safe_payload_json"] == "{}"


@pytest.mark.asyncio
async def test_list_tool_calls_returns_404_for_missing_conversation(client):
    response = await client.get(f"/api/chat/conversations/{uuid4()}/tool-calls")

    assert response.status_code == 404
    assert response.json()["detail"] == "conversation not found"
