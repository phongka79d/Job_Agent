from datetime import datetime, timezone

import pytest

from app.db.models import AgentToolCall, ChatConversation, RoleProfile
from app.services.agent_event_service import AgentEventService


async def _create_conversation(db_session) -> ChatConversation:
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()
    return conversation


@pytest.mark.asyncio
async def test_tool_call_lifecycle_persists_safe_summaries(db_session):
    conversation = await _create_conversation(db_session)

    service = AgentEventService()
    call = await service.create_tool_call(
        db_session,
        conversation_id=conversation.id,
        tool_name="search_jobs",
        input_summary="Search jobs in Hanoi",
        safe_payload={"query": "AI Engineer Intern Hanoi"},
    )
    running = await service.mark_running(db_session, call.id)
    succeeded = await service.mark_success(
        db_session,
        call.id,
        result_summary="Found 5 URLs",
        safe_payload={"inserted_jobs": 5, "review_queue_path": "/review"},
    )

    assert call.status == "pending"
    assert running.status == "running"
    assert succeeded.status == "success"
    assert succeeded.safe_payload_json == (
        '{"inserted_jobs":5,"review_queue_path":"/review"}'
    )


@pytest.mark.asyncio
async def test_create_tool_call_persists_empty_safe_payload(db_session):
    conversation = await _create_conversation(db_session)

    call = await AgentEventService().create_tool_call(
        db_session,
        conversation_id=conversation.id,
        tool_name="search_jobs",
        input_summary="Search with no visible parameters",
        safe_payload={},
    )

    assert call.safe_payload_json == "{}"


@pytest.mark.asyncio
async def test_mark_failed_persists_frontend_safe_error(db_session):
    conversation = await _create_conversation(db_session)
    service = AgentEventService()
    call = await service.create_tool_call(
        db_session,
        conversation_id=conversation.id,
        tool_name="search_jobs",
        input_summary="Search jobs in Hanoi",
    )

    failed = await service.mark_failed(
        db_session,
        call.id,
        error_message="Search provider unavailable",
    )

    assert failed.status == "failed"
    assert failed.error_message == "Search provider unavailable"
    assert failed.completed_at is not None


@pytest.mark.asyncio
async def test_list_tool_calls_orders_by_created_order_and_id(db_session):
    conversation = await _create_conversation(db_session)
    other_conversation = await _create_conversation(db_session)
    same_created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    later_created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    first = AgentToolCall(
        id="00000000-0000-0000-0000-000000000001",
        conversation_id=conversation.id,
        tool_name="search_jobs",
        input_summary="First",
        status="pending",
        created_at=same_created_at,
    )
    second = AgentToolCall(
        id="00000000-0000-0000-0000-000000000002",
        conversation_id=conversation.id,
        tool_name="parse_job",
        input_summary="Second",
        status="pending",
        created_at=same_created_at,
    )
    third = AgentToolCall(
        id="00000000-0000-0000-0000-000000000000",
        conversation_id=conversation.id,
        tool_name="rank_jobs",
        input_summary="Third",
        status="pending",
        created_at=later_created_at,
    )
    other = AgentToolCall(
        id="00000000-0000-0000-0000-000000000003",
        conversation_id=other_conversation.id,
        tool_name="search_jobs",
        input_summary="Other conversation",
        status="pending",
        created_at=same_created_at,
    )
    db_session.add_all([third, second, first, other])
    await db_session.commit()

    tool_calls = await AgentEventService().list_tool_calls(
        db_session,
        conversation_id=conversation.id,
    )

    assert [tool_call.id for tool_call in tool_calls] == [
        first.id,
        second.id,
        third.id,
    ]


@pytest.mark.asyncio
async def test_missing_tool_call_id_raises_value_error(db_session):
    with pytest.raises(ValueError, match="tool call not found"):
        await AgentEventService().mark_running(db_session, "missing-tool-call")
