import pytest

from app.db.models import ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion, RoleProfile
from app.services.profile_document_retrieval_service import ProfileDocumentRetrievalService
from app.services.tool_registry import (
    ToolRequest,
    build_retrieve_profile_documents_handler,
)


class FakeProfileVectorStore:
    def __init__(self, chunk_ids: list[str] | None = None, error: Exception | None = None) -> None:
        self.chunk_ids = chunk_ids or []
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def query_profile_document_chunks(self, **kwargs) -> list[str]:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.chunk_ids


class FakeEmbedder:
    async def embed_text(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


async def create_ready_cv(db_session, profile: RoleProfile, *, text: str, active: bool = True):
    document = ProfileDocument(
        role_profile_id=profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=len(text),
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
        extracted_text_chars=len(text),
        chunk_count=1,
        extraction_status="ready",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(version)
    await db_session.flush()
    document.active_version_id = version.id
    chunk = ProfileDocumentChunk(
        document_id=document.id,
        role_profile_id=profile.id,
        version_id=version.id,
        source_type="profile_cv",
        chunk_index=0,
        text=text,
        token_count=8,
        qdrant_point_id="55555555-5555-5555-5555-555555555555",
    )
    db_session.add(chunk)
    if active:
        profile.active_cv_document_id = document.id
        profile.active_cv_version_id = version.id
    await db_session.commit()
    return document, version, chunk


@pytest.mark.asyncio
async def test_retrieval_filters_chunks_by_role_profile(db_session):
    profile = RoleProfile(target_role="AI Engineer", skills="[]")
    other = RoleProfile(target_role="Backend Engineer", skills="[]")
    db_session.add_all([profile, other])
    await db_session.commit()

    await create_ready_cv(db_session, profile, text="Python FastAPI internship experience")
    await create_ready_cv(db_session, other, text="Python FastAPI internship experience from another profile", active=False)

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
        document_kind="cv",
        status="ready",
    )
    db_session.add(document)
    await db_session.flush()
    version = ProfileDocumentVersion(
        document_id=document.id,
        role_profile_id=test_role_profile.id,
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=500,
        chunk_count=2,
        extraction_status="ready",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(version)
    await db_session.flush()
    document.active_version_id = version.id
    test_role_profile.active_cv_document_id = document.id
    test_role_profile.active_cv_version_id = version.id
    db_session.add_all(
        [
            ProfileDocumentChunk(
                document_id=document.id,
                role_profile_id=test_role_profile.id,
                version_id=version.id,
                source_type="profile_cv",
                chunk_index=0,
                text="General coursework and certificates",
                token_count=4,
                qdrant_point_id="33333333-3333-3333-3333-333333333333",
            ),
            ProfileDocumentChunk(
                document_id=document.id,
                role_profile_id=test_role_profile.id,
                version_id=version.id,
                source_type="profile_cv",
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
        document_kind="cv",
        status="ready",
    )
    db_session.add(document)
    await db_session.flush()
    version = ProfileDocumentVersion(
        document_id=document.id,
        role_profile_id=test_role_profile.id,
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=500,
        chunk_count=1,
        extraction_status="ready",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(version)
    await db_session.flush()
    document.active_version_id = version.id
    test_role_profile.active_cv_document_id = document.id
    test_role_profile.active_cv_version_id = version.id
    db_session.add(
        ProfileDocumentChunk(
            document_id=document.id,
            role_profile_id=test_role_profile.id,
            version_id=version.id,
            source_type="profile_cv",
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
    assert result.result_summary == "Retrieved 1 active CV chunks"
    assert result.safe_payload["chunk_count"] == 1


@pytest.mark.asyncio
async def test_retrieval_uses_active_cv_version_only(db_session, test_role_profile):
    active_document, active_version, active_chunk = await create_ready_cv(
        db_session,
        test_role_profile,
        text="Active CV Python FastAPI RAG experience",
    )
    inactive_document = ProfileDocument(
        role_profile_id=test_role_profile.id,
        original_filename="old.pdf",
        stored_path="old.pdf",
        content_hash="old",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=40,
        chunk_count=1,
        document_kind="cv",
        status="ready",
    )
    db_session.add(inactive_document)
    await db_session.flush()
    inactive_version = ProfileDocumentVersion(
        document_id=inactive_document.id,
        role_profile_id=test_role_profile.id,
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="old.pdf",
        stored_path="old.pdf",
        content_hash="old",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=40,
        chunk_count=1,
        extraction_status="ready",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(inactive_version)
    await db_session.flush()
    db_session.add(
        ProfileDocumentChunk(
            document_id=inactive_document.id,
            role_profile_id=test_role_profile.id,
            version_id=inactive_version.id,
            source_type="profile_cv",
            chunk_index=0,
            text="Inactive old CV content",
            token_count=4,
            qdrant_point_id="66666666-6666-6666-6666-666666666666",
        )
    )
    await db_session.commit()

    service = ProfileDocumentRetrievalService(
        embedder=FakeEmbedder(),
        vector_store=FakeProfileVectorStore(chunk_ids=[active_chunk.id]),
    )

    result = await service.retrieve_active_cv_chunks(
        db_session,
        role_profile_id=test_role_profile.id,
        query="Python RAG",
        limit=5,
    )

    assert [chunk.chunk.id for chunk in result.chunks] == [active_chunk.id]
    assert result.document.id == active_document.id
    assert result.version.id == active_version.id


@pytest.mark.asyncio
async def test_retrieval_discards_vector_chunk_ids_outside_active_cv(db_session, test_role_profile):
    active_document, active_version, active_chunk = await create_ready_cv(
        db_session,
        test_role_profile,
        text="Active CV Python evidence",
    )
    stale_document = ProfileDocument(
        role_profile_id=test_role_profile.id,
        original_filename="stale.pdf",
        stored_path="stale.pdf",
        content_hash="stale",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=40,
        chunk_count=1,
        document_kind="cv",
        status="ready",
    )
    db_session.add(stale_document)
    await db_session.flush()
    stale_version = ProfileDocumentVersion(
        document_id=stale_document.id,
        role_profile_id=test_role_profile.id,
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="stale.pdf",
        stored_path="stale.pdf",
        content_hash="stale",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=40,
        chunk_count=1,
        extraction_status="ready",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(stale_version)
    await db_session.flush()
    stale_chunk = ProfileDocumentChunk(
        document_id=stale_document.id,
        role_profile_id=test_role_profile.id,
        version_id=stale_version.id,
        source_type="profile_cv",
        chunk_index=0,
        text="Stale CV content must not be returned",
        token_count=4,
        qdrant_point_id="88888888-8888-8888-8888-888888888888",
    )
    db_session.add(stale_chunk)
    await db_session.commit()

    service = ProfileDocumentRetrievalService(
        embedder=FakeEmbedder(),
        vector_store=FakeProfileVectorStore(chunk_ids=[stale_chunk.id, active_chunk.id]),
    )

    result = await service.retrieve_active_cv_chunks(
        db_session,
        role_profile_id=test_role_profile.id,
        query="Python",
        limit=5,
    )

    assert result.document.id == active_document.id
    assert result.version.id == active_version.id
    assert [item.chunk.id for item in result.chunks] == [active_chunk.id]


@pytest.mark.asyncio
async def test_retrieval_falls_back_to_sqlite_keyword_when_qdrant_fails(db_session, test_role_profile):
    await create_ready_cv(
        db_session,
        test_role_profile,
        text="Python FastAPI active CV evidence",
    )
    service = ProfileDocumentRetrievalService(
        embedder=FakeEmbedder(),
        vector_store=FakeProfileVectorStore(error=RuntimeError("qdrant unavailable")),
    )

    result = await service.retrieve_active_cv_chunks(
        db_session,
        role_profile_id=test_role_profile.id,
        query="FastAPI",
        limit=5,
    )

    assert len(result.chunks) == 1
    assert result.used_fallback is True
    assert result.chunks[0].chunk.text == "Python FastAPI active CV evidence"


@pytest.mark.asyncio
async def test_retrieval_returns_empty_result_when_no_active_cv(db_session, test_role_profile):
    service = ProfileDocumentRetrievalService()

    result = await service.retrieve_active_cv_chunks(
        db_session,
        role_profile_id=test_role_profile.id,
        query="Python",
        limit=5,
    )

    assert result.document is None
    assert result.version is None
    assert result.chunks == []
