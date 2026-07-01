import pytest

from app.db.models import (
    ChatConversation,
    ChatMessage,
    MemorySummary,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
    RoleProfile,
)
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


@pytest.mark.asyncio
async def test_memory_includes_active_cv_evidence(db_session):
    profile = RoleProfile(target_role="AI Engineer", location="Hanoi", skills='["Python"]')
    db_session.add(profile)
    await db_session.flush()
    document = ProfileDocument(
        role_profile_id=profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=80,
        chunk_count=1,
        document_kind="cv",
        status="ready",
    )
    db_session.add(document)
    await db_session.flush()
    version = ProfileDocumentVersion(
        document_id=document.id,
        role_profile_id=profile.id,
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=80,
        chunk_count=1,
        extraction_status="ready",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(version)
    await db_session.flush()
    document.active_version_id = version.id
    profile.active_cv_document_id = document.id
    profile.active_cv_version_id = version.id
    db_session.add(
        ProfileDocumentChunk(
            document_id=document.id,
            role_profile_id=profile.id,
            version_id=version.id,
            source_type="profile_cv",
            chunk_index=0,
            text="Active CV evidence: Python FastAPI internship project",
            token_count=8,
            qdrant_point_id="77777777-7777-7777-7777-777777777777",
        )
    )
    conversation = ChatConversation(role_profile_id=profile.id, title="Session")
    db_session.add(conversation)
    await db_session.commit()

    memory = await ChatMemoryService().assemble(
        db_session,
        conversation_id=conversation.id,
        current_user_message="Compare my CV with this role",
    )

    assert "Active CV evidence" in memory.context_text
    assert "Active CV: cv.pdf" in memory.context_text
