from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.db.models import ProfileDocument, ProfileDocumentVersion, RoleProfile
from app.services.profile_document_indexing_service import ProfileDocumentIndexingService


@dataclass
class FakeEmbedder:
    async def embed_text(self, text: str) -> list[float]:
        return [float(len(text)), 0.0, 1.0]


@dataclass
class FakeVectorStore:
    calls: list[dict[str, object]]

    async def upsert_profile_document_chunk(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_index_extracted_text_persists_chunks_with_version_id(db_session) -> None:
    profile = RoleProfile(id="profile-1", target_role="AI Engineer")
    document = ProfileDocument(
        id="doc-1",
        role_profile_id="profile-1",
        original_filename="cv.pdf",
        stored_path="stored.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=100,
        document_kind="cv",
        status="processing",
    )
    version = ProfileDocumentVersion(
        id="version-1",
        document_id="doc-1",
        role_profile_id="profile-1",
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path="stored.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=100,
        extraction_status="processing",
        structure_status="not_extracted",
        created_by="user",
    )
    db_session.add(profile)
    await db_session.flush()
    db_session.add_all([document, version])
    await db_session.flush()

    vector_store = FakeVectorStore(calls=[])
    service = ProfileDocumentIndexingService(embedder=FakeEmbedder(), vector_store=vector_store)

    chunk_count = await service.index_extracted_text(
        db_session,
        role_profile_id="profile-1",
        document_id="doc-1",
        version_id="version-1",
        text="A" * 2200,
    )
    await db_session.commit()

    assert chunk_count == 2
    assert len(vector_store.calls) == 2
    assert {call["version_id"] for call in vector_store.calls} == {"version-1"}


def test_chunk_text_uses_stable_overlap() -> None:
    service = ProfileDocumentIndexingService(embedder=FakeEmbedder(), vector_store=FakeVectorStore(calls=[]))

    chunks = service.chunk_text("A" * 2000, max_chars=1800, overlap_chars=200)

    assert len(chunks) == 2
    assert chunks[0] == "A" * 1800
    assert chunks[1] == "A" * 400
