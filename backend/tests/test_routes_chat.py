import json
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.routes_role_profiles import get_session
from sqlalchemy import select

from app.db.models import AgentToolCall, ChatMessage, RoleProfile
from app.main import app
from app.services.agent_event_service import AgentEventService
from app.services.tool_registry import ToolRegistry, ToolRequest, ToolResult


class ChatLLMDouble:
    def __init__(self, answer: str = "Live LLM route answer") -> None:
        self.answer = answer
        self.calls = []

    async def generate_reply(self, *, user_message: str, working_memory: str) -> str:
        self.calls.append(
            {
                "user_message": user_message,
                "working_memory": working_memory,
            }
        )
        return self.answer


class FailingChatLLMDouble:
    async def generate_reply(self, *, user_message: str, working_memory: str) -> str:
        from app.services.chat_llm_client import ChatLLMProviderError

        raise ChatLLMProviderError("missing key")


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
async def test_stream_conversation_events_returns_agent_sse_and_persists_assistant(
    client,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    llm_client = ChatLLMDouble(answer="Here is your application pipeline summary.")
    monkeypatch.setattr(routes_chat, "chat_llm_client", llm_client, raising=False)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Session",
        },
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Summarize my application pipeline"},
    )
    after_message_id = message_response.json()["message"]["id"]

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": after_message_id},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message_started" in response.text
    assert "event: assistant_delta" in response.text
    assert "event: message_completed" in response.text
    assert "Here is your application pipeline summary." in response.text

    messages_response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/messages"
    )
    messages = messages_response.json()["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Here is your application pipeline summary."
    assert llm_client.calls


@pytest.mark.asyncio
async def test_stream_search_intent_calls_search_tool_and_persists_visible_event(
    client,
    db_session,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    async def search_handler(request: ToolRequest) -> ToolResult:
        assert request.name == "search_jobs"
        assert request.context["role_profile_id"] == role_profile.id
        assert request.arguments["query"] == "Start searching for AI Engineer Level Intern jobs"
        return ToolResult(
            content="Inserted 2 jobs into Review Queue.",
            result_summary="Added 2 jobs to Review Queue.",
            safe_payload={"inserted_jobs": 2, "review_queue_path": "/review"},
        )

    def build_registry(session):
        assert session is db_session
        return ToolRegistry(overrides={"search_jobs": search_handler})

    monkeypatch.setattr(routes_chat, "build_tool_registry", build_registry)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Session",
        },
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Start searching for AI Engineer Level Intern jobs"},
    )
    after_message_id = message_response.json()["message"]["id"]

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": after_message_id},
    )

    assert response.status_code == 200
    assert "event: tool_call_started" in response.text
    assert "event: tool_call_completed" in response.text
    assert "Called 1 tool: Job search." in response.text
    assert "Company XYZ" not in response.text

    calls = (
        await db_session.execute(
            select(AgentToolCall).where(
                AgentToolCall.conversation_id == conversation["id"]
            )
        )
    ).scalars().all()
    assert len(calls) == 1
    assert calls[0].tool_name == "search_jobs"
    assert calls[0].status == "success"
    assert calls[0].input_summary == "Job search: Start searching for AI Engineer Level Intern jobs"
    assert calls[0].result_summary == "Added 2 jobs to Review Queue."
    assert json.loads(calls[0].safe_payload_json) == {
        "inserted_jobs": 2,
        "review_queue_path": "/review",
    }

    messages_response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/messages"
    )
    messages = messages_response.json()["messages"]
    assert messages[1]["content"] == (
        "Called 1 tool: Job search. "
        "Added 2 jobs to Review Queue. Open Review Queue to review jobs."
    )


@pytest.mark.asyncio
async def test_stream_conversation_events_persists_visible_message_when_llm_unavailable(
    client,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    monkeypatch.setattr(routes_chat, "chat_llm_client", FailingChatLLMDouble())
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Session",
        },
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Summarize my application pipeline"},
    )
    after_message_id = message_response.json()["message"]["id"]

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": after_message_id},
    )

    assert response.status_code == 200
    assert "event: assistant_delta" in response.text
    assert "Chat LLM is unavailable" in response.text
    assert "event: message_completed" in response.text

    messages_response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/messages"
    )
    messages = messages_response.json()["messages"]
    assert messages[1]["content"].startswith("Chat LLM is unavailable.")
    assert json.loads(messages[1]["metadata_json"])["source"] == "chat_agent_error"


@pytest.mark.asyncio
async def test_stream_conversation_events_returns_404_for_missing_message(
    client,
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

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": uuid4()},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "message not found"


@pytest.mark.asyncio
async def test_stream_conversation_events_returns_404_for_message_from_other_conversation(
    client,
    role_profile,
):
    first_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "First session",
        },
    )
    second_response = await client.post(
        "/api/chat/conversations",
        json={
            "role_profile_id": role_profile.id,
            "title": "Second session",
        },
    )
    first = first_response.json()
    second = second_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{second['id']}/messages",
        json={"content": "Find backend jobs"},
    )
    other_message_id = message_response.json()["message"]["id"]

    response = await client.get(
        f"/api/chat/conversations/{first['id']}/stream",
        params={"after_message_id": other_message_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "message not found"


@pytest.mark.asyncio
async def test_stream_conversation_events_returns_404_for_missing_conversation(client):
    response = await client.get(
        f"/api/chat/conversations/{uuid4()}/stream",
        params={"after_message_id": uuid4()},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "conversation not found"


@pytest.mark.asyncio
async def test_stream_pasted_job_text_calls_extract_text_tool_and_persists_visible_event(
    client,
    db_session,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    pasted_job = (
        "Senior AI Engineer\n"
        "Company: Example Labs\n"
        "Location: Hanoi\n"
        "Responsibilities: build LLM evaluation workflows and retrieval systems.\n"
        "Requirements: Python, FastAPI, LangGraph, vector databases, and applied ML experience.\n"
        "Benefits: hybrid work and training budget.\n"
        "Apply by sending your CV."
    )
    progress_messages = []

    async def text_handler(request: ToolRequest) -> ToolResult:
        assert request.name == "extract_job_from_text"
        assert request.context["role_profile_id"] == role_profile.id
        assert request.arguments["raw_text"] == pasted_job
        assert "on_progress" in request.context
        await request.context["on_progress"]("Extracting structured job data...")
        progress_messages.append("called")
        return ToolResult(
            content="Added 1 job to Review Queue.",
            result_summary="Added 1 job to Review Queue.",
            safe_payload={
                "inserted_jobs": 1,
                "review_queue_path": "/review",
                "job_ids": ["job-1"],
            },
        )

    def build_registry(session):
        assert session is db_session
        return ToolRegistry(overrides={"extract_job_from_text": text_handler})

    monkeypatch.setattr(routes_chat, "build_tool_registry", build_registry)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={"role_profile_id": role_profile.id, "title": "Session"},
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": pasted_job},
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": message_response.json()["message"]["id"]},
    )

    assert response.status_code == 200
    assert "event: tool_call_started" in response.text
    assert "event: tool_call_progress" in response.text
    assert "event: tool_call_completed" in response.text
    assert "Called 1 tool: Extract job from text." in response.text
    assert "Senior AI Engineer" not in response.text
    assert progress_messages == ["called"]

    calls = (
        await db_session.execute(
            select(AgentToolCall).where(
                AgentToolCall.conversation_id == conversation["id"]
            )
        )
    ).scalars().all()
    assert len(calls) == 1
    assert calls[0].tool_name == "extract_job_from_text"
    assert calls[0].status == "success"
    assert calls[0].input_summary == f"Pasted job text, {len(pasted_job)} characters"
    assert calls[0].result_summary == "Added 1 job to Review Queue."
    assert json.loads(calls[0].safe_payload_json) == {
        "inserted_jobs": 1,
        "review_queue_path": "/review",
        "job_ids": ["job-1"],
    }

    messages_response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/messages"
    )
    messages = messages_response.json()["messages"]
    assert messages[1]["content"] == (
        "Called 1 tool: Extract job from text. "
        "Added 1 job to Review Queue. Open Review Queue to inspect and approve it."
    )


@pytest.mark.asyncio
async def test_stream_explicit_short_parse_request_calls_extract_text_tool(
    client,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    short_job = (
        "Parse this job:\n"
        "Title: AI Engineer Intern\n"
        "Company: Compact Labs\n"
        "Requirements: Python and retrieval basics"
    )
    calls = []

    async def text_handler(request: ToolRequest) -> ToolResult:
        calls.append(request)
        return ToolResult(
            content="Added 1 job to Review Queue.",
            result_summary="Added 1 job to Review Queue.",
            safe_payload={"inserted_jobs": 1, "review_queue_path": "/review"},
        )

    def build_registry(session):
        return ToolRegistry(overrides={"extract_job_from_text": text_handler})

    monkeypatch.setattr(routes_chat, "build_tool_registry", build_registry)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={"role_profile_id": role_profile.id, "title": "Session"},
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": short_job},
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": message_response.json()["message"]["id"]},
    )

    assert response.status_code == 200
    assert "event: tool_call_started" in response.text
    assert "Called 1 tool: Extract job from text." in response.text
    assert len(calls) == 1
    assert calls[0].arguments["raw_text"] == short_job


@pytest.mark.asyncio
async def test_stream_short_non_job_message_does_not_call_extract_text_tool(
    client,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    llm_client = ChatLLMDouble(answer="I can help with that.")
    monkeypatch.setattr(routes_chat, "chat_llm_client", llm_client, raising=False)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={"role_profile_id": role_profile.id, "title": "Session"},
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Can you compare my pipeline?"},
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": message_response.json()["message"]["id"]},
    )

    assert response.status_code == 200
    assert "extract_job_from_text" not in response.text
    assert "I can help with that." in response.text
    assert llm_client.calls


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


@pytest.mark.asyncio
async def test_delete_conversation_removes_messages_and_tool_calls(
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
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "Find jobs"},
    )
    service = AgentEventService()
    await service.create_tool_call(
        db_session,
        conversation_id=conversation["id"],
        tool_name="search_jobs",
        input_summary="Search jobs",
        safe_payload={},
    )

    response = await client.delete(f"/api/chat/conversations/{conversation['id']}")

    assert response.status_code == 204
    messages = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.conversation_id == conversation["id"])
        )
    ).scalars().all()
    tool_calls = (
        await db_session.execute(
            select(AgentToolCall).where(
                AgentToolCall.conversation_id == conversation["id"]
            )
        )
    ).scalars().all()
    assert messages == []
    assert tool_calls == []
    assert (
        await client.get(f"/api/chat/conversations/{conversation['id']}/messages")
    ).status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_returns_404_for_missing_conversation(client):
    response = await client.delete(f"/api/chat/conversations/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "conversation not found"
