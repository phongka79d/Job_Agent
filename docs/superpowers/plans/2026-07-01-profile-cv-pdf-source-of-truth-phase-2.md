# Profile CV Active Retrieval And Agent Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the active profile CV retrievable by the AI agent through visible read-only tools, and make chat memory/scoring prefer the active CV as profile evidence.

**Architecture:** Extend the landed Phase 1 PDF/version model. Keep PDF files authoritative, use `profile_document_versions` and active CV pointers for scoping, add `version_id` to Qdrant profile-document payloads, and keep raw CV text out of frontend safe payloads. Existing chat tool-call persistence and frontend tool-call rendering are reused.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, SQLite, Qdrant client, existing embedding service, existing chat SSE/tool-call events, pytest, React/Vitest only for unchanged generic tool timeline verification.

---

## Source Inputs

- Spec: `docs/superpowers/specs/2026-07-01-profile-cv-pdf-source-of-truth-design.md`
- Roadmap: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-roadmap.md`
- Phase 1: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-1.md`

## Phase 2 Scope

Implement:

- active-CV retrieval service
- version-aware profile chunk retrieval
- Qdrant profile-document payload and filter support for `version_id`
- tools:
  - `list_profile_cvs`
  - `get_active_profile_cv`
  - `view_profile_cv_metadata`
  - `retrieve_profile_cv_chunks`
  - `analyze_cv_structure`
- chat-visible tool event for CV reads
- chat memory includes active CV evidence when present
- job scoring uses active CV extracted text as primary embedding evidence when present

Do not implement:

- CV draft editing
- PDF export
- job-score CV improvement suggestions
- OCR
- new frontend panels beyond existing generic tool-call timeline

## File Structure

Modify:

- `backend/app/services/qdrant_service.py`
  - Add `version_id` to profile document payload/indexes.
  - Add version-filtered profile document chunk query by vector.
- `backend/app/services/profile_document_service.py`
  - Pass `version_id` into Qdrant upserts.
  - Extend `ProfileDocumentVectorStore` protocol.
- `backend/app/services/profile_document_retrieval_service.py`
  - Replace profile-wide keyword-only retrieval with active-CV-aware retrieval and Qdrant-first/SQLite-fallback behavior.
- `backend/app/services/tool_registry.py`
  - Register CV read tools and handlers.
  - Keep `retrieve_profile_documents` as a compatibility alias to active CV retrieval.
- `backend/app/api/routes_chat.py`
  - Wire CV tool handlers into `build_tool_registry`.
  - Add visible CV-read tool event branch for CV/profile questions.
- `backend/app/services/chat_memory_service.py`
  - Add active CV metadata and bounded relevant chunks to working memory.
- `backend/app/services/job_processing_service.py`
  - Build semantic role query from active CV chunks first, with structured profile fields as supplemental evidence.
- `backend/app/services/scoring_service.py`
  - Add a pure helper that combines role preferences with active CV evidence for embedding.
- `backend/tests/test_qdrant_service.py`
- `backend/tests/test_profile_document_service.py`
- `backend/tests/test_profile_document_retrieval_service.py`
- `backend/tests/test_tool_registry.py`
- `backend/tests/test_routes_chat.py`
- `backend/tests/test_chat_memory_service.py`
- `backend/tests/test_job_processing_service.py`
- `backend/tests/test_scoring_service.py`

No new database tables in this phase.

---

### Task 1: Add Version-Aware Qdrant Profile Document Payloads

**Files:**
- Modify: `backend/app/services/qdrant_service.py`
- Modify: `backend/app/services/profile_document_service.py`
- Test: `backend/tests/test_qdrant_service.py`
- Test: `backend/tests/test_profile_document_service.py`

- [ ] **Step 1: Write failing Qdrant payload/index tests**

Update `backend/tests/test_qdrant_service.py`.

In `test_ensure_profile_document_collection_requests_payload_indexes`, update the expected set:

```python
    assert set(PROFILE_DOCUMENT_PAYLOAD_INDEX_FIELDS) == {
        "role_profile_id",
        "document_id",
        "version_id",
        "source_type",
    }
```

In `test_upsert_profile_document_chunk_uses_sanitized_payload`, add:

```python
    version_id = str(uuid4())
```

Pass it to the upsert:

```python
        version_id=version_id,
```

Update the payload assertion:

```python
    assert point.payload == build_profile_document_payload(
        role_profile_id=role_profile_id,
        document_id=document_id,
        version_id=version_id,
        chunk_id=chunk_id,
        chunk_index=0,
    )
    assert point.payload["source_type"] == "profile_cv"
```

Add this test:

```python
@pytest.mark.asyncio
async def test_query_profile_document_chunks_filters_by_active_version():
    client = FakeQdrantClient()
    service = QdrantService(client=client, vector_size=3)
    role_profile_id = str(uuid4())
    document_id = str(uuid4())
    version_id = str(uuid4())

    await service.query_profile_document_chunks(
        query_vector=[1.0, 0.0, 0.0],
        role_profile_id=role_profile_id,
        document_id=document_id,
        version_id=version_id,
        limit=4,
    )

    collection_name, query, kwargs = client.queries[0]
    assert collection_name == PROFILE_DOCUMENT_COLLECTION_NAME
    assert query == [1.0, 0.0, 0.0]
    assert kwargs["limit"] == 4
    payload_filter = kwargs["query_filter"]
    filter_values = {
        condition.key: condition.match.value
        for condition in payload_filter.must
        if hasattr(condition, "key")
    }
    assert filter_values == {
        "role_profile_id": role_profile_id,
        "document_id": document_id,
        "version_id": version_id,
        "source_type": "profile_cv",
    }
```

Keep the existing `FakeQdrantClient.__init__` query tracking:

```python
        self.queries = []
```

Keep the existing `FakeQdrantClient.query_points` behavior that records calls and preserves queued responses:

```python
    async def query_points(self, collection_name, query, **kwargs):
        self.queries.append((collection_name, query, kwargs))
        if self.query_responses:
            return self.query_responses.pop(0)
        return SimpleNamespace(points=[])
```

- [ ] **Step 2: Run Qdrant tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_qdrant_service.py::test_ensure_profile_document_collection_requests_payload_indexes tests\test_qdrant_service.py::test_upsert_profile_document_chunk_uses_sanitized_payload tests\test_qdrant_service.py::test_query_profile_document_chunks_filters_by_active_version -q
```

Expected: fail because `version_id` is not indexed or accepted.

- [ ] **Step 3: Update Qdrant payload/index implementation**

In `backend/app/services/qdrant_service.py`, update:

```python
PROFILE_DOCUMENT_PAYLOAD_INDEX_FIELDS = (
    "role_profile_id",
    "document_id",
    "version_id",
    "source_type",
)
```

Update `build_profile_document_payload`:

```python
def build_profile_document_payload(
    *,
    role_profile_id: str,
    document_id: str,
    version_id: str,
    chunk_id: str,
    chunk_index: int,
) -> dict[str, str | int]:
    """Build the approved lightweight Qdrant payload for profile CV chunks."""
    return {
        "role_profile_id": role_profile_id,
        "document_id": document_id,
        "version_id": version_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "source_type": "profile_cv",
    }
```

Keep `QdrantClientProtocol.query_points` as:

```python
    async def query_points(
        self,
        collection_name: str,
        query: Sequence[float],
        **kwargs: object,
    ) -> object:
        raise NotImplementedError
```

Update `upsert_profile_document_chunk` signature:

```python
    async def upsert_profile_document_chunk(
        self,
        *,
        point_id: str,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        chunk_id: str,
        chunk_index: int,
        vector: Sequence[float],
    ) -> None:
```

Pass `version_id` into `build_profile_document_payload`.

Add this helper:

```python
def build_profile_document_filter(
    *,
    role_profile_id: str,
    document_id: str,
    version_id: str,
) -> qmodels.Filter:
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="role_profile_id",
                match=qmodels.MatchValue(value=role_profile_id),
            ),
            qmodels.FieldCondition(
                key="document_id",
                match=qmodels.MatchValue(value=document_id),
            ),
            qmodels.FieldCondition(
                key="version_id",
                match=qmodels.MatchValue(value=version_id),
            ),
            qmodels.FieldCondition(
                key="source_type",
                match=qmodels.MatchValue(value="profile_cv"),
            ),
        ]
    )
```

Add this method to `QdrantService`:

```python
    async def query_profile_document_chunks(
        self,
        *,
        query_vector: Sequence[float],
        role_profile_id: str,
        document_id: str,
        version_id: str,
        limit: int = 5,
    ) -> list[str]:
        """Return matching profile CV chunk IDs for one active document version."""
        try:
            response = await self.client.query_points(
                collection_name=PROFILE_DOCUMENT_COLLECTION_NAME,
                query=self._validate_vector(query_vector),
                query_filter=build_profile_document_filter(
                    role_profile_id=role_profile_id,
                    document_id=document_id,
                    version_id=version_id,
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            self._log_qdrant_error("query_profile_document_chunks", exc)
            raise QdrantServiceError("Qdrant profile document query failed") from exc

        points = getattr(response, "points", response)
        chunk_ids: list[str] = []
        for point in points or []:
            payload = getattr(point, "payload", {}) or {}
            if isinstance(payload, dict) and payload.get("chunk_id"):
                chunk_ids.append(str(payload["chunk_id"]))
        return chunk_ids
```

- [ ] **Step 4: Pass version IDs from profile document indexing**

In `backend/app/services/profile_document_service.py`, update `ProfileDocumentVectorStore`:

```python
    async def upsert_profile_document_chunk(
        self,
        *,
        point_id: str,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        chunk_id: str,
        chunk_index: int,
        vector: list[float],
    ) -> None:
        raise NotImplementedError
```

In `create_document_from_pdf`, update the vector upsert call:

```python
                await self.vector_store.upsert_profile_document_chunk(
                    point_id=chunk.qdrant_point_id,
                    role_profile_id=role_profile_id,
                    document_id=document.id,
                    version_id=version.id,
                    chunk_id=chunk_id,
                    chunk_index=index,
                    vector=vector,
                )
```

Update every test fake `upsert_profile_document_chunk` with `**kwargs`; no additional fake change is needed when the fake already accepts `**kwargs`.

- [ ] **Step 5: Run Qdrant and profile document service tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_qdrant_service.py tests\test_profile_document_service.py -q
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add backend/app/services/qdrant_service.py backend/app/services/profile_document_service.py backend/tests/test_qdrant_service.py backend/tests/test_profile_document_service.py
git commit -m "feat: index profile cv chunks by version"
```

---

### Task 2: Build Active-CV Retrieval Service

**Files:**
- Modify: `backend/app/services/profile_document_retrieval_service.py`
- Test: `backend/tests/test_profile_document_retrieval_service.py`

- [ ] **Step 1: Write failing active-CV retrieval tests**

Update imports in `backend/tests/test_profile_document_retrieval_service.py`:

```python
from app.db.models import ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion, RoleProfile
```

Add this fake vector store near the top of the file:

```python
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
```

Add a helper:

```python
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
```

Add tests:

```python
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
```

```python
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
```

```python
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
```

- [ ] **Step 2: Run retrieval tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_retrieval_service.py -q
```

Expected: fail because active-CV result types and methods do not exist.

- [ ] **Step 3: Implement active-CV retrieval dataclasses and service**

Replace `backend/app/services/profile_document_retrieval_service.py` with this structure while preserving the existing `retrieve(...)` method as a compatibility wrapper:

```python
"""Profile CV retrieval service for chat memory and tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion, RoleProfile
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService


class TextEmbedder(Protocol):
    async def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class ProfileChunkVectorStore(Protocol):
    async def query_profile_document_chunks(
        self,
        *,
        query_vector: list[float],
        role_profile_id: str,
        document_id: str,
        version_id: str,
        limit: int = 5,
    ) -> list[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class RetrievedProfileCvChunk:
    chunk: ProfileDocumentChunk
    score_source: str


@dataclass(frozen=True)
class ActiveProfileCvRetrievalResult:
    document: ProfileDocument | None
    version: ProfileDocumentVersion | None
    chunks: list[RetrievedProfileCvChunk]
    used_fallback: bool = False


class ProfileDocumentRetrievalService:
    def __init__(
        self,
        *,
        embedder: TextEmbedder | None = None,
        vector_store: ProfileChunkVectorStore | None = None,
    ) -> None:
        self.embedder = embedder or EmbeddingService()
        self.vector_store = vector_store or QdrantService()

    async def retrieve(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        query: str,
        limit: int = 5,
    ) -> list[ProfileDocumentChunk]:
        result = await self.retrieve_active_cv_chunks(
            session,
            role_profile_id=role_profile_id,
            query=query,
            limit=limit,
        )
        return [item.chunk for item in result.chunks]

    async def retrieve_active_cv_chunks(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        query: str,
        limit: int = 5,
    ) -> ActiveProfileCvRetrievalResult:
        active = await self.get_active_cv(session, role_profile_id=role_profile_id)
        if active is None:
            return ActiveProfileCvRetrievalResult(document=None, version=None, chunks=[])
        document, version = active

        try:
            query_vector = await self.embedder.embed_text(query or document.original_filename)
            chunk_ids = await self.vector_store.query_profile_document_chunks(
                query_vector=query_vector,
                role_profile_id=role_profile_id,
                document_id=document.id,
                version_id=version.id,
                limit=limit,
            )
            chunks = await self._chunks_by_ids(session, chunk_ids)
            if chunks:
                return ActiveProfileCvRetrievalResult(
                    document=document,
                    version=version,
                    chunks=[RetrievedProfileCvChunk(chunk=chunk, score_source="qdrant") for chunk in chunks],
                )
        except Exception:
            pass

        chunks = await self._keyword_chunks(
            session,
            role_profile_id=role_profile_id,
            document_id=document.id,
            version_id=version.id,
            query=query,
            limit=limit,
        )
        return ActiveProfileCvRetrievalResult(
            document=document,
            version=version,
            chunks=[RetrievedProfileCvChunk(chunk=chunk, score_source="sqlite_keyword") for chunk in chunks],
            used_fallback=True,
        )

    async def get_active_cv(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
    ) -> tuple[ProfileDocument, ProfileDocumentVersion] | None:
        profile = await session.get(RoleProfile, role_profile_id)
        if profile is None or profile.active_cv_document_id is None or profile.active_cv_version_id is None:
            return None
        document = await session.get(ProfileDocument, profile.active_cv_document_id)
        version = await session.get(ProfileDocumentVersion, profile.active_cv_version_id)
        if document is None or version is None:
            return None
        if document.role_profile_id != role_profile_id or version.role_profile_id != role_profile_id:
            return None
        return document, version

    async def list_profile_cvs(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
    ) -> list[ProfileDocument]:
        result = await session.execute(
            select(ProfileDocument)
            .where(ProfileDocument.role_profile_id == role_profile_id)
            .order_by(ProfileDocument.created_at.desc(), ProfileDocument.id.desc())
        )
        return list(result.scalars())

    async def _chunks_by_ids(
        self,
        session: AsyncSession,
        chunk_ids: list[str],
    ) -> list[ProfileDocumentChunk]:
        if not chunk_ids:
            return []
        result = await session.execute(
            select(ProfileDocumentChunk).where(ProfileDocumentChunk.id.in_(chunk_ids))
        )
        by_id = {chunk.id: chunk for chunk in result.scalars()}
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    async def _keyword_chunks(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        query: str,
        limit: int,
    ) -> list[ProfileDocumentChunk]:
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.role_profile_id == role_profile_id)
            .where(ProfileDocumentChunk.document_id == document_id)
            .where(ProfileDocumentChunk.version_id == version_id)
            .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
            .limit(100)
        )
        chunks = list(result.scalars())
        terms = [term.lower() for term in query.split() if len(term) >= 3]
        if not terms:
            return chunks[:limit]

        def score(chunk: ProfileDocumentChunk) -> int:
            text = chunk.text.lower()
            return sum(1 for term in terms if term in text)

        ranked = sorted(chunks, key=score, reverse=True)
        return [chunk for chunk in ranked if score(chunk) > 0][:limit]
```

- [ ] **Step 4: Run retrieval tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_retrieval_service.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add backend/app/services/profile_document_retrieval_service.py backend/tests/test_profile_document_retrieval_service.py
git commit -m "feat: retrieve active profile cv chunks"
```

---

### Task 3: Add Read-Only Profile CV Tools

**Files:**
- Modify: `backend/app/services/tool_registry.py`
- Test: `backend/tests/test_tool_registry.py`
- Test: `backend/tests/test_profile_document_retrieval_service.py`

- [ ] **Step 1: Write failing tool registry tests**

In `backend/tests/test_tool_registry.py`, extend `test_registry_exposes_safe_tool_metadata`:

```python
    for tool_name in [
        "list_profile_cvs",
        "get_active_profile_cv",
        "view_profile_cv_metadata",
        "retrieve_profile_cv_chunks",
        "analyze_cv_structure",
    ]:
        assert tool_name in tools
        assert tools[tool_name].requires_confirmation is False
        assert "api_key" not in tools[tool_name].description.lower()
```

Add:

```python
@pytest.mark.asyncio
async def test_profile_cv_tool_handlers_return_sanitized_payloads():
    from app.services.tool_registry import (
        build_analyze_cv_structure_handler,
        build_get_active_profile_cv_handler,
        build_list_profile_cvs_handler,
        build_retrieve_profile_cv_chunks_handler,
        build_view_profile_cv_metadata_handler,
    )

    class Document:
        id = "doc-1"
        original_filename = "cv.pdf"
        status = "ready"
        chunk_count = 2
        active_version_id = "version-1"

    class Version:
        id = "version-1"
        version_number = 1
        source_type = "original_upload"
        extraction_status = "ready"
        structure_status = "not_extracted"
        structure_confidence = None

    class Chunk:
        text = "Private full CV text with Python and FastAPI"
        id = "chunk-1"
        chunk_index = 0

    class Item:
        chunk = Chunk()
        score_source = "sqlite_keyword"

    class Result:
        document = Document()
        version = Version()
        chunks = [Item()]
        used_fallback = True

    class Retrieval:
        async def list_profile_cvs(self, session, *, role_profile_id):
            return [Document()]

        async def get_active_cv(self, session, *, role_profile_id):
            return Document(), Version()

        async def retrieve_active_cv_chunks(self, session, *, role_profile_id, query, limit):
            return Result()

    session = object()
    request = ToolRequest(
        name="retrieve_profile_cv_chunks",
        arguments={"query": "Python", "limit": 3},
        context={"role_profile_id": "profile-1"},
    )

    retrieve_result = await build_retrieve_profile_cv_chunks_handler(Retrieval(), session)(request)
    assert "Private full CV text" in retrieve_result.content
    assert "Private full CV text" not in str(retrieve_result.safe_payload)
    assert retrieve_result.safe_payload == {
        "document_id": "doc-1",
        "version_id": "version-1",
        "chunk_count": 1,
        "used_fallback": True,
    }

    list_result = await build_list_profile_cvs_handler(Retrieval(), session)(request)
    assert list_result.safe_payload["documents"][0]["document_id"] == "doc-1"

    active_result = await build_get_active_profile_cv_handler(Retrieval(), session)(request)
    assert active_result.safe_payload["document_id"] == "doc-1"

    metadata_result = await build_view_profile_cv_metadata_handler(Retrieval(), session)(request)
    assert metadata_result.safe_payload["version_id"] == "version-1"

    structure_result = await build_analyze_cv_structure_handler(Retrieval(), session)(request)
    assert structure_result.safe_payload["structure_status"] == "not_extracted"
```

- [ ] **Step 2: Run tool tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_tool_registry.py -q
```

Expected: fail because CV tool names and builders do not exist.

- [ ] **Step 3: Register CV tools**

In `backend/app/services/tool_registry.py`, import:

```python
from app.services.profile_document_retrieval_service import ProfileDocumentRetrievalService
```

Add these `ToolDefinition` entries to `ToolRegistry.__init__` before the legacy `retrieve_profile_documents` entry:

```python
            "list_profile_cvs": ToolDefinition(
                name="list_profile_cvs",
                description="List uploaded profile CV PDFs and active-version metadata.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "get_active_profile_cv": ToolDefinition(
                name="get_active_profile_cv",
                description="Return safe metadata for the active profile CV source of truth.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "view_profile_cv_metadata": ToolDefinition(
                name="view_profile_cv_metadata",
                description="Return safe metadata for a profile CV document and its active version.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "retrieve_profile_cv_chunks": ToolDefinition(
                name="retrieve_profile_cv_chunks",
                description="Retrieve relevant active CV chunks for backend AI reasoning.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
            "analyze_cv_structure": ToolDefinition(
                name="analyze_cv_structure",
                description="Report extracted CV structure reliability metadata without editing the PDF.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
```

- [ ] **Step 4: Add CV tool handlers**

Append these helpers below `build_retrieve_profile_documents_handler`:

```python
def _document_safe_payload(document: object) -> dict[str, Any]:
    return {
        "document_id": str(getattr(document, "id", "")),
        "filename": str(getattr(document, "original_filename", "")),
        "status": str(getattr(document, "status", "")),
        "chunk_count": int(getattr(document, "chunk_count", 0) or 0),
        "active_version_id": (
            str(getattr(document, "active_version_id"))
            if getattr(document, "active_version_id", None)
            else None
        ),
    }


def _version_safe_payload(version: object) -> dict[str, Any]:
    return {
        "version_id": str(getattr(version, "id", "")),
        "version_number": int(getattr(version, "version_number", 0) or 0),
        "source_type": str(getattr(version, "source_type", "")),
        "extraction_status": str(getattr(version, "extraction_status", "")),
        "structure_status": str(getattr(version, "structure_status", "")),
        "structure_confidence": getattr(version, "structure_confidence", None),
    }


def build_list_profile_cvs_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        documents = await retrieval_service.list_profile_cvs(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
        )
        safe_documents = [_document_safe_payload(document) for document in documents]
        return ToolResult(
            content=f"Found {len(safe_documents)} uploaded profile CVs.",
            result_summary=f"Found {len(safe_documents)} profile CVs",
            safe_payload={"documents": safe_documents},
        )

    return handler


def build_get_active_profile_cv_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        active = await retrieval_service.get_active_cv(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
        )
        if active is None:
            return ToolResult(
                content="No active profile CV is selected.",
                result_summary="No active profile CV",
                safe_payload={"has_active_cv": False},
            )
        document, version = active
        return ToolResult(
            content=(
                "Active profile CV is available. "
                "Use retrieve_profile_cv_chunks to read relevant extracted text."
            ),
            result_summary=f"Active CV: {document.original_filename}",
            safe_payload={
                "has_active_cv": True,
                **_document_safe_payload(document),
                **_version_safe_payload(version),
            },
        )

    return handler


def build_view_profile_cv_metadata_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        return await build_get_active_profile_cv_handler(retrieval_service, session)(request)

    return handler


def build_retrieve_profile_cv_chunks_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        result = await retrieval_service.retrieve_active_cv_chunks(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            query=str(request.arguments.get("query", "")),
            limit=int(request.arguments.get("limit", 5)),
        )
        content = "\n\n".join(item.chunk.text for item in result.chunks)
        if result.document is None or result.version is None:
            return ToolResult(
                content="No active profile CV is selected.",
                result_summary="No active profile CV",
                safe_payload={"has_active_cv": False, "chunk_count": 0},
            )
        return ToolResult(
            content=content,
            result_summary=f"Retrieved {len(result.chunks)} active CV chunks",
            safe_payload={
                "document_id": result.document.id,
                "version_id": result.version.id,
                "chunk_count": len(result.chunks),
                "used_fallback": result.used_fallback,
            },
        )

    return handler


def build_analyze_cv_structure_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        active = await retrieval_service.get_active_cv(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
        )
        if active is None:
            return ToolResult(
                content="No active profile CV is selected.",
                result_summary="No active profile CV",
                safe_payload={"has_active_cv": False},
            )
        document, version = active
        structure_status = str(getattr(version, "structure_status", "not_extracted"))
        return ToolResult(
            content=(
                "CV structure status is "
                f"{structure_status}. Structure-preserving editing is not part of Phase 2."
            ),
            result_summary=f"CV structure: {structure_status}",
            safe_payload={
                "has_active_cv": True,
                "document_id": document.id,
                "version_id": version.id,
                "structure_status": structure_status,
                "structure_confidence": getattr(version, "structure_confidence", None),
            },
        )

    return handler
```

Update `build_retrieve_profile_documents_handler` to delegate to the new active CV handler:

```python
def build_retrieve_profile_documents_handler(
    retrieval_service: object,
    session: object,
) -> ToolHandler:
    return build_retrieve_profile_cv_chunks_handler(retrieval_service, session)
```

- [ ] **Step 5: Run tool tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_tool_registry.py tests\test_profile_document_retrieval_service.py -q
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 3**

```powershell
git add backend/app/services/tool_registry.py backend/tests/test_tool_registry.py backend/tests/test_profile_document_retrieval_service.py
git commit -m "feat: add profile cv read tools"
```

---

### Task 4: Wire Visible Chat Tool Events For CV Reads

**Files:**
- Modify: `backend/app/api/routes_chat.py`
- Test: `backend/tests/test_routes_chat.py`

- [ ] **Step 1: Write failing chat route test**

Add to `backend/tests/test_routes_chat.py`:

```python
@pytest.mark.asyncio
async def test_stream_cv_question_calls_profile_cv_retrieval_tool(
    client,
    db_session,
    role_profile,
    monkeypatch,
):
    from app.api import routes_chat

    async def retrieve_handler(request: ToolRequest) -> ToolResult:
        assert request.name == "retrieve_profile_cv_chunks"
        assert request.context["role_profile_id"] == role_profile.id
        assert request.arguments["query"] == "What skills are missing from my CV?"
        return ToolResult(
            content="Active CV evidence: Python and FastAPI projects.",
            result_summary="Retrieved 1 active CV chunk",
            safe_payload={
                "document_id": "doc-1",
                "version_id": "version-1",
                "chunk_count": 1,
                "used_fallback": False,
            },
        )

    def build_registry(session):
        assert session is db_session
        return ToolRegistry(overrides={"retrieve_profile_cv_chunks": retrieve_handler})

    monkeypatch.setattr(routes_chat, "build_tool_registry", build_registry)
    conversation_response = await client.post(
        "/api/chat/conversations",
        json={"role_profile_id": role_profile.id, "title": "Session"},
    )
    conversation = conversation_response.json()
    message_response = await client.post(
        f"/api/chat/conversations/{conversation['id']}/messages",
        json={"content": "What skills are missing from my CV?"},
    )

    response = await client.get(
        f"/api/chat/conversations/{conversation['id']}/stream",
        params={"after_message_id": message_response.json()["message"]["id"]},
    )

    assert response.status_code == 200
    assert "event: tool_call_started" in response.text
    assert "event: tool_call_completed" in response.text
    assert "retrieve_profile_cv_chunks" in response.text
    assert "Active CV evidence" not in response.text

    calls = (
        await db_session.execute(
            select(AgentToolCall).where(AgentToolCall.conversation_id == conversation["id"])
        )
    ).scalars().all()
    assert len(calls) == 1
    assert calls[0].tool_name == "retrieve_profile_cv_chunks"
    assert calls[0].status == "success"
    assert json.loads(calls[0].safe_payload_json) == {
        "document_id": "doc-1",
        "version_id": "version-1",
        "chunk_count": 1,
        "used_fallback": False,
    }
```

- [ ] **Step 2: Run chat route test and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_chat.py::test_stream_cv_question_calls_profile_cv_retrieval_tool -q
```

Expected: fail because CV questions do not trigger CV tools.

- [ ] **Step 3: Wire CV handlers into chat registry**

In `backend/app/api/routes_chat.py`, extend imports from `tool_registry`:

```python
    build_analyze_cv_structure_handler,
    build_get_active_profile_cv_handler,
    build_list_profile_cvs_handler,
    build_retrieve_profile_cv_chunks_handler,
    build_search_jobs_handler,
    build_view_profile_cv_metadata_handler,
```

Add import:

```python
from app.services.profile_document_retrieval_service import ProfileDocumentRetrievalService
```

Add module singleton:

```python
profile_cv_retrieval_service = ProfileDocumentRetrievalService()
```

Update `build_tool_registry` overrides:

```python
            "list_profile_cvs": build_list_profile_cvs_handler(profile_cv_retrieval_service, session),
            "get_active_profile_cv": build_get_active_profile_cv_handler(profile_cv_retrieval_service, session),
            "view_profile_cv_metadata": build_view_profile_cv_metadata_handler(profile_cv_retrieval_service, session),
            "retrieve_profile_cv_chunks": build_retrieve_profile_cv_chunks_handler(profile_cv_retrieval_service, session),
            "analyze_cv_structure": build_analyze_cv_structure_handler(profile_cv_retrieval_service, session),
            "retrieve_profile_documents": build_retrieve_profile_cv_chunks_handler(profile_cv_retrieval_service, session),
```

- [ ] **Step 4: Add CV intent helper and visible branch**

Add near intent helpers:

```python
def _is_profile_cv_read_intent(content: str) -> bool:
    normalized = content.casefold()
    cv_terms = ("cv", "resume", "profile", "portfolio", "transcript", "certificate")
    read_terms = (
        "read",
        "analyze",
        "compare",
        "skill",
        "skills",
        "missing",
        "improve",
        "match",
        "score",
        "evidence",
    )
    return any(term in normalized for term in cv_terms) and any(
        term in normalized for term in read_terms
    )
```

Before the final `else:` LLM branch in `event_generator`, add a branch modeled after the search/extract branches. Use this exact assistant content and do not include retrieved CV text in SSE payloads:

```python
        elif _is_profile_cv_read_intent(user_message.content):
            tool_call = await agent_event_service.create_tool_call(
                session,
                conversation_id=str(conversation_id),
                tool_name="retrieve_profile_cv_chunks",
                input_summary=f"Active CV retrieval: {user_message.content}",
                safe_payload={"query": user_message.content},
            )
            tool_call = await agent_event_service.mark_running(session, tool_call.id)
            yield _sse_event(
                "tool_call_started",
                {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status,
                    "input_summary": tool_call.input_summary,
                },
            )
            try:
                tool_result = await build_tool_registry(session).execute(
                    ToolRequest(
                        name="retrieve_profile_cv_chunks",
                        arguments={"query": user_message.content, "limit": 5},
                        context={
                            "role_profile_id": conversation.role_profile_id,
                            "conversation_id": str(conversation_id),
                        },
                    )
                )
            except Exception:
                logger.exception("retrieve_profile_cv_chunks tool failed")
                tool_call = await agent_event_service.mark_failed(
                    session,
                    tool_call.id,
                    error_message="Active CV retrieval failed. Check uploaded CV extraction and indexing.",
                )
                assistant_content = (
                    "Called 1 tool: Retrieve active CV, but retrieval failed. "
                    "Check that an active text-based CV PDF is uploaded and try again."
                )
                agent_metadata_source = "chat_agent_tool_error"
                yield _sse_event(
                    "tool_call_failed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "error_message": tool_call.error_message,
                    },
                )
            else:
                tool_call = await agent_event_service.mark_success(
                    session,
                    tool_call.id,
                    result_summary=tool_result.result_summary,
                    safe_payload=tool_result.safe_payload,
                )
                assistant_content = (
                    "Called 1 tool: Retrieve active CV. "
                    f"{tool_result.result_summary}. I used the active CV extracted text as profile evidence."
                )
                agent_metadata_source = "chat_agent_tool"
                yield _sse_event(
                    "tool_call_completed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "result_summary": tool_call.result_summary,
                        "safe_payload": tool_result.safe_payload,
                    },
                )
```

- [ ] **Step 5: Run chat route tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_chat.py -q
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add backend/app/api/routes_chat.py backend/tests/test_routes_chat.py
git commit -m "feat: show active cv retrieval tool calls"
```

---

### Task 5: Prefer Active CV Evidence In Memory And Scoring

**Files:**
- Modify: `backend/app/services/chat_memory_service.py`
- Modify: `backend/app/services/scoring_service.py`
- Modify: `backend/app/services/job_processing_service.py`
- Test: `backend/tests/test_chat_memory_service.py`
- Test: `backend/tests/test_scoring_service.py`
- Test: `backend/tests/test_job_processing_service.py`

- [ ] **Step 1: Write failing scoring helper test**

In `backend/tests/test_scoring_service.py`, import:

```python
from app.services.scoring_service import build_role_query_text, build_role_query_text_with_cv_evidence
```

Add:

```python
def test_build_role_query_text_with_cv_evidence_prefers_active_cv_text():
    profile = {
        "target_role": "AI Engineer",
        "level": "Intern",
        "location": "Hanoi",
        "accept_remote": True,
        "skills": ["Python"],
        "resume_text": "Legacy resume text",
    }

    text = build_role_query_text_with_cv_evidence(
        profile,
        active_cv_text="Active CV evidence with FastAPI and RAG projects",
    )

    assert "Active CV evidence with FastAPI and RAG projects" in text
    assert "Legacy resume text" not in text
    assert "Target role: AI Engineer" in text
    assert "Skills: Python" in text
```

- [ ] **Step 2: Write failing memory test**

In `backend/tests/test_chat_memory_service.py`, add a ready active CV document/version/chunk using the helper shape from Task 2, then assert memory contains active CV evidence:

```python
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
```

Update imports in that test file:

```python
from app.db.models import (
    ChatConversation,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
    RoleProfile,
)
```

- [ ] **Step 3: Run memory/scoring tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_scoring_service.py::test_build_role_query_text_with_cv_evidence_prefers_active_cv_text tests\test_chat_memory_service.py::test_memory_includes_active_cv_evidence -q
```

Expected: fail because helper and memory behavior do not exist.

- [ ] **Step 4: Add scoring helper**

In `backend/app/services/scoring_service.py`, add this ORM-safe helper after `build_role_query_text`:

```python
def build_role_query_text_with_cv_evidence(role_profile: Any, active_cv_text: str | None) -> str:
    """Build profile embedding text with active CV evidence as the primary source."""
    if not active_cv_text or not str(active_cv_text).strip():
        return build_role_query_text(role_profile)

    target_role = _get_field(role_profile, "target_role")
    level = _get_field(role_profile, "level")
    location = _get_field(role_profile, "location")
    accept_remote = _get_field(role_profile, "accept_remote")
    skills_list = _parse_list_field(_get_field(role_profile, "skills"))

    parts: list[str] = []
    if target_role and str(target_role).strip():
        parts.append(f"Target role: {str(target_role).strip()}")
    if level and str(level).strip():
        parts.append(f"Level: {str(level).strip()}")
    if location and str(location).strip():
        parts.append(f"Location: {str(location).strip()}")
    if accept_remote:
        parts.append("Remote acceptable")
    if skills_list:
        parts.append(f"Skills: {', '.join(skills_list)}")
    parts.append(f"Active CV evidence:\n{str(active_cv_text).strip()}")
    return "\n".join(parts)
```

- [ ] **Step 5: Add memory active CV context**

In `backend/app/services/chat_memory_service.py`, update model imports:

```python
from app.db.models import (
    ChatConversation,
    ChatMessage,
    MemorySummary,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
    RoleProfile,
)
```

Inside `assemble`, after the `role_profile` `BudgetItem`, add:

```python
        active_cv_text = await self._get_active_cv_context(
            session,
            role_profile_id=conversation.role_profile_id,
            current_user_message=current_user_message,
        )
        if active_cv_text:
            items.append(
                BudgetItem(
                    key="active_cv",
                    text=active_cv_text,
                    tokens=self.token_counter.count(active_cv_text),
                    priority=78,
                )
            )
```

Add helper methods:

```python
    async def _get_active_cv_context(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        current_user_message: str,
    ) -> str | None:
        profile = await session.get(RoleProfile, role_profile_id)
        if profile is None or profile.active_cv_document_id is None or profile.active_cv_version_id is None:
            return None
        document = await session.get(ProfileDocument, profile.active_cv_document_id)
        version = await session.get(ProfileDocumentVersion, profile.active_cv_version_id)
        if document is None or version is None:
            return None
        chunks = await self._get_active_cv_chunks(
            session,
            role_profile_id=role_profile_id,
            document_id=document.id,
            version_id=version.id,
            query=current_user_message,
        )
        if not chunks:
            return f"Active CV: {document.original_filename}\nNo extracted active CV chunks available."
        body = "\n\n".join(chunk.text for chunk in chunks)
        return f"Active CV: {document.original_filename}\nVersion: {version.version_number}\n{body}"

    async def _get_active_cv_chunks(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        query: str,
    ) -> list[ProfileDocumentChunk]:
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.role_profile_id == role_profile_id)
            .where(ProfileDocumentChunk.document_id == document_id)
            .where(ProfileDocumentChunk.version_id == version_id)
            .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
            .limit(12)
        )
        chunks = list(result.scalars())
        terms = [term.lower() for term in query.split() if len(term) >= 3]
        if not terms:
            return chunks[:5]

        def score(chunk: ProfileDocumentChunk) -> int:
            text = chunk.text.lower()
            return sum(1 for term in terms if term in text)

        ranked = sorted(chunks, key=score, reverse=True)
        matches = [chunk for chunk in ranked if score(chunk) > 0]
        return (matches or chunks)[:5]
```

- [ ] **Step 6: Use active CV in job scoring**

In `backend/app/services/job_processing_service.py`, import:

```python
from app.db.models import ProfileDocumentChunk
```

Update scoring import:

```python
    build_role_query_text_with_cv_evidence,
```

Add helper before `_score_committed_job`:

```python
async def _load_active_cv_text_for_scoring(
    session: AsyncSession,
    role_profile: RoleProfile,
    *,
    max_chunks: int = 12,
) -> str | None:
    if role_profile.active_cv_document_id is None or role_profile.active_cv_version_id is None:
        return None
    result = await session.execute(
        select(ProfileDocumentChunk)
        .where(ProfileDocumentChunk.role_profile_id == role_profile.id)
        .where(ProfileDocumentChunk.document_id == role_profile.active_cv_document_id)
        .where(ProfileDocumentChunk.version_id == role_profile.active_cv_version_id)
        .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
        .limit(max_chunks)
    )
    chunks = list(result.scalars())
    if not chunks:
        return None
    return "\n\n".join(chunk.text for chunk in chunks)
```

In `_score_committed_job`, replace:

```python
    role_query_text = build_role_query_text(role_profile)
```

with:

```python
    active_cv_text = await _load_active_cv_text_for_scoring(session, role_profile)
    role_query_text = build_role_query_text_with_cv_evidence(role_profile, active_cv_text)
```

- [ ] **Step 7: Run memory/scoring/job processing tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_scoring_service.py tests\test_chat_memory_service.py tests\test_job_processing_service.py -q
```

Expected: tests pass.

- [ ] **Step 8: Commit Task 5**

```powershell
git add backend/app/services/chat_memory_service.py backend/app/services/scoring_service.py backend/app/services/job_processing_service.py backend/tests/test_chat_memory_service.py backend/tests/test_scoring_service.py backend/tests/test_job_processing_service.py
git commit -m "feat: prefer active cv evidence in memory and scoring"
```

---

### Task 6: Final Phase 2 Verification

**Files:**
- Modify only if verification finds breakage.

- [ ] **Step 1: Run backend verification**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Expected:

- compileall exits `0`
- pytest reports all tests passed
- pip check reports `No broken requirements found.`

- [ ] **Step 2: Run frontend verification**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Expected:

- lint exits `0`; existing warnings are acceptable only if unchanged
- typecheck exits `0`
- tests pass
- build exits `0`

- [ ] **Step 3: Run CV tool safety scan**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
rg -n "retrieve_profile_cv_chunks|list_profile_cvs|get_active_profile_cv|view_profile_cv_metadata|analyze_cv_structure|safe_payload|stored_path|content_hash|OPENAI_API_KEY|api_key" backend\app frontend\job-agent-ui\src
```

Expected:

- CV tool safe payloads contain IDs, counts, statuses, filenames, and booleans only.
- Full CV text appears only in backend `ToolResult.content` or backend memory/scoring context, never in `safe_payload`.
- `stored_path` and `content_hash` remain backend-only.
- no API keys appear in frontend code or tool safe payloads.

- [ ] **Step 4: Review final diff**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
git diff --check
git status --short
git diff --stat
```

Expected:

- no whitespace errors
- only Phase 2 files changed
- no draft/export/OCR code added
- no runtime demo/mock data introduced

- [ ] **Step 5: Commit verification cleanup if needed**

Only if Step 1-4 required cleanup edits:

```powershell
git add backend frontend docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-2.md
git commit -m "test: verify profile cv retrieval tools"
```
