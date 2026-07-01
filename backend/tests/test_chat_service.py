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
