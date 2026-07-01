# Profile CV PDF Export And Version Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export approved CV drafts into real stored PDF versions, let users view/download those versions, and promote an exported version to active CV only after explicit confirmation.

**Architecture:** Reuse the existing profile document/version tables, storage service, file-serving routes, draft service, tool registry, and React profile document panel. Add a focused PDF renderer, extract shared version indexing out of upload flow, then wire export through backend route, chat tool, and frontend version-history controls without overwriting original PDFs.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, SQLite, Qdrant, pypdf, reportlab, React, TypeScript, Vitest, oxlint.

---

## Source Documents

- `docs/superpowers/specs/2026-07-01-profile-cv-pdf-source-of-truth-design.md`
- `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-roadmap.md`
- `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-3.md`

## Current Baseline

Already available:

- `ProfileDocument`, `ProfileDocumentVersion`, `ProfileDocumentChunk`, `ProfileCvDraft`, and `ProfileCvImprovementSuggestion` models.
- Original PDF upload creates version 1 with `source_type="original_upload"`.
- Existing real PDF file routes:
  - `GET /api/role-profiles/{role_profile_id}/documents/{document_id}/file`
  - `GET /api/role-profiles/{role_profile_id}/documents/{document_id}/download`
  - `GET /api/role-profiles/{role_profile_id}/documents/{document_id}/versions/{version_id}/file`
  - `GET /api/role-profiles/{role_profile_id}/documents/{document_id}/versions/{version_id}/download`
- Existing activation route with confirmation:
  - `POST /api/role-profiles/{role_profile_id}/documents/{document_id}/versions/{version_id}/activate`
- Existing draft preview route:
  - `GET /api/role-profiles/{role_profile_id}/documents/{document_id}/drafts/{draft_id}/preview`
- Existing frontend functions for list, upload, view, download, activate, delete, suggestions, drafts, and draft preview.

Phase 4 must keep these behaviors:

- The original uploaded PDF is immutable.
- Export creates a new `ProfileDocumentVersion` with `source_type="exported_draft"`.
- Export does not change `RoleProfile.active_cv_document_id`, `RoleProfile.active_cv_version_id`, or `ProfileDocument.active_version_id`.
- Active version promotion requires `confirmed: true`.
- Frontend safe payloads and tool-call safe payloads must not include full CV text.

## File Structure

Create:

- `backend/app/services/cv_pdf_export_service.py`
  Renders a draft preview into a real PDF file using a clean supported template.

- `backend/app/services/profile_document_indexing_service.py`
  Owns chunking, token counting, embedding, `ProfileDocumentChunk` persistence, and Qdrant upsert for any profile document version.

- `backend/app/services/profile_cv_export_service.py`
  Orchestrates draft-to-PDF export: validate draft, render PDF, store PDF, create version metadata, extract text, index chunks, mark draft exported.

- `backend/tests/test_cv_pdf_export_service.py`
- `backend/tests/test_profile_document_indexing_service.py`
- `backend/tests/test_profile_cv_export_service.py`

Modify:

- `backend/requirements.txt`
  Add `reportlab>=4.2,<5`.

- `backend/app/services/profile_document_service.py`
  Delegate upload indexing to `ProfileDocumentIndexingService`.

- `backend/app/services/profile_document_storage_service.py`
  Add a small `write_pdf_bytes(...)` helper only if rendering directly to bytes is cleaner than copying a temporary PDF. Prefer reusing `copy_pdf(...)` if the exporter writes to a temporary file.

- `backend/app/api/schemas.py`
  Add `CvDraftExportRequest`.

- `backend/app/api/routes_profile_documents.py`
  Add the draft export route and instantiate `ProfileCvExportService`.

- `backend/app/services/tool_registry.py`
  Register `export_cv_draft_to_pdf` and `set_active_cv_version`; add handlers with safe payloads.

- `backend/app/api/routes_chat.py`
  Wire the new tool handlers into the chat registry.

- `backend/tests/test_routes_profile_documents.py`
- `backend/tests/test_tool_registry.py`

- `frontend/job-agent-ui/src/types/profileDocuments.ts`
  Add `ExportCvDraftPayload`.

- `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`
  Add exported-version file URL helpers and `exportCvDraftToPdf(...)`.

- `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
  Load/render version history and add export/view/download/set-active controls.

- `frontend/job-agent-ui/src/styles/app.css`
- `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`
- `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`

## Task 1: Add PDF Renderer Dependency And Service

**Files:**

- Modify: `backend/requirements.txt`
- Create: `backend/app/services/cv_pdf_export_service.py`
- Test: `backend/tests/test_cv_pdf_export_service.py`

- [ ] **Step 1: Write the failing PDF renderer test**

Create `backend/tests/test_cv_pdf_export_service.py`:

```python
from pathlib import Path

from pypdf import PdfReader

from app.services.cv_pdf_export_service import CvPdfExportService


def test_write_pdf_creates_real_pdf_with_preview_content(tmp_path: Path) -> None:
    output_path = tmp_path / "draft-export.pdf"
    preview = {
        "title": "AI Engineer CV Draft",
        "sections": [
            {
                "heading": "Summary",
                "content": "Python, FastAPI, retrieval augmented generation, and LangGraph.",
            },
            {
                "heading": "Projects",
                "content": "Built an AI job agent that ranks roles against a CV.",
            },
        ],
        "edits": [
            {
                "requirement": "RAG experience",
                "proposed_edit": "Emphasize retrieval augmented generation project evidence.",
                "edit_kind": "wording_only",
                "risk_level": "low",
            }
        ],
        "recommendation": None,
    }

    CvPdfExportService().write_pdf(output_path, preview)

    assert output_path.read_bytes().startswith(b"%PDF")
    reader = PdfReader(str(output_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "AI Engineer CV Draft" in text
    assert "FastAPI" in text
    assert "RAG experience" in text
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_cv_pdf_export_service.py -q
```

Expected: FAIL because `app.services.cv_pdf_export_service` does not exist.

- [ ] **Step 3: Add the PDF dependency**

Append to `backend/requirements.txt`:

```text
reportlab>=4.2,<5
```

Install the updated backend requirements before the next test run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: pip installs `reportlab` and keeps existing packages.

- [ ] **Step 4: Add the renderer service**

Create `backend/app/services/cv_pdf_export_service.py`:

```python
"""Render editable CV draft previews into real PDF files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class CvPdfExportService:
    """Writes a clean supported-template PDF from a draft preview."""

    def write_pdf(self, output_path: Path, preview: dict[str, Any]) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        styles = getSampleStyleSheet()
        title = str(preview.get("title") or "CV draft").strip() or "CV draft"
        story: list[Any] = [Paragraph(title, styles["Title"]), Spacer(1, 0.18 * inch)]

        recommendation = preview.get("recommendation")
        if recommendation:
            story.extend(
                [
                    Paragraph("Template recommendation", styles["Heading2"]),
                    Paragraph(str(recommendation), styles["BodyText"]),
                    Spacer(1, 0.12 * inch),
                ]
            )

        for section in preview.get("sections", []):
            if not isinstance(section, dict):
                continue
            heading = str(section.get("heading") or "Section").strip() or "Section"
            content = str(section.get("content") or "").strip()
            if not content:
                continue
            story.append(Paragraph(heading, styles["Heading2"]))
            for paragraph in content.splitlines():
                clean = paragraph.strip()
                if clean:
                    story.append(Paragraph(clean, styles["BodyText"]))
            story.append(Spacer(1, 0.12 * inch))

        edits = [edit for edit in preview.get("edits", []) if isinstance(edit, dict)]
        if edits:
            story.append(Paragraph("Applied edit plan", styles["Heading2"]))
            for edit in edits:
                requirement = str(edit.get("requirement") or "Requirement").strip()
                proposed_edit = str(edit.get("proposed_edit") or "").strip()
                if proposed_edit:
                    story.append(Paragraph(f"{requirement}: {proposed_edit}", styles["BodyText"]))

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=LETTER,
            rightMargin=0.72 * inch,
            leftMargin=0.72 * inch,
            topMargin=0.72 * inch,
            bottomMargin=0.72 * inch,
        )
        document.build(story)
        return output_path
```

- [ ] **Step 5: Run the renderer test and commit**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_cv_pdf_export_service.py -q
```

Expected: PASS.

Commit:

```powershell
git add backend/requirements.txt backend/app/services/cv_pdf_export_service.py backend/tests/test_cv_pdf_export_service.py
git commit -m "feat: add cv pdf export renderer"
```

## Task 2: Extract Shared Profile Document Version Indexing

**Files:**

- Create: `backend/app/services/profile_document_indexing_service.py`
- Modify: `backend/app/services/profile_document_service.py`
- Test: `backend/tests/test_profile_document_indexing_service.py`
- Test: existing `backend/tests/test_routes_profile_documents.py`

- [ ] **Step 1: Write the failing indexing service tests**

Create `backend/tests/test_profile_document_indexing_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.db.models import ProfileDocument, ProfileDocumentVersion
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
    db_session.add_all([document, version])
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
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_document_indexing_service.py -q
```

Expected: FAIL because the indexing service does not exist.

- [ ] **Step 3: Add the shared indexing service**

Create `backend/app/services/profile_document_indexing_service.py`:

```python
"""Shared chunking, embedding, and vector indexing for profile document versions."""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfileDocumentChunk
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.token_budget_service import SimpleTokenCounter


class TextEmbedder(Protocol):
    async def embed_text(self, text: str) -> list[float]:
        ...


class ProfileDocumentVectorStore(Protocol):
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
        ...


class ProfileDocumentIndexingService:
    def __init__(
        self,
        *,
        token_counter: SimpleTokenCounter | None = None,
        embedder: TextEmbedder | None = None,
        vector_store: ProfileDocumentVectorStore | None = None,
    ) -> None:
        self.token_counter = token_counter or SimpleTokenCounter()
        self.embedder = embedder or EmbeddingService()
        self.vector_store = vector_store or QdrantService()

    def chunk_text(
        self,
        text: str,
        *,
        max_chars: int = 1800,
        overlap_chars: int = 200,
    ) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(text):
                break
            start = max(0, end - overlap_chars)
        return chunks

    async def index_extracted_text(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        text: str,
    ) -> int:
        chunks = self.chunk_text(text)
        if not chunks:
            raise ValueError("PDF does not contain enough extractable text")

        for index, chunk_text in enumerate(chunks):
            chunk_id = str(uuid4())
            chunk = ProfileDocumentChunk(
                id=chunk_id,
                document_id=document_id,
                role_profile_id=role_profile_id,
                version_id=version_id,
                source_type="profile_cv",
                chunk_index=index,
                text=chunk_text,
                token_count=self.token_counter.count(chunk_text),
                qdrant_point_id=str(uuid4()),
            )
            vector = await self.embedder.embed_text(chunk_text)
            await self.vector_store.upsert_profile_document_chunk(
                point_id=chunk.qdrant_point_id,
                role_profile_id=role_profile_id,
                document_id=document_id,
                version_id=version_id,
                chunk_id=chunk_id,
                chunk_index=index,
                vector=vector,
            )
            session.add(chunk)
        return len(chunks)
```

- [ ] **Step 4: Refactor upload indexing to reuse the service**

Modify `backend/app/services/profile_document_service.py`:

```python
from app.services.profile_document_indexing_service import ProfileDocumentIndexingService
```

In `ProfileDocumentService.__init__`, replace the separate token/embed/vector indexing ownership with:

```python
        indexing_service: ProfileDocumentIndexingService | None = None,
```

and:

```python
        self.indexing_service = indexing_service or ProfileDocumentIndexingService(
            token_counter=token_counter,
            embedder=embedder,
            vector_store=vector_store,
        )
```

Replace the manual loop in `create_document_from_pdf(...)` with:

```python
            text = self.extractor.extract_text(stored_path)
            chunk_count = await self.indexing_service.index_extracted_text(
                session,
                role_profile_id=role_profile_id,
                document_id=document.id,
                version_id=version.id,
                text=text,
            )
            document.extracted_text_chars = len(text)
            document.chunk_count = chunk_count
            version.extracted_text_chars = len(text)
            version.chunk_count = chunk_count
```

Remove the private `_chunk_text(...)` method after the route and service tests pass.

- [ ] **Step 5: Run focused backend tests and commit**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_document_indexing_service.py tests/test_routes_profile_documents.py -q
```

Expected: PASS.

Commit:

```powershell
git add backend/app/services/profile_document_indexing_service.py backend/app/services/profile_document_service.py backend/tests/test_profile_document_indexing_service.py
git commit -m "refactor: share profile document version indexing"
```

## Task 3: Add Draft-To-PDF Export Service

**Files:**

- Create: `backend/app/services/profile_cv_export_service.py`
- Test: `backend/tests/test_profile_cv_export_service.py`

- [ ] **Step 1: Write failing export service tests**

Create `backend/tests/test_profile_cv_export_service.py` with three tests:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from app.db.models import ProfileCvDraft, ProfileDocument, ProfileDocumentVersion, RoleProfile
from app.services.profile_cv_export_service import ExportCvDraftRequest, ProfileCvExportService
from app.services.profile_document_storage_service import ProfileDocumentStorageService


class FakeExtractor:
    def extract_text(self, path: Path) -> str:
        return "Exported CV text with FastAPI and LangGraph evidence."


class FakeStructureExtractor:
    def analyze(self, text: str):
        class Result:
            status = "reliable"
            confidence = 0.9
        return Result()


class FakeIndexer:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def index_extracted_text(self, session, **kwargs):
        self.calls.append(kwargs)
        return 1


@pytest.mark.asyncio
async def test_export_draft_creates_exported_version_without_activating(db_session, tmp_path: Path) -> None:
    profile = RoleProfile(id="profile-1", name="AI Engineer", target_role="AI Engineer")
    document = ProfileDocument(
        id="doc-1",
        role_profile_id="profile-1",
        original_filename="cv.pdf",
        stored_path=str(tmp_path / "original.pdf"),
        content_hash="original",
        mime_type="application/pdf",
        file_size_bytes=100,
        document_kind="cv",
        active_version_id="version-1",
        status="ready",
    )
    version = ProfileDocumentVersion(
        id="version-1",
        document_id="doc-1",
        role_profile_id="profile-1",
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path=str(tmp_path / "original.pdf"),
        content_hash="original",
        mime_type="application/pdf",
        file_size_bytes=100,
        extraction_status="ready",
        structure_status="reliable",
        created_by="user",
    )
    draft = ProfileCvDraft(
        id="draft-1",
        role_profile_id="profile-1",
        document_id="doc-1",
        base_version_id="version-1",
        status="draft",
        title="AI Engineer draft",
        structure_json='{"sections":[{"heading":"Summary","content":"FastAPI and LangGraph"}],"recommendation":null}',
        edit_plan_json='{"edits":[{"requirement":"Backend","proposed_edit":"Highlight FastAPI"}]}',
        structure_status_at_creation="reliable",
        created_by="ai",
    )
    profile.active_cv_document_id = "doc-1"
    profile.active_cv_version_id = "version-1"
    db_session.add_all([profile, document, version, draft])
    await db_session.commit()

    indexer = FakeIndexer()
    service = ProfileCvExportService(
        storage=ProfileDocumentStorageService(root_dir=tmp_path / "storage"),
        extractor=FakeExtractor(),
        structure_extractor=FakeStructureExtractor(),
        indexing_service=indexer,
    )

    exported = await service.export_draft_to_pdf(
        db_session,
        ExportCvDraftRequest(
            role_profile_id="profile-1",
            document_id="doc-1",
            draft_id="draft-1",
            confirmed=True,
        ),
    )

    assert exported.source_type == "exported_draft"
    assert exported.parent_version_id == "version-1"
    assert exported.draft_id == "draft-1"
    assert exported.version_number == 2
    assert exported.extraction_status == "ready"
    assert Path(exported.stored_path).read_bytes().startswith(b"%PDF")
    assert indexer.calls[0]["version_id"] == exported.id
    await db_session.refresh(profile)
    await db_session.refresh(document)
    await db_session.refresh(draft)
    assert profile.active_cv_version_id == "version-1"
    assert document.active_version_id == "version-1"
    assert draft.status == "exported"


@pytest.mark.asyncio
async def test_export_draft_requires_confirmation(db_session) -> None:
    service = ProfileCvExportService()

    with pytest.raises(ValueError, match="requires confirmation"):
        await service.export_draft_to_pdf(
            db_session,
            ExportCvDraftRequest(
                role_profile_id="profile-1",
                document_id="doc-1",
                draft_id="draft-1",
                confirmed=False,
            ),
        )


@pytest.mark.asyncio
async def test_export_draft_rejects_wrong_document_scope(db_session) -> None:
    db_session.add(
        ProfileCvDraft(
            id="draft-1",
            role_profile_id="profile-1",
            document_id="doc-2",
            base_version_id="version-1",
            status="draft",
            title="Draft",
            structure_json='{"sections":[]}',
            edit_plan_json='{"edits":[]}',
            structure_status_at_creation="reliable",
            created_by="ai",
        )
    )
    await db_session.commit()

    with pytest.raises(LookupError, match="CV draft not found"):
        await ProfileCvExportService().export_draft_to_pdf(
            db_session,
            ExportCvDraftRequest(
                role_profile_id="profile-1",
                document_id="doc-1",
                draft_id="draft-1",
                confirmed=True,
            ),
        )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_export_service.py -q
```

Expected: FAIL because `ProfileCvExportService` does not exist.

- [ ] **Step 3: Add the export orchestration service**

Create `backend/app/services/profile_cv_export_service.py`:

```python
"""Export editable CV drafts into stored PDF document versions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfileCvDraft, ProfileDocument, ProfileDocumentVersion
from app.services.cv_pdf_export_service import CvPdfExportService
from app.services.cv_structure_extraction_service import CvStructureExtractionService
from app.services.pdf_text_extraction_service import PdfTextExtractionService
from app.services.profile_document_indexing_service import ProfileDocumentIndexingService
from app.services.profile_document_storage_service import ProfileDocumentStorageService


@dataclass(frozen=True)
class ExportCvDraftRequest:
    role_profile_id: str
    document_id: str
    draft_id: str
    confirmed: bool
    created_by: str = "ai"


class ProfileCvExportService:
    def __init__(
        self,
        *,
        pdf_exporter: CvPdfExportService | None = None,
        storage: ProfileDocumentStorageService | None = None,
        extractor: PdfTextExtractionService | None = None,
        structure_extractor: CvStructureExtractionService | None = None,
        indexing_service: ProfileDocumentIndexingService | None = None,
    ) -> None:
        self.pdf_exporter = pdf_exporter or CvPdfExportService()
        self.storage = storage or ProfileDocumentStorageService()
        self.extractor = extractor or PdfTextExtractionService()
        self.structure_extractor = structure_extractor or CvStructureExtractionService()
        self.indexing_service = indexing_service or ProfileDocumentIndexingService()

    async def export_draft_to_pdf(
        self,
        session: AsyncSession,
        request: ExportCvDraftRequest,
    ) -> ProfileDocumentVersion:
        if not request.confirmed:
            raise ValueError("Exporting a CV draft to PDF requires confirmation.")

        document = await session.get(ProfileDocument, request.document_id)
        draft = await session.get(ProfileCvDraft, request.draft_id)
        if (
            document is None
            or draft is None
            or document.role_profile_id != request.role_profile_id
            or draft.role_profile_id != request.role_profile_id
            or draft.document_id != request.document_id
        ):
            raise LookupError("CV draft not found")
        if draft.status != "draft":
            raise ValueError("Only draft CVs can be exported.")

        base_version = await session.get(ProfileDocumentVersion, draft.base_version_id)
        if base_version is None or base_version.document_id != document.id:
            raise LookupError("Base CV version not found")

        version_id = str(uuid4())
        preview = {
            "draft_id": draft.id,
            "title": draft.title,
            "status": draft.status,
            "structure_status": draft.structure_status_at_creation,
            **json.loads(draft.structure_json),
            **json.loads(draft.edit_plan_json),
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            rendered_path = Path(tmp_dir) / f"{version_id}.pdf"
            self.pdf_exporter.write_pdf(rendered_path, preview)
            stored_path = self.storage.copy_pdf(
                rendered_path,
                role_profile_id=request.role_profile_id,
                document_id=request.document_id,
                version_id=version_id,
                directory_name="versions",
            )

        pdf_bytes = stored_path.read_bytes()
        content_hash = hashlib.sha256(pdf_bytes).hexdigest()
        next_number = await self._next_version_number(session, document_id=request.document_id)
        exported = ProfileDocumentVersion(
            id=version_id,
            document_id=document.id,
            role_profile_id=request.role_profile_id,
            version_number=next_number,
            source_type="exported_draft",
            parent_version_id=base_version.id,
            draft_id=draft.id,
            display_name=f"Exported draft v{next_number}",
            filename=f"{Path(document.original_filename).stem}-draft-v{next_number}.pdf",
            stored_path=str(stored_path),
            content_hash=content_hash,
            mime_type="application/pdf",
            file_size_bytes=len(pdf_bytes),
            extraction_status="processing",
            structure_status="not_extracted",
            created_by=request.created_by,
        )
        session.add(exported)
        await session.flush()

        text = self.extractor.extract_text(stored_path)
        chunk_count = await self.indexing_service.index_extracted_text(
            session,
            role_profile_id=request.role_profile_id,
            document_id=document.id,
            version_id=exported.id,
            text=text,
        )
        structure = self.structure_extractor.analyze(text)
        exported.extracted_text_chars = len(text)
        exported.chunk_count = chunk_count
        exported.extraction_status = "ready"
        exported.structure_status = structure.status
        exported.structure_confidence = structure.confidence
        draft.status = "exported"
        await session.commit()
        await session.refresh(exported)
        return exported

    @staticmethod
    async def _next_version_number(session: AsyncSession, *, document_id: str) -> int:
        result = await session.execute(
            select(func.max(ProfileDocumentVersion.version_number)).where(
                ProfileDocumentVersion.document_id == document_id
            )
        )
        current = result.scalar_one_or_none() or 0
        return int(current) + 1
```

- [ ] **Step 4: Run export service tests and commit**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_export_service.py tests/test_profile_document_indexing_service.py -q
```

Expected: PASS.

Commit:

```powershell
git add backend/app/services/profile_cv_export_service.py backend/tests/test_profile_cv_export_service.py
git commit -m "feat: export cv drafts as pdf versions"
```

## Task 4: Expose Export API Route

**Files:**

- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/api/routes_profile_documents.py`
- Test: `backend/tests/test_routes_profile_documents.py`

- [ ] **Step 1: Add route tests first**

Append tests to `backend/tests/test_routes_profile_documents.py`:

```python
@pytest.mark.asyncio
async def test_export_cv_draft_requires_confirmation(client, role_profile):
    document, version = await upload_ready_profile_document(client, role_profile)
    draft_response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions/{version['id']}/drafts",
        json={"title": "Export draft", "suggestion_ids": [], "confirmed": True},
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()

    response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/drafts/{draft['id']}/export-pdf",
        json={"confirmed": False},
    )

    assert response.status_code == 409
    assert "requires confirmation" in response.json()["detail"]


@pytest.mark.asyncio
async def test_export_cv_draft_returns_exported_version(client, role_profile):
    document, version = await upload_ready_profile_document(client, role_profile)
    draft_response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions/{version['id']}/drafts",
        json={"title": "Export draft", "suggestion_ids": [], "confirmed": True},
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()

    response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/drafts/{draft['id']}/export-pdf",
        json={"confirmed": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document["id"]
    assert body["source_type"] == "exported_draft"
    assert body["draft_id"] == draft["id"]
    assert body["extraction_status"] == "ready"

    versions_response = await client.get(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions"
    )
    assert versions_response.status_code == 200
    versions = versions_response.json()["versions"]
    assert [item["version_number"] for item in versions] == [2, 1]
```

- [ ] **Step 2: Run the route tests and verify they fail**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_routes_profile_documents.py -q
```

Expected: FAIL because the export route and schema do not exist.

- [ ] **Step 3: Add the request schema**

Modify `backend/app/api/schemas.py` near `CvDraftCreateRequest`:

```python
class CvDraftExportRequest(ApiSchema):
    confirmed: bool = False
```

Ensure `ProfileDocumentVersionResponse` exposes these existing fields:

```python
parent_version_id: str | None = None
draft_id: str | None = None
```

If those fields are missing, add them to the response model so the frontend can link exported versions to drafts.

- [ ] **Step 4: Add the export route**

Modify imports in `backend/app/api/routes_profile_documents.py`:

```python
from app.api.schemas import CvDraftExportRequest
from app.services.profile_cv_export_service import ExportCvDraftRequest, ProfileCvExportService
```

Add singleton:

```python
profile_cv_export_service = ProfileCvExportService()
```

Add route after draft preview:

```python
@router.post("/{document_id}/drafts/{draft_id}/export-pdf", response_model=ProfileDocumentVersionResponse)
async def export_cv_draft_pdf(
    role_profile_id: UUID,
    document_id: UUID,
    draft_id: UUID,
    request: CvDraftExportRequest,
    session: SessionDep,
) -> ProfileDocumentVersionResponse:
    await _require_profile(session, str(role_profile_id))
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exporting a CV draft to PDF requires confirmation.",
        )
    try:
        return await profile_cv_export_service.export_draft_to_pdf(
            session,
            ExportCvDraftRequest(
                role_profile_id=str(role_profile_id),
                document_id=str(document_id),
                draft_id=str(draft_id),
                confirmed=request.confirmed,
                created_by="ai",
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
```

- [ ] **Step 5: Run route tests and commit**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_routes_profile_documents.py tests/test_profile_cv_export_service.py -q
```

Expected: PASS.

Commit:

```powershell
git add backend/app/api/schemas.py backend/app/api/routes_profile_documents.py backend/tests/test_routes_profile_documents.py
git commit -m "feat: expose cv draft pdf export api"
```

## Task 5: Add Agent Tools For Export And Active Version Promotion

**Files:**

- Modify: `backend/app/services/tool_registry.py`
- Modify: `backend/app/api/routes_chat.py`
- Test: `backend/tests/test_tool_registry.py`

- [ ] **Step 1: Write failing tool registry tests**

Append to `backend/tests/test_tool_registry.py`:

```python
import pytest

from app.services.profile_cv_export_service import ExportCvDraftRequest
from app.services.tool_registry import ToolRegistry, ToolRequest, build_export_cv_draft_to_pdf_handler, build_set_active_cv_version_handler


def test_cv_export_and_active_tools_require_confirmation():
    tools = ToolRegistry().list_tools()

    assert tools["export_cv_draft_to_pdf"].requires_confirmation is True
    assert tools["set_active_cv_version"].requires_confirmation is True


@pytest.mark.asyncio
async def test_export_cv_draft_tool_returns_safe_payload():
    class ExportService:
        async def export_draft_to_pdf(self, session, request: ExportCvDraftRequest):
            assert request.confirmed is True
            class Version:
                id = "version-2"
                document_id = "doc-1"
                version_number = 2
                source_type = "exported_draft"
                extraction_status = "ready"
                structure_status = "reliable"
                structure_confidence = 0.91
            return Version()

    handler = build_export_cv_draft_to_pdf_handler(ExportService(), object())
    result = await handler(
        ToolRequest(
            name="export_cv_draft_to_pdf",
            arguments={"draft_id": "draft-1", "confirmed": True},
            context={"role_profile_id": "profile-1", "document_id": "doc-1"},
        )
    )

    assert result.result_summary == "Exported CV draft as PDF version 2"
    assert result.safe_payload == {
        "document_id": "doc-1",
        "version_id": "version-2",
        "version_number": 2,
        "source_type": "exported_draft",
        "extraction_status": "ready",
        "structure_status": "reliable",
        "structure_confidence": 0.91,
    }


@pytest.mark.asyncio
async def test_set_active_cv_version_tool_returns_safe_payload():
    class DocumentService:
        async def set_active_version(self, session, **kwargs):
            assert kwargs["confirmed"] is True
            class Version:
                id = "version-2"
                document_id = "doc-1"
                version_number = 2
                source_type = "exported_draft"
                extraction_status = "ready"
                structure_status = "reliable"
                structure_confidence = 0.91
            return Version()

    handler = build_set_active_cv_version_handler(DocumentService(), object())
    result = await handler(
        ToolRequest(
            name="set_active_cv_version",
            arguments={"version_id": "version-2", "confirmed": True},
            context={"role_profile_id": "profile-1", "document_id": "doc-1"},
        )
    )

    assert result.result_summary == "Set CV version 2 active"
    assert result.safe_payload["version_id"] == "version-2"
    assert "FastAPI" not in str(result.safe_payload)
```

- [ ] **Step 2: Run tool tests and verify they fail**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py -q
```

Expected: FAIL because the new tools and handlers do not exist.

- [ ] **Step 3: Register tool definitions**

Modify `ToolRegistry.__init__` in `backend/app/services/tool_registry.py`:

```python
            "export_cv_draft_to_pdf": ToolDefinition(
                name="export_cv_draft_to_pdf",
                description="Export an approved CV edit draft into a real PDF version without activating it.",
                requires_confirmation=True,
                handler=_not_wired,
            ),
            "set_active_cv_version": ToolDefinition(
                name="set_active_cv_version",
                description="Set a profile CV version as the active source of truth after confirmation.",
                requires_confirmation=True,
                handler=_not_wired,
            ),
```

- [ ] **Step 4: Add tool handlers**

Add imports:

```python
from app.services.profile_cv_export_service import ExportCvDraftRequest
```

Add handlers:

```python
def build_export_cv_draft_to_pdf_handler(
    export_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        version = await export_service.export_draft_to_pdf(
            session,
            ExportCvDraftRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                document_id=str(request.context["document_id"]),
                draft_id=str(request.arguments["draft_id"]),
                confirmed=bool(request.arguments.get("confirmed", False)),
                created_by="ai",
            ),
        )
        return ToolResult(
            content="Exported the CV draft as a new PDF version. The active CV was not changed.",
            result_summary=f"Exported CV draft as PDF version {version.version_number}",
            safe_payload={
                "document_id": version.document_id,
                "version_id": version.id,
                "version_number": version.version_number,
                "source_type": version.source_type,
                "extraction_status": version.extraction_status,
                "structure_status": version.structure_status,
                "structure_confidence": version.structure_confidence,
            },
        )

    return handler


def build_set_active_cv_version_handler(
    document_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        version = await document_service.set_active_version(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            document_id=str(request.context["document_id"]),
            version_id=str(request.arguments["version_id"]),
            confirmed=bool(request.arguments.get("confirmed", False)),
        )
        return ToolResult(
            content="Set the selected CV version as the active profile CV source of truth.",
            result_summary=f"Set CV version {version.version_number} active",
            safe_payload={
                "document_id": version.document_id,
                "version_id": version.id,
                "version_number": version.version_number,
                "source_type": version.source_type,
                "extraction_status": version.extraction_status,
                "structure_status": version.structure_status,
                "structure_confidence": version.structure_confidence,
            },
        )

    return handler
```

- [ ] **Step 5: Wire chat routes**

Modify `backend/app/api/routes_chat.py` imports:

```python
from app.services.profile_cv_export_service import ProfileCvExportService
from app.services.profile_document_service import ProfileDocumentService
from app.services.tool_registry import build_export_cv_draft_to_pdf_handler, build_set_active_cv_version_handler
```

Add singletons:

```python
profile_cv_export_service = ProfileCvExportService()
profile_document_service = ProfileDocumentService()
```

Add overrides in `build_tool_registry(...)`:

```python
            "export_cv_draft_to_pdf": build_export_cv_draft_to_pdf_handler(profile_cv_export_service, session),
            "set_active_cv_version": build_set_active_cv_version_handler(profile_document_service, session),
```

- [ ] **Step 6: Run tool tests and commit**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py tests/test_routes_profile_documents.py -q
```

Expected: PASS.

Commit:

```powershell
git add backend/app/services/tool_registry.py backend/app/api/routes_chat.py backend/tests/test_tool_registry.py
git commit -m "feat: add cv export agent tools"
```

## Task 6: Add Frontend Version History And Export Controls

**Files:**

- Modify: `frontend/job-agent-ui/src/types/profileDocuments.ts`
- Modify: `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`
- Modify: `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
- Modify: `frontend/job-agent-ui/src/styles/app.css`
- Test: `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`
- Test: `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`

- [ ] **Step 1: Write failing frontend API tests**

Update imports in `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`:

```ts
import {
  exportCvDraftToPdf,
  getProfileDocumentVersionDownloadUrl,
  getProfileDocumentVersionFileUrl,
} from "../api/profileDocumentsClient";
```

Append tests:

```ts
it("builds version file and download URLs", () => {
  expect(getProfileDocumentVersionFileUrl("profile-1", "doc-1", "version-2")).toBe(
    "http://localhost:8000/api/role-profiles/profile-1/documents/doc-1/versions/version-2/file"
  );
  expect(getProfileDocumentVersionDownloadUrl("profile-1", "doc-1", "version-2")).toBe(
    "http://localhost:8000/api/role-profiles/profile-1/documents/doc-1/versions/version-2/download"
  );
});

it("exports a CV draft as PDF with confirmation", async () => {
  postSpy.mockResolvedValueOnce({ data: {
    id: "version-2",
    document_id: "doc-1",
    role_profile_id: "profile-1",
    version_number: 2,
    source_type: "exported_draft",
    display_name: "Exported draft v2",
    filename: "cv-draft-v2.pdf",
    mime_type: "application/pdf",
    file_size_bytes: 1000,
    extracted_text_chars: 80,
    chunk_count: 1,
    extraction_status: "ready",
    structure_status: "reliable",
    structure_confidence: 0.9,
    error_reason: null,
    created_by: "ai",
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
  } });

  const version = await exportCvDraftToPdf("profile-1", "doc-1", "draft-1", { confirmed: true });

  expect(postSpy).toHaveBeenCalledWith(
    "/api/role-profiles/profile-1/documents/doc-1/drafts/draft-1/export-pdf",
    { confirmed: true }
  );
  expect(version.id).toBe("version-2");
  expect(version.source_type).toBe("exported_draft");
});
```

- [ ] **Step 2: Add client types and functions**

Modify `frontend/job-agent-ui/src/types/profileDocuments.ts`:

```ts
export interface ExportCvDraftPayload {
  confirmed: boolean;
}
```

Modify `frontend/job-agent-ui/src/api/profileDocumentsClient.ts` imports:

```ts
  ExportCvDraftPayload,
```

Add helpers:

```ts
export function getProfileDocumentVersionFileUrl(roleProfileId: string, documentId: string, versionId: string): string {
  return resolveApiUrl(`/api/role-profiles/${roleProfileId}/documents/${documentId}/versions/${versionId}/file`);
}

export function getProfileDocumentVersionDownloadUrl(roleProfileId: string, documentId: string, versionId: string): string {
  return resolveApiUrl(`/api/role-profiles/${roleProfileId}/documents/${documentId}/versions/${versionId}/download`);
}

export async function exportCvDraftToPdf(
  roleProfileId: string,
  documentId: string,
  draftId: string,
  payload: ExportCvDraftPayload
): Promise<ProfileDocumentVersion> {
  try {
    const response = await apiClient.post<ProfileDocumentVersion>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/drafts/${draftId}/export-pdf`,
      payload
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
```

- [ ] **Step 3: Write failing panel tests**

Update the `vi.mock("../api/profileDocumentsClient", ...)` block in `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx` with these new mocks:

```tsx
  exportCvDraftToPdf: vi.fn(),
  getProfileDocumentVersionDownloadUrl: vi.fn(
    (profileId, documentId, versionId) =>
      `/api/role-profiles/${profileId}/documents/${documentId}/versions/${versionId}/download`
  ),
  getProfileDocumentVersionFileUrl: vi.fn(
    (profileId, documentId, versionId) =>
      `/api/role-profiles/${profileId}/documents/${documentId}/versions/${versionId}/file`
  ),
  listProfileDocumentVersions: vi.fn(),
```

Update the imports from `../api/profileDocumentsClient`:

```tsx
  exportCvDraftToPdf,
  listProfileDocumentVersions,
```

Update the type import:

```tsx
import type { CvDraft, ProfileDocument, ProfileDocumentVersion } from "../types/profileDocuments";
```

Add fixtures after `readyDocument`:

```tsx
const originalVersion: ProfileDocumentVersion = {
  id: "version-1",
  document_id: "doc-1",
  role_profile_id: "profile-1",
  version_number: 1,
  source_type: "original_upload",
  display_name: "Original upload",
  filename: "cv.pdf",
  mime_type: "application/pdf",
  file_size_bytes: 1000,
  extracted_text_chars: 500,
  chunk_count: 2,
  extraction_status: "ready",
  structure_status: "reliable",
  structure_confidence: 0.9,
  error_reason: null,
  created_by: "user",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const exportedVersion: ProfileDocumentVersion = {
  ...originalVersion,
  id: "version-2",
  version_number: 2,
  source_type: "exported_draft",
  display_name: "Exported draft v2",
  filename: "cv-draft-v2.pdf",
  created_by: "ai",
};

const draft: CvDraft = {
  id: "draft-1",
  role_profile_id: "profile-1",
  document_id: "doc-1",
  base_version_id: "version-1",
  status: "draft",
  title: "Draft",
  structure_status_at_creation: "reliable",
  created_by: "ai",
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};
```

Append tests:

```tsx
it("renders version history with exported version controls", async () => {
  vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);
  vi.mocked(listProfileDocumentVersions).mockResolvedValue([originalVersion, exportedVersion]);
  vi.mocked(listCvSuggestions).mockResolvedValue([]);
  vi.mocked(listCvDrafts).mockResolvedValue([]);

  render(<ProfileDocumentPanel activeProfileId="profile-1" />);

  expect(await screen.findByText("Version history")).toBeInTheDocument();
  expect(screen.getByText("Exported draft v2")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /view exported draft v2/i })).toHaveAttribute(
    "href",
    expect.stringContaining("/versions/version-2/file")
  );
});

it("exports a draft and refreshes version history", async () => {
  window.confirm = vi.fn(() => true);
  vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);
  vi.mocked(listProfileDocumentVersions).mockResolvedValue([originalVersion]);
  vi.mocked(listCvSuggestions).mockResolvedValue([]);
  vi.mocked(listCvDrafts).mockResolvedValue([draft]);
  vi.mocked(exportCvDraftToPdf).mockResolvedValue(exportedVersion);

  render(<ProfileDocumentPanel activeProfileId="profile-1" />);
  fireEvent.click(await screen.findByRole("button", { name: /export .* PDF/i }));

  expect(exportCvDraftToPdf).toHaveBeenCalledWith("profile-1", readyDocument.id, draft.id, { confirmed: true });
});
```

- [ ] **Step 4: Load and render version history in the panel**

Modify imports in `ProfileDocumentPanel.tsx`:

```tsx
import { Download, Eye, FileText, Loader2, Star, Trash2, Upload } from "lucide-react";
import {
  exportCvDraftToPdf,
  getProfileDocumentVersionDownloadUrl,
  getProfileDocumentVersionFileUrl,
  listProfileDocumentVersions,
} from "../../api/profileDocumentsClient";
import type { ProfileDocumentVersion } from "../../types/profileDocuments";
```

Add state:

```tsx
const [versionsByDocument, setVersionsByDocument] = useState<Record<string, ProfileDocumentVersion[]>>({});
```

Update both document refresh paths to load versions:

```tsx
const versionEntries = await Promise.all(
  nextDocuments.map(async (document) => [document.id, await listProfileDocumentVersions(activeProfileId, document.id)] as const)
);
setVersionsByDocument(Object.fromEntries(versionEntries));
```

Add export handler:

```tsx
const handleExportDraft = async (document: ProfileDocument, draft: CvDraft) => {
  if (!activeProfileId) return;
  const confirmed = window.confirm("Export this CV draft as a new PDF version? The active CV will not change.");
  if (!confirmed) return;
  setError(null);
  try {
    await exportCvDraftToPdf(activeProfileId, document.id, draft.id, { confirmed: true });
    await refreshDocuments();
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to export CV draft");
  }
};
```

Add a version history block under each document action row:

```tsx
<div className="profile-document-subpanel">
  <div className="profile-document-subpanel-title">Version history</div>
  {(versionsByDocument[document.id] ?? []).map((version) => (
    <div key={version.id} className="profile-document-version-row">
      <div>
        <strong>{version.display_name}</strong>
        <small>
          v{version.version_number} - {version.source_type} - {version.extraction_status}
        </small>
      </div>
      <div className="profile-document-actions">
        <a
          href={getProfileDocumentVersionFileUrl(activeProfileId!, document.id, version.id)}
          target="_blank"
          rel="noreferrer"
          aria-label={`View ${version.display_name}`}
        >
          <Eye size={14} /> View
        </a>
        <a
          href={getProfileDocumentVersionDownloadUrl(activeProfileId!, document.id, version.id)}
          aria-label={`Download ${version.display_name}`}
        >
          <Download size={14} /> Download
        </a>
        {document.active_version_id !== version.id ? (
          <button
            type="button"
            onClick={() => void activateProfileDocumentVersion(activeProfileId!, document.id, version.id).then(refreshDocuments)}
            aria-label={`Set ${version.display_name} active`}
          >
            <Star size={14} /> Set active
          </button>
        ) : (
          <span className="document-active-badge">Active version</span>
        )}
      </div>
    </div>
  ))}
</div>
```

In the draft list, add:

```tsx
{draft.status === "draft" ? (
  <button
    type="button"
    onClick={() => void handleExportDraft(document, draft)}
    aria-label={`Export ${draft.title} PDF`}
  >
    <Upload size={14} /> Export PDF
  </button>
) : null}
```

- [ ] **Step 5: Add styles for version rows**

Modify `frontend/job-agent-ui/src/styles/app.css`:

```css
.profile-document-version-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 6px;
  padding: 8px 0;
  border-top: 1px solid var(--border-subtle);
}

.profile-document-version-row strong,
.profile-document-version-row small {
  display: block;
}

.profile-document-version-row small {
  color: var(--text-muted);
  font-size: 11px;
}
```

- [ ] **Step 6: Run frontend tests and commit**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/profileDocumentsClient.test.ts src/test/ProfileDocumentPanel.test.tsx
npm run typecheck
```

Expected: targeted tests PASS and typecheck PASS.

Commit:

```powershell
git add frontend/job-agent-ui/src/types/profileDocuments.ts frontend/job-agent-ui/src/api/profileDocumentsClient.ts frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx frontend/job-agent-ui/src/styles/app.css frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx
git commit -m "feat: show cv version history and export controls"
```

## Task 7: Full Verification And Plan Checkoff

**Files:**

- Modify: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-4.md`

- [ ] **Step 1: Run backend verification**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Expected:

- compileall exits 0
- pytest exits 0
- pip check reports no broken requirements

- [ ] **Step 2: Run frontend verification**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Expected:

- lint exits 0
- typecheck exits 0
- tests exit 0
- build exits 0
- Existing lint warnings are acceptable only if unchanged from prior phases.

- [ ] **Step 3: Run safety and stale-reference scans**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
rg -n "export_cv_draft_to_pdf|set_active_cv_version|export-pdf|exported_draft" backend frontend docs
rg -n "raw CV|full CV text|api_key|OPENAI_API_KEY|TAVILY_API_KEY" backend\app frontend\job-agent-ui\src
git diff --check
git status --short
```

Expected:

- new tool and route names appear only in service, route, tests, API client, frontend UI, and plan/docs
- no safe payload includes raw full CV text or secrets
- `git diff --check` exits 0
- `git status --short` shows only intentional files until the final plan checkoff commit

- [ ] **Step 4: Manually verify the Phase 4 flow**

Start backend and frontend:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host localhost --port 8000
```

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run dev -- --host localhost --port 5173
```

Manual flow:

1. Open `http://localhost:5173`.
2. Select a role profile with an uploaded CV.
3. Open a draft preview.
4. Click `Export PDF`.
5. Confirm the export.
6. Confirm a new exported version appears in Version history.
7. Click `View` for the exported version and verify the browser opens a PDF.
8. Click `Download` for the exported version and verify the downloaded file is a PDF.
9. Confirm the active CV badge stays on the old active version after export.
10. Click `Set active` on the exported version and confirm the active badge moves only after that action.

- [ ] **Step 5: Check off completed tasks and commit the plan update**

After every task above is complete and verified, update this plan file by changing each completed checkbox from `- [ ]` to `- [x]`.

Commit:

```powershell
git add docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-4.md
git commit -m "docs: complete profile cv pdf export phase"
```

## Acceptance Criteria

- `reportlab>=4.2,<5` is installed and verified by `pip check`.
- Draft export creates a new real PDF file under profile document storage.
- Export creates a `ProfileDocumentVersion` with:
  - `source_type="exported_draft"`
  - `parent_version_id` set to the draft base version
  - `draft_id` set to the exported draft
  - `created_by="ai"`
  - `extraction_status="ready"` after extraction succeeds
- Export indexes the exported version text into SQLite chunks and Qdrant with the exported `version_id`.
- Export marks the draft as `exported`.
- Export does not promote the exported version to active CV.
- Existing version file/download endpoints serve exported PDF versions without special-case routes.
- `export_cv_draft_to_pdf` and `set_active_cv_version` are registered as confirmation-required tools.
- Tool safe payloads include IDs, status, counts, version numbers, and structure metadata only.
- Frontend shows version history for each uploaded CV.
- Frontend can view, download, export, and promote versions.
- Original uploaded PDFs remain immutable and are never overwritten.

## Risks And Guardrails

- `reportlab` produces a clean supported-template PDF, not a pixel-perfect edit of the uploaded original. This matches the approved structure preservation rule because arbitrary uploaded PDF layout editing is outside the current reliable path.
- If exported PDF text extraction fails, the export route should return an error and leave the version marked failed only if a version row was already created. The service should not activate that version.
- If Qdrant upsert fails, the export should fail as indexing failed, matching upload behavior. Do not silently create an active-looking version without retrievable chunks.
- Do not add OCR.
- Do not add cloud storage.
- Do not change existing job scoring behavior in this phase.
- Do not expose full extracted CV text in frontend safe payloads or tool-call safe payloads.

## Final Verification Commands

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check

cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```
