from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db.models import ChatConversation, ChatMessage, RoleProfile
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_create_conversation_persists_role_profile_link(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    conversation = await ChatService().create_conversation(
        db_session,
        role_profile_id=profile.id,
        title="AI jobs in Hanoi",
    )

    assert conversation.role_profile_id == profile.id
    assert conversation.title == "AI jobs in Hanoi"
    assert conversation.status == "active"


@pytest.mark.asyncio
async def test_create_message_persists_full_content(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    message = await ChatService().append_message(
        db_session,
        conversation_id=conversation.id,
        role="user",
        content="Find AI Engineer Intern jobs in Hanoi",
        metadata={"source": "chat"},
    )

    rows = (
        await db_session.execute(
            select(ChatMessage).where(ChatMessage.conversation_id == conversation.id)
        )
    ).scalars().all()
    assert rows == [message]
    assert rows[0].content == "Find AI Engineer Intern jobs in Hanoi"
    assert rows[0].metadata_json == '{"source":"chat"}'


@pytest.mark.asyncio
async def test_create_message_persists_empty_metadata_dict(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    message = await ChatService().append_message(
        db_session,
        conversation_id=conversation.id,
        role="assistant",
        content="No metadata fields yet",
        metadata={},
    )

    assert message.metadata_json == "{}"


@pytest.mark.asyncio
async def test_list_conversations_filters_limits_and_orders_by_latest_activity(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    other_profile = RoleProfile(target_role="Data Engineer", skills="[]")
    db_session.add_all([profile, other_profile])
    await db_session.commit()
    await db_session.refresh(profile)
    await db_session.refresh(other_profile)

    stale = ChatConversation(role_profile_id=profile.id, title="Stale")
    middle = ChatConversation(role_profile_id=profile.id, title="Middle")
    recent = ChatConversation(role_profile_id=profile.id, title="Recent")
    other = ChatConversation(role_profile_id=other_profile.id, title="Other")
    db_session.add_all([stale, middle, recent, other])
    await db_session.commit()

    stale.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    middle.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    recent.updated_at = datetime(2024, 1, 3, tzinfo=timezone.utc)
    other.updated_at = datetime(2024, 1, 4, tzinfo=timezone.utc)
    await db_session.commit()

    await ChatService().append_message(
        db_session,
        conversation_id=stale.id,
        role="user",
        content="Bring this conversation back to the top",
    )

    conversations = await ChatService().list_conversations(
        db_session,
        role_profile_id=profile.id,
        limit=2,
    )

    assert [conversation.id for conversation in conversations] == [stale.id, recent.id]


@pytest.mark.asyncio
async def test_list_messages_filters_limits_and_orders_chronologically(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    other_conversation = ChatConversation(role_profile_id=profile.id, title="Other")
    db_session.add_all([conversation, other_conversation])
    await db_session.commit()
    await db_session.refresh(conversation)
    await db_session.refresh(other_conversation)

    third = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content="Third",
        created_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
    )
    first = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content="First",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    second = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content="Second",
        created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    other = ChatMessage(
        conversation_id=other_conversation.id,
        role="user",
        content="Other conversation",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add_all([third, first, second, other])
    await db_session.commit()

    messages = await ChatService().list_messages(
        db_session,
        conversation_id=conversation.id,
        limit=2,
    )

    assert [message.id for message in messages] == [first.id, second.id]
