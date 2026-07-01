import pytest

from app.db.models import ProfileDocument, ProfileDocumentChunk, RoleProfile
from app.services.profile_document_retrieval_service import ProfileDocumentRetrievalService
from app.services.tool_registry import (
    ToolRequest,
    build_retrieve_profile_documents_handler,
)


@pytest.mark.asyncio
async def test_retrieval_filters_chunks_by_role_profile(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    other = RoleProfile(target_role="Backend Engineer", skills="[]")
    db_session.add_all([profile, other])
    await db_session.commit()

    document = ProfileDocument(
        role_profile_id=profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=500,
        chunk_count=1,
        status="ready",
    )
    other_document = ProfileDocument(
        role_profile_id=other.id,
        original_filename="other.pdf",
        stored_path="other.pdf",
        content_hash="other-hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=500,
        chunk_count=1,
        status="ready",
    )
    db_session.add_all([document, other_document])
    await db_session.flush()
    db_session.add_all(
        [
            ProfileDocumentChunk(
                document_id=document.id,
                role_profile_id=profile.id,
                chunk_index=0,
                text="Python FastAPI internship experience",
                token_count=4,
                qdrant_point_id="11111111-1111-1111-1111-111111111111",
            ),
            ProfileDocumentChunk(
                document_id=other_document.id,
                role_profile_id=other.id,
                chunk_index=0,
                text="Python FastAPI internship experience from another profile",
                token_count=7,
                qdrant_point_id="22222222-2222-2222-2222-222222222222",
            ),
        ]
    )
    await db_session.commit()

    chunks = await ProfileDocumentRetrievalService().retrieve(
        db_session,
        role_profile_id=profile.id,
        query="Python internship",
        limit=3,
    )

    assert len(chunks) == 1
    assert chunks[0].role_profile_id == profile.id


@pytest.mark.asyncio
async def test_retrieval_ranks_matching_chunks_before_weaker_matches(db_session, test_role_profile):
    document = ProfileDocument(
        role_profile_id=test_role_profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=500,
        chunk_count=2,
        status="ready",
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add_all(
        [
            ProfileDocumentChunk(
                document_id=document.id,
                role_profile_id=test_role_profile.id,
                chunk_index=0,
                text="General coursework and certificates",
                token_count=4,
                qdrant_point_id="33333333-3333-3333-3333-333333333333",
            ),
            ProfileDocumentChunk(
                document_id=document.id,
                role_profile_id=test_role_profile.id,
                chunk_index=1,
                text="Python FastAPI internship portfolio",
                token_count=4,
                qdrant_point_id="44444444-4444-4444-4444-444444444444",
            ),
        ]
    )
    await db_session.commit()

    chunks = await ProfileDocumentRetrievalService().retrieve(
        db_session,
        role_profile_id=test_role_profile.id,
        query="Python FastAPI internship",
        limit=1,
    )

    assert [chunk.text for chunk in chunks] == ["Python FastAPI internship portfolio"]


@pytest.mark.asyncio
async def test_retrieve_profile_documents_tool_returns_sanitized_summary(
    db_session,
    test_role_profile,
):
    document = ProfileDocument(
        role_profile_id=test_role_profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=500,
        chunk_count=1,
        status="ready",
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add(
        ProfileDocumentChunk(
            document_id=document.id,
            role_profile_id=test_role_profile.id,
            chunk_index=0,
            text="Python FastAPI internship experience",
            token_count=4,
            qdrant_point_id="55555555-5555-5555-5555-555555555555",
        )
    )
    await db_session.commit()
    handler = build_retrieve_profile_documents_handler(
        ProfileDocumentRetrievalService(),
        db_session,
    )

    result = await handler(
        ToolRequest(
            name="retrieve_profile_documents",
            arguments={"query": "Python", "limit": 5},
            context={"role_profile_id": test_role_profile.id},
        )
    )

    assert result.content == "Python FastAPI internship experience"
    assert result.result_summary == "Retrieved 1 profile document chunks"
    assert result.safe_payload == {"chunk_count": 1}
