import pytest

from app.db.models import ChatConversation, RoleProfile
from app.services.agent_event_service import AgentEventService


@pytest.mark.asyncio
async def test_tool_call_lifecycle_persists_safe_summaries(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()

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
    )

    assert call.status == "pending"
    assert running.status == "running"
    assert succeeded.status == "success"
    assert succeeded.safe_payload_json == '{"query":"AI Engineer Intern Hanoi"}'


@pytest.mark.asyncio
async def test_create_tool_call_persists_empty_safe_payload(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()

    call = await AgentEventService().create_tool_call(
        db_session,
        conversation_id=conversation.id,
        tool_name="search_jobs",
        input_summary="Search with no visible parameters",
        safe_payload={},
    )

    assert call.safe_payload_json == "{}"
