import pytest

from app.db.models import ChatConversation, ChatMessage, MemorySummary, RoleProfile
from app.services.chat_memory_service import ChatMemoryService
from app.services.token_budget_service import SimpleTokenCounter


@pytest.mark.asyncio
async def test_memory_uses_summary_profile_and_recent_messages(db_session):
    profile = RoleProfile(target_role="AI Engineer", location="Hanoi", skills='["Python"]')
    db_session.add(profile)
    await db_session.commit()
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()
    db_session.add(
        MemorySummary(
            conversation_id=conversation.id,
            summary_text="Earlier: user wants internships.",
            token_count=4,
        )
    )
    db_session.add(ChatMessage(conversation_id=conversation.id, role="user", content="Find jobs", token_count=2))
    await db_session.commit()

    memory = await ChatMemoryService(max_tokens=100, token_counter=SimpleTokenCounter()).assemble(
        db_session,
        conversation_id=conversation.id,
        current_user_message="Rank them",
    )

    assert "Earlier: user wants internships." in memory.context_text
    assert "AI Engineer" in memory.context_text
    assert "Find jobs" in memory.context_text
    assert memory.total_tokens <= 100
