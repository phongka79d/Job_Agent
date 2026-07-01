# Profile CV Structure And Drafts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic CV structure analysis, improvement suggestions, and editable draft previews without modifying original or exported PDF files.

**Architecture:** Extend the existing Phase 1/2 PDF source-of-truth foundation. Store structure metadata on `profile_document_versions`, add draft and suggestion SQLite tables, keep routes thin, put draft/suggestion logic in services, and expose only sanitized draft/suggestion metadata through tools and frontend APIs.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, SQLite idempotent migrations, existing chat tool registry, React, TypeScript, Vitest, pytest.

---

## Source Inputs

- Spec: `docs/superpowers/specs/2026-07-01-profile-cv-pdf-source-of-truth-design.md`
- Roadmap: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-roadmap.md`
- Phase 1: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-1.md`
- Phase 2: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-2.md`

## Phase 3 Scope

Implement:

- deterministic CV structure extraction from extracted text
- `structure_status`: `reliable`, `partial`, `unreliable`
- `profile_cv_drafts` table and draft service
- `profile_cv_improvement_suggestions` table and suggestion service
- tools:
  - `suggest_cv_improvements`
  - `create_cv_edit_draft`
  - `preview_cv_edit_draft`
- profile document draft/suggestion API routes
- frontend suggestion and draft preview panels
- required poor-structure template recommendation

Do not implement:

- PDF export
- active version promotion for drafts
- OCR
- pixel-perfect editing of arbitrary uploaded PDFs
- automatic AI rewriting without user confirmation

## File Structure

Modify:

- `backend/app/db/models.py`
  - Add `ProfileCvDraft` and `ProfileCvImprovementSuggestion`.
- `backend/app/db/session.py`
  - Add new tables to expected table guard.
- `backend/app/db/sqlite_migrations.py`
  - Create new tables idempotently for existing SQLite databases.
- `backend/app/services/profile_document_service.py`
  - Run structure extraction after text extraction and update version fields.
- `backend/app/services/tool_registry.py`
  - Register and implement Phase 3 CV suggestion/draft tools.
- `backend/app/api/routes_profile_documents.py`
  - Add draft/suggestion routes that delegate to services.
- `backend/app/api/schemas.py`
  - Add draft and suggestion request/response schemas.
- `backend/app/api/routes_chat.py`
  - Wire new tools into `build_tool_registry`.
- `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`
  - Add draft and suggestion API functions.
- `frontend/job-agent-ui/src/types/profileDocuments.ts`
  - Add draft and suggestion types.
- `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
  - Render suggestion and draft preview panels.

Create:

- `backend/app/services/cv_structure_extraction_service.py`
  - Deterministic text structure analyzer.
- `backend/app/services/profile_cv_draft_service.py`
  - Draft and suggestion persistence logic.
- `backend/tests/test_cv_structure_extraction_service.py`
  - Structure reliability tests.
- `backend/tests/test_profile_cv_draft_service.py`
  - Draft/suggestion service tests.

Test:

- `backend/tests/test_sqlite_migrations.py`
- `backend/tests/test_profile_document_service.py`
- `backend/tests/test_tool_registry.py`
- `backend/tests/test_routes_profile_documents.py`
- `backend/tests/test_routes_chat.py`
- `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`
- `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`

---

### Task 1: Add Draft And Suggestion Database Foundation

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/app/db/sqlite_migrations.py`
- Test: `backend/tests/test_profile_document_service.py`
- Test: `backend/tests/test_sqlite_migrations.py`

- [ ] **Step 1: Write failing model table tests**

Update `backend/tests/test_profile_document_service.py` imports:

```python
from app.db.models import (
    Base,
    ProfileCvDraft,
    ProfileCvImprovementSuggestion,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
    RoleProfile,
)
```

Extend the existing `test_profile_document_models_are_registered_with_metadata`:

```python
def test_profile_document_models_are_registered_with_metadata():
    assert "profile_documents" in Base.metadata.tables
    assert "profile_document_versions" in Base.metadata.tables
    assert "profile_document_chunks" in Base.metadata.tables
    assert "profile_cv_drafts" in Base.metadata.tables
    assert "profile_cv_improvement_suggestions" in Base.metadata.tables

    assert ProfileDocument.__tablename__ == "profile_documents"
    assert ProfileDocumentVersion.__tablename__ == "profile_document_versions"
    assert ProfileDocumentChunk.__tablename__ == "profile_document_chunks"
    assert ProfileCvDraft.__tablename__ == "profile_cv_drafts"
    assert ProfileCvImprovementSuggestion.__tablename__ == "profile_cv_improvement_suggestions"
```

- [ ] **Step 2: Write failing migration table tests**

Update `backend/tests/test_sqlite_migrations.py`.

In both migration tests, create the prerequisite tables before calling `apply_sqlite_migrations`:

```python
await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
await conn.execute(text("CREATE TABLE profile_document_versions (id VARCHAR(36) PRIMARY KEY)"))
```

Add helper:

```python
async def _table_names(conn):
    rows = (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).all()
    return {row[0] for row in rows}
```

Assert:

```python
tables = await _table_names(conn)
assert "profile_cv_drafts" in tables
assert "profile_cv_improvement_suggestions" in tables
```

Assert draft columns:

```python
draft_columns = await _columns(conn, "profile_cv_drafts")
assert {
    "id",
    "role_profile_id",
    "document_id",
    "base_version_id",
    "status",
    "title",
    "structure_json",
    "edit_plan_json",
    "structure_status_at_creation",
    "created_by",
    "created_at",
    "updated_at",
} <= draft_columns
```

Assert suggestion columns:

```python
suggestion_columns = await _columns(conn, "profile_cv_improvement_suggestions")
assert {
    "id",
    "role_profile_id",
    "document_id",
    "version_id",
    "job_id",
    "requirement",
    "current_cv_evidence",
    "missing_or_weak_evidence",
    "proposed_edit",
    "edit_kind",
    "risk_level",
    "requires_confirmation",
    "status",
    "created_at",
    "updated_at",
} <= suggestion_columns
```

- [ ] **Step 3: Run database tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py::test_profile_document_models_are_registered_with_metadata tests\test_sqlite_migrations.py -q
```

Expected: fail because `ProfileCvDraft`, `ProfileCvImprovementSuggestion`, and migration-created tables do not exist.

- [ ] **Step 4: Add ORM models**

In `backend/app/db/models.py`, add after `ProfileDocumentChunk`:

```python
class ProfileCvDraft(Base):
    """Editable CV draft created from a real profile document version."""
    __tablename__ = "profile_cv_drafts"

    __table_args__ = (
        Index("idx_profile_cv_drafts_role_profile_updated", "role_profile_id", text("updated_at DESC")),
        Index("idx_profile_cv_drafts_document_updated", "document_id", text("updated_at DESC")),
    )

    id: Mapped[uuid_pk]
    role_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("role_profiles.id"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profile_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    base_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profile_document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    structure_json: Mapped[str] = mapped_column(Text, nullable=False)
    edit_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    structure_status_at_creation: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False, default="ai")
    created_at: Mapped[created_timestamp]
    updated_at: Mapped[updated_timestamp]


class ProfileCvImprovementSuggestion(Base):
    """Targeted CV improvement suggestion grounded in existing CV evidence."""
    __tablename__ = "profile_cv_improvement_suggestions"

    __table_args__ = (
        Index("idx_profile_cv_suggestions_role_profile_status", "role_profile_id", "status"),
        Index("idx_profile_cv_suggestions_document_created", "document_id", text("created_at DESC")),
    )

    id: Mapped[uuid_pk]
    role_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("role_profiles.id"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profile_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profile_document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("job_posts.id", ondelete="SET NULL"),
        nullable=True,
    )
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    current_cv_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    missing_or_weak_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_edit: Mapped[str] = mapped_column(Text, nullable=False)
    edit_kind: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="suggested")
    created_at: Mapped[created_timestamp]
    updated_at: Mapped[updated_timestamp]
```

- [ ] **Step 5: Update expected database tables**

In `backend/app/db/session.py`, add to `expected_tables`:

```python
"profile_cv_drafts",
"profile_cv_improvement_suggestions",
```

- [ ] **Step 6: Add idempotent SQLite table migrations**

In `backend/app/db/sqlite_migrations.py`, add helper above `apply_sqlite_migrations`:

```python
async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    row = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        )
    ).first()
    return row is not None


async def _create_table_if_missing(
    conn: AsyncConnection,
    table_name: str,
    ddl: str,
) -> None:
    if await _table_exists(conn, table_name):
        return
    await conn.execute(text(ddl))
```

At the end of `apply_sqlite_migrations`, add:

```python
    await _create_table_if_missing(
        conn,
        "profile_cv_drafts",
        """
        CREATE TABLE profile_cv_drafts (
            id VARCHAR(36) PRIMARY KEY,
            role_profile_id VARCHAR(36) NOT NULL,
            document_id VARCHAR(36) NOT NULL,
            base_version_id VARCHAR(36) NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            title TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            edit_plan_json TEXT NOT NULL,
            structure_status_at_creation TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'ai',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """,
    )
    await _create_table_if_missing(
        conn,
        "profile_cv_improvement_suggestions",
        """
        CREATE TABLE profile_cv_improvement_suggestions (
            id VARCHAR(36) PRIMARY KEY,
            role_profile_id VARCHAR(36) NOT NULL,
            document_id VARCHAR(36) NOT NULL,
            version_id VARCHAR(36) NOT NULL,
            job_id VARCHAR(36),
            requirement TEXT NOT NULL,
            current_cv_evidence TEXT NOT NULL,
            missing_or_weak_evidence TEXT NOT NULL,
            proposed_edit TEXT NOT NULL,
            edit_kind TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            requires_confirmation BOOLEAN NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """,
    )
```

- [ ] **Step 7: Run database tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py::test_profile_document_models_are_registered_with_metadata tests\test_sqlite_migrations.py tests\test_db_session.py -q
```

Expected: tests pass.

- [ ] **Step 8: Commit Task 1**

```powershell
git add backend/app/db/models.py backend/app/db/session.py backend/app/db/sqlite_migrations.py backend/tests/test_profile_document_service.py backend/tests/test_sqlite_migrations.py
git commit -m "feat: add profile cv draft tables"
```

---

### Task 2: Add Deterministic CV Structure Extraction

**Files:**
- Create: `backend/app/services/cv_structure_extraction_service.py`
- Modify: `backend/app/services/profile_document_service.py`
- Test: `backend/tests/test_cv_structure_extraction_service.py`
- Test: `backend/tests/test_profile_document_service.py`

- [ ] **Step 1: Write failing structure extraction tests**

Create `backend/tests/test_cv_structure_extraction_service.py`:

```python
from app.services.cv_structure_extraction_service import (
    POOR_STRUCTURE_RECOMMENDATION,
    CvStructureExtractionService,
)


def test_structure_extraction_marks_ordered_cv_reliable():
    text = """
    Summary
    AI engineer intern focused on Python and RAG.

    Experience
    - Built FastAPI services
    - Integrated vector search

    Projects
    - Job Agent: LangGraph workflow

    Education
    University of Engineering, 2024

    Skills
    Python, FastAPI, SQL
    """

    result = CvStructureExtractionService().analyze(text)

    assert result.status == "reliable"
    assert result.confidence >= 0.75
    assert [section.heading for section in result.sections][:3] == [
        "Summary",
        "Experience",
        "Projects",
    ]
    assert result.recommendation is None


def test_structure_extraction_marks_sparse_text_partial():
    text = "AI engineer intern. Python FastAPI RAG. Hanoi. Open to internships."

    result = CvStructureExtractionService().analyze(text)

    assert result.status == "partial"
    assert 0.25 <= result.confidence < 0.75
    assert result.recommendation is None


def test_structure_extraction_marks_broken_text_unreliable_with_template_message():
    text = "Python\n|\n|\n2024\nName\nEmail\nTable cell cell cell\n" * 2

    result = CvStructureExtractionService().analyze(text)

    assert result.status == "unreliable"
    assert result.confidence < 0.25
    assert result.recommendation == POOR_STRUCTURE_RECOMMENDATION
```

- [ ] **Step 2: Run structure tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_cv_structure_extraction_service.py -q
```

Expected: fail because the service module does not exist.

- [ ] **Step 3: Implement structure extraction service**

Create `backend/app/services/cv_structure_extraction_service.py`:

```python
"""Deterministic CV structure extraction from text-based PDFs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re


POOR_STRUCTURE_RECOMMENDATION = (
    "The current PDF structure is not reliable enough for structure-preserving edits. "
    "I recommend converting it into a cleaner CV template before editing."
)

KNOWN_HEADINGS = {
    "summary",
    "profile",
    "experience",
    "work experience",
    "projects",
    "education",
    "skills",
    "certifications",
    "certificates",
    "awards",
}


@dataclass(frozen=True)
class CvSection:
    heading: str
    content: str
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CvStructureResult:
    status: str
    confidence: float
    sections: list[CvSection]
    warnings: list[str]
    recommendation: str | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "status": self.status,
                "confidence": self.confidence,
                "sections": [
                    {
                        "heading": section.heading,
                        "content": section.content,
                        "bullets": section.bullets,
                    }
                    for section in self.sections
                ],
                "warnings": self.warnings,
                "recommendation": self.recommendation,
            },
            separators=(",", ":"),
        )


class CvStructureExtractionService:
    def analyze(self, text: str) -> CvStructureResult:
        normalized = (text or "").replace("\r\n", "\n").strip()
        if not normalized:
            return CvStructureResult(
                status="unreliable",
                confidence=0.0,
                sections=[],
                warnings=["No extracted text available."],
                recommendation=POOR_STRUCTURE_RECOMMENDATION,
            )

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        sections = self._split_sections(lines)
        bullet_count = sum(len(section.bullets) for section in sections)
        heading_count = len(sections)
        table_noise = sum(1 for line in lines if "|" in line or "\t" in line)

        score = 0.0
        warnings: list[str] = []
        if heading_count >= 4:
            score += 0.45
        elif heading_count >= 2:
            score += 0.25
        else:
            warnings.append("Few recognizable CV headings were detected.")

        if bullet_count >= 3:
            score += 0.25
        elif bullet_count >= 1:
            score += 0.1
        else:
            warnings.append("Few bullet groups were detected.")

        if len(lines) >= 8:
            score += 0.2
        elif len(lines) >= 3:
            score += 0.1

        if table_noise >= max(2, len(lines) // 4):
            score -= 0.35
            warnings.append("Table-like text extraction noise was detected.")

        confidence = max(0.0, min(1.0, round(score, 2)))
        if confidence >= 0.75:
            status = "reliable"
            recommendation = None
        elif confidence >= 0.25:
            status = "partial"
            recommendation = None
        else:
            status = "unreliable"
            recommendation = POOR_STRUCTURE_RECOMMENDATION

        return CvStructureResult(
            status=status,
            confidence=confidence,
            sections=sections,
            warnings=warnings,
            recommendation=recommendation,
        )

    def _split_sections(self, lines: list[str]) -> list[CvSection]:
        sections: list[CvSection] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        for line in lines:
            if self._is_heading(line):
                if current_heading is not None:
                    sections.append(self._section(current_heading, current_lines))
                current_heading = self._clean_heading(line)
                current_lines = []
                continue
            if current_heading is not None:
                current_lines.append(line)

        if current_heading is not None:
            sections.append(self._section(current_heading, current_lines))
        return sections

    def _is_heading(self, line: str) -> bool:
        cleaned = self._clean_heading(line).casefold()
        if cleaned in KNOWN_HEADINGS:
            return True
        return bool(re.fullmatch(r"[A-Z][A-Za-z ]{2,32}", line)) and len(line.split()) <= 4

    def _clean_heading(self, line: str) -> str:
        return re.sub(r"[:\-]+$", "", line.strip())

    def _section(self, heading: str, lines: list[str]) -> CvSection:
        bullets = [
            line.lstrip("-*• ").strip()
            for line in lines
            if line.startswith(("-", "*", "•"))
        ]
        return CvSection(
            heading=heading,
            content="\n".join(lines).strip(),
            bullets=[bullet for bullet in bullets if bullet],
        )
```

- [ ] **Step 4: Write failing profile document service structure test**

In `backend/tests/test_profile_document_service.py`, add:

```python
@pytest.mark.asyncio
async def test_create_document_extracts_cv_structure_status(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "cv.pdf"
    source_path.write_bytes(b"%PDF-test")
    service = ProfileDocumentService(
        extractor=FakeExtractor(
            "Summary\nAI engineer intern\n\n"
            "Experience\n- Built FastAPI services\n\n"
            "Projects\n- RAG app\n\n"
            "Education\nUniversity\n\n"
            "Skills\nPython"
        ),
        embedder=FakeEmbedder(),
        vector_store=FakeVectorStore(),
    )
    document = await service.create_document_from_pdf(
        db_session,
        role_profile_id=test_role_profile.id,
        source_path=source_path,
        original_filename="cv.pdf",
        mime_type="application/pdf",
    )

    version = await db_session.get(ProfileDocumentVersion, document.active_version_id)
    assert version.structure_status == "reliable"
    assert version.structure_confidence is not None
    assert version.structure_confidence >= 0.75
```

- [ ] **Step 5: Run profile document structure test and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py::test_create_document_extracts_cv_structure_status -q
```

Expected: fail because upload still leaves `structure_status` as `not_extracted`.

- [ ] **Step 6: Wire structure extraction into upload processing**

In `backend/app/services/profile_document_service.py`, add import:

```python
from app.services.cv_structure_extraction_service import CvStructureExtractionService
```

Add constructor parameter:

```python
structure_extractor: CvStructureExtractionService | None = None,
```

Set:

```python
self.structure_extractor = structure_extractor or CvStructureExtractionService()
```

After extracted text is available and before commit, add:

```python
            structure = self.structure_extractor.analyze(text)
            version.structure_status = structure.status
            version.structure_confidence = structure.confidence
```

When text extraction fails, keep the existing `extraction_status="failed"` path and set:

```python
            version.structure_status = "unreliable"
            version.structure_confidence = 0.0
```

- [ ] **Step 7: Run structure tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_cv_structure_extraction_service.py tests\test_profile_document_service.py -q
```

Expected: tests pass.

- [ ] **Step 8: Commit Task 2**

```powershell
git add backend/app/services/cv_structure_extraction_service.py backend/app/services/profile_document_service.py backend/tests/test_cv_structure_extraction_service.py backend/tests/test_profile_document_service.py
git commit -m "feat: analyze profile cv structure"
```

---

### Task 3: Add Draft And Suggestion Services

**Files:**
- Create: `backend/app/services/profile_cv_draft_service.py`
- Test: `backend/tests/test_profile_cv_draft_service.py`

- [ ] **Step 1: Write failing draft service tests**

Create `backend/tests/test_profile_cv_draft_service.py`:

```python
import json

import pytest

from app.db.models import (
    ProfileCvDraft,
    ProfileCvImprovementSuggestion,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
    RoleProfile,
)
from app.services.cv_structure_extraction_service import POOR_STRUCTURE_RECOMMENDATION
from app.services.profile_cv_draft_service import (
    CreateCvDraftRequest,
    CreateCvSuggestionRequest,
    ProfileCvDraftService,
)


async def create_cv(db_session, *, structure_status: str = "reliable"):
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
        structure_status=structure_status,
        structure_confidence=0.8 if structure_status == "reliable" else 0.1,
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
            text="Active CV evidence: Python FastAPI project",
            token_count=8,
            qdrant_point_id="99999999-9999-9999-9999-999999999999",
        )
    )
    await db_session.commit()
    return profile, document, version


@pytest.mark.asyncio
async def test_create_suggestion_rejects_fabricated_fact_edit(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()

    with pytest.raises(ValueError, match="requires user-provided facts"):
        await service.create_suggestion(
            db_session,
            CreateCvSuggestionRequest(
                role_profile_id=profile.id,
                document_id=document.id,
                version_id=version.id,
                requirement="AWS production experience",
                current_cv_evidence="No AWS evidence in active CV.",
                missing_or_weak_evidence="AWS is missing.",
                proposed_edit="Add AWS production deployment experience.",
                edit_kind="requires_user_fact",
                risk_level="high",
                requires_confirmation=True,
            ),
        )


@pytest.mark.asyncio
async def test_create_wording_suggestion_persists_grounded_item(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()

    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            requirement="FastAPI",
            current_cv_evidence="Active CV evidence: Python FastAPI project",
            missing_or_weak_evidence="FastAPI evidence is present but not emphasized.",
            proposed_edit="Emphasize FastAPI API ownership in the project bullet.",
            edit_kind="wording_only",
            risk_level="low",
            requires_confirmation=True,
        ),
    )

    assert suggestion.status == "suggested"
    assert suggestion.edit_kind == "wording_only"


@pytest.mark.asyncio
async def test_create_draft_preserves_original_and_marks_suggestions_drafted(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()
    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            requirement="FastAPI",
            current_cv_evidence="Active CV evidence: Python FastAPI project",
            missing_or_weak_evidence="FastAPI evidence is weakly worded.",
            proposed_edit="Rewrite bullet to lead with FastAPI service delivery.",
            edit_kind="wording_only",
            risk_level="low",
            requires_confirmation=True,
        ),
    )

    draft = await service.create_draft(
        db_session,
        CreateCvDraftRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            base_version_id=version.id,
            title="FastAPI emphasis draft",
            suggestion_ids=[suggestion.id],
            confirmed=True,
            created_by="ai",
        ),
    )

    stored = await db_session.get(ProfileCvDraft, draft.id)
    updated_suggestion = await db_session.get(ProfileCvImprovementSuggestion, suggestion.id)
    document_after = await db_session.get(ProfileDocument, document.id)
    assert stored.status == "draft"
    assert json.loads(stored.edit_plan_json)["suggestion_ids"] == [suggestion.id]
    assert updated_suggestion.status == "drafted"
    assert document_after.active_version_id == version.id


@pytest.mark.asyncio
async def test_create_draft_for_unreliable_structure_returns_template_recommendation(db_session):
    profile, document, version = await create_cv(db_session, structure_status="unreliable")
    service = ProfileCvDraftService()

    draft = await service.create_draft(
        db_session,
        CreateCvDraftRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            base_version_id=version.id,
            title="Template draft",
            suggestion_ids=[],
            confirmed=True,
            created_by="ai",
        ),
    )

    preview = await service.preview_draft(db_session, role_profile_id=profile.id, draft_id=draft.id)
    assert preview["recommendation"] == POOR_STRUCTURE_RECOMMENDATION
    assert preview["structure_status"] == "unreliable"
```

- [ ] **Step 2: Run draft service tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_cv_draft_service.py -q
```

Expected: fail because `profile_cv_draft_service.py` does not exist.

- [ ] **Step 3: Implement draft service**

Create `backend/app/services/profile_cv_draft_service.py`:

```python
"""Profile CV suggestion and draft services."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ProfileCvDraft,
    ProfileCvImprovementSuggestion,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
)
from app.services.cv_structure_extraction_service import POOR_STRUCTURE_RECOMMENDATION


EditKind = Literal["wording_only", "requires_user_fact"]
RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CreateCvSuggestionRequest:
    role_profile_id: str
    document_id: str
    version_id: str
    requirement: str
    current_cv_evidence: str
    missing_or_weak_evidence: str
    proposed_edit: str
    edit_kind: EditKind
    risk_level: RiskLevel
    requires_confirmation: bool = True
    job_id: str | None = None


@dataclass(frozen=True)
class CreateCvDraftRequest:
    role_profile_id: str
    document_id: str
    base_version_id: str
    title: str
    suggestion_ids: list[str]
    confirmed: bool
    created_by: str = "ai"


class ProfileCvDraftService:
    async def create_suggestion(
        self,
        session: AsyncSession,
        request: CreateCvSuggestionRequest,
    ) -> ProfileCvImprovementSuggestion:
        await self._require_version(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.version_id,
        )
        if request.edit_kind == "requires_user_fact":
            raise ValueError("Suggestion requires user-provided facts before drafting.")
        if request.risk_level not in {"low", "medium", "high"}:
            raise ValueError("risk_level must be low, medium, or high")
        if request.edit_kind != "wording_only":
            raise ValueError("edit_kind must be wording_only or requires_user_fact")

        suggestion = ProfileCvImprovementSuggestion(
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.version_id,
            job_id=request.job_id,
            requirement=request.requirement.strip(),
            current_cv_evidence=request.current_cv_evidence.strip(),
            missing_or_weak_evidence=request.missing_or_weak_evidence.strip(),
            proposed_edit=request.proposed_edit.strip(),
            edit_kind=request.edit_kind,
            risk_level=request.risk_level,
            requires_confirmation=request.requires_confirmation,
            status="suggested",
        )
        session.add(suggestion)
        await session.commit()
        await session.refresh(suggestion)
        return suggestion

    async def list_suggestions(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str | None = None,
    ) -> list[ProfileCvImprovementSuggestion]:
        statement = select(ProfileCvImprovementSuggestion).where(
            ProfileCvImprovementSuggestion.role_profile_id == role_profile_id
        )
        if document_id:
            statement = statement.where(ProfileCvImprovementSuggestion.document_id == document_id)
        result = await session.execute(statement.order_by(ProfileCvImprovementSuggestion.created_at.desc()))
        return list(result.scalars())

    async def create_draft(
        self,
        session: AsyncSession,
        request: CreateCvDraftRequest,
    ) -> ProfileCvDraft:
        if not request.confirmed:
            raise ValueError("Creating a CV draft requires confirmation.")
        document, version = await self._require_version(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.base_version_id,
        )
        suggestions = await self._load_suggestions(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.base_version_id,
            suggestion_ids=request.suggestion_ids,
        )
        chunks = await self._load_chunks(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.base_version_id,
        )
        structure = {
            "source": "extracted_text",
            "document_id": document.id,
            "version_id": version.id,
            "structure_status": version.structure_status,
            "sections": [{"heading": "Extracted CV", "content": "\n\n".join(chunk.text for chunk in chunks)}],
            "recommendation": (
                POOR_STRUCTURE_RECOMMENDATION
                if version.structure_status == "unreliable"
                else None
            ),
        }
        edit_plan = {
            "suggestion_ids": [suggestion.id for suggestion in suggestions],
            "edits": [
                {
                    "requirement": suggestion.requirement,
                    "current_cv_evidence": suggestion.current_cv_evidence,
                    "proposed_edit": suggestion.proposed_edit,
                    "edit_kind": suggestion.edit_kind,
                    "risk_level": suggestion.risk_level,
                }
                for suggestion in suggestions
            ],
        }
        draft = ProfileCvDraft(
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            base_version_id=request.base_version_id,
            status="draft",
            title=request.title.strip() or "CV edit draft",
            structure_json=json.dumps(structure, separators=(",", ":")),
            edit_plan_json=json.dumps(edit_plan, separators=(",", ":")),
            structure_status_at_creation=version.structure_status,
            created_by=request.created_by,
        )
        session.add(draft)
        for suggestion in suggestions:
            suggestion.status = "drafted"
        await session.commit()
        await session.refresh(draft)
        return draft

    async def list_drafts(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str | None = None,
    ) -> list[ProfileCvDraft]:
        statement = select(ProfileCvDraft).where(ProfileCvDraft.role_profile_id == role_profile_id)
        if document_id:
            statement = statement.where(ProfileCvDraft.document_id == document_id)
        result = await session.execute(statement.order_by(ProfileCvDraft.updated_at.desc()))
        return list(result.scalars())

    async def preview_draft(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        draft_id: str,
    ) -> dict[str, object]:
        draft = await session.get(ProfileCvDraft, draft_id)
        if draft is None or draft.role_profile_id != role_profile_id:
            raise LookupError("CV draft not found")
        structure = json.loads(draft.structure_json)
        edit_plan = json.loads(draft.edit_plan_json)
        return {
            "draft_id": draft.id,
            "title": draft.title,
            "status": draft.status,
            "structure_status": draft.structure_status_at_creation,
            "recommendation": structure.get("recommendation"),
            "sections": structure.get("sections", []),
            "edits": edit_plan.get("edits", []),
        }

    async def _require_version(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
    ) -> tuple[ProfileDocument, ProfileDocumentVersion]:
        document = await session.get(ProfileDocument, document_id)
        version = await session.get(ProfileDocumentVersion, version_id)
        if document is None or version is None:
            raise LookupError("Profile CV version not found")
        if document.role_profile_id != role_profile_id or version.role_profile_id != role_profile_id:
            raise LookupError("Profile CV version not found")
        if version.document_id != document_id:
            raise LookupError("Profile CV version not found")
        return document, version

    async def _load_suggestions(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        suggestion_ids: list[str],
    ) -> list[ProfileCvImprovementSuggestion]:
        if not suggestion_ids:
            return []
        result = await session.execute(
            select(ProfileCvImprovementSuggestion)
            .where(ProfileCvImprovementSuggestion.id.in_(suggestion_ids))
            .where(ProfileCvImprovementSuggestion.role_profile_id == role_profile_id)
            .where(ProfileCvImprovementSuggestion.document_id == document_id)
            .where(ProfileCvImprovementSuggestion.version_id == version_id)
        )
        by_id = {suggestion.id: suggestion for suggestion in result.scalars()}
        missing = [suggestion_id for suggestion_id in suggestion_ids if suggestion_id not in by_id]
        if missing:
            raise LookupError("CV suggestion not found")
        return [by_id[suggestion_id] for suggestion_id in suggestion_ids]

    async def _load_chunks(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
    ) -> list[ProfileDocumentChunk]:
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.role_profile_id == role_profile_id)
            .where(ProfileDocumentChunk.document_id == document_id)
            .where(ProfileDocumentChunk.version_id == version_id)
            .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
        )
        return list(result.scalars())
```

- [ ] **Step 4: Run draft service tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_cv_draft_service.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit Task 3**

```powershell
git add backend/app/services/profile_cv_draft_service.py backend/tests/test_profile_cv_draft_service.py
git commit -m "feat: add profile cv draft service"
```

---

### Task 4: Add Draft And Suggestion API Routes

**Files:**
- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/api/routes_profile_documents.py`
- Test: `backend/tests/test_routes_profile_documents.py`

- [ ] **Step 1: Write failing route tests**

Append to `backend/tests/test_routes_profile_documents.py`:

```python
async def upload_ready_profile_document(client, role_profile):
    upload = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()
    version_response = await client.get(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions"
    )
    assert version_response.status_code == 200
    version = version_response.json()["versions"][0]
    return document, version


@pytest.mark.asyncio
async def test_cv_suggestion_and_draft_routes(client, role_profile, db_session):
    document, version = await upload_ready_profile_document(client, role_profile)

    suggestion_response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions/{version['id']}/suggestions",
        json={
            "requirement": "FastAPI",
            "current_cv_evidence": "Active CV evidence: FastAPI project",
            "missing_or_weak_evidence": "FastAPI impact is weakly worded.",
            "proposed_edit": "Lead the project bullet with FastAPI service delivery.",
            "edit_kind": "wording_only",
            "risk_level": "low",
            "requires_confirmation": True,
        },
    )
    assert suggestion_response.status_code == 201
    suggestion = suggestion_response.json()
    assert suggestion["status"] == "suggested"

    draft_response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions/{version['id']}/drafts",
        json={
            "title": "FastAPI emphasis draft",
            "suggestion_ids": [suggestion["id"]],
            "confirmed": True,
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["status"] == "draft"

    preview_response = await client.get(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/drafts/{draft['id']}/preview"
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["draft_id"] == draft["id"]
    assert preview_response.json()["edits"][0]["requirement"] == "FastAPI"
```

Also add:

```python
@pytest.mark.asyncio
async def test_cv_draft_creation_requires_confirmation(client, role_profile, db_session):
    document, version = await upload_ready_profile_document(client, role_profile)

    response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions/{version['id']}/drafts",
        json={"title": "Draft", "suggestion_ids": [], "confirmed": False},
    )

    assert response.status_code == 409
    assert "confirmation" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run route tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_profile_documents.py::test_cv_suggestion_and_draft_routes tests\test_routes_profile_documents.py::test_cv_draft_creation_requires_confirmation -q
```

Expected: fail because routes and schemas do not exist.

- [ ] **Step 3: Add API schemas**

In `backend/app/api/schemas.py`, add:

```python
class CvImprovementSuggestionCreateRequest(ApiSchema):
    requirement: str = Field(min_length=1)
    current_cv_evidence: str = Field(min_length=1)
    missing_or_weak_evidence: str = Field(min_length=1)
    proposed_edit: str = Field(min_length=1)
    edit_kind: str = Field(pattern="^(wording_only|requires_user_fact)$")
    risk_level: str = Field(pattern="^(low|medium|high)$")
    requires_confirmation: bool = True
    job_id: UUID | None = None


class CvImprovementSuggestionResponse(ApiSchema):
    id: UUID
    role_profile_id: UUID
    document_id: UUID
    version_id: UUID
    job_id: UUID | None
    requirement: str
    current_cv_evidence: str
    missing_or_weak_evidence: str
    proposed_edit: str
    edit_kind: str
    risk_level: str
    requires_confirmation: bool
    status: str
    created_at: datetime
    updated_at: datetime


class CvImprovementSuggestionListResponse(ApiSchema):
    suggestions: list[CvImprovementSuggestionResponse] = Field(default_factory=list)


class CvDraftCreateRequest(ApiSchema):
    title: str = Field(min_length=1, max_length=200)
    suggestion_ids: list[UUID] = Field(default_factory=list)
    confirmed: bool = False


class CvDraftResponse(ApiSchema):
    id: UUID
    role_profile_id: UUID
    document_id: UUID
    base_version_id: UUID
    status: str
    title: str
    structure_status_at_creation: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class CvDraftListResponse(ApiSchema):
    drafts: list[CvDraftResponse] = Field(default_factory=list)


class CvDraftPreviewResponse(ApiSchema):
    draft_id: UUID
    title: str
    status: str
    structure_status: str
    recommendation: str | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    edits: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Add routes**

In `backend/app/api/routes_profile_documents.py`, extend schema imports:

```python
    CvDraftCreateRequest,
    CvDraftListResponse,
    CvDraftPreviewResponse,
    CvDraftResponse,
    CvImprovementSuggestionCreateRequest,
    CvImprovementSuggestionListResponse,
    CvImprovementSuggestionResponse,
```

Add service imports:

```python
from app.services.profile_cv_draft_service import (
    CreateCvDraftRequest,
    CreateCvSuggestionRequest,
    ProfileCvDraftService,
)
```

Add singleton:

```python
profile_cv_draft_service = ProfileCvDraftService()
```

Add routes before `delete_profile_document`:

```python
@router.post(
    "/{document_id}/versions/{version_id}/suggestions",
    response_model=CvImprovementSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cv_suggestion(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    request: CvImprovementSuggestionCreateRequest,
    session: SessionDep,
):
    await _require_profile(session, str(role_profile_id))
    try:
        return await profile_cv_draft_service.create_suggestion(
            session,
            CreateCvSuggestionRequest(
                role_profile_id=str(role_profile_id),
                document_id=str(document_id),
                version_id=str(version_id),
                job_id=str(request.job_id) if request.job_id else None,
                requirement=request.requirement,
                current_cv_evidence=request.current_cv_evidence,
                missing_or_weak_evidence=request.missing_or_weak_evidence,
                proposed_edit=request.proposed_edit,
                edit_kind=request.edit_kind,  # type: ignore[arg-type]
                risk_level=request.risk_level,  # type: ignore[arg-type]
                requires_confirmation=request.requires_confirmation,
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{document_id}/suggestions", response_model=CvImprovementSuggestionListResponse)
async def list_cv_suggestions(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> CvImprovementSuggestionListResponse:
    await _require_profile(session, str(role_profile_id))
    suggestions = await profile_cv_draft_service.list_suggestions(
        session,
        role_profile_id=str(role_profile_id),
        document_id=str(document_id),
    )
    return CvImprovementSuggestionListResponse(suggestions=suggestions)


@router.post(
    "/{document_id}/versions/{version_id}/drafts",
    response_model=CvDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cv_draft(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    request: CvDraftCreateRequest,
    session: SessionDep,
):
    await _require_profile(session, str(role_profile_id))
    try:
        return await profile_cv_draft_service.create_draft(
            session,
            CreateCvDraftRequest(
                role_profile_id=str(role_profile_id),
                document_id=str(document_id),
                base_version_id=str(version_id),
                title=request.title,
                suggestion_ids=[str(suggestion_id) for suggestion_id in request.suggestion_ids],
                confirmed=request.confirmed,
                created_by="ai",
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{document_id}/drafts", response_model=CvDraftListResponse)
async def list_cv_drafts(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> CvDraftListResponse:
    await _require_profile(session, str(role_profile_id))
    drafts = await profile_cv_draft_service.list_drafts(
        session,
        role_profile_id=str(role_profile_id),
        document_id=str(document_id),
    )
    return CvDraftListResponse(drafts=drafts)


@router.get("/{document_id}/drafts/{draft_id}/preview", response_model=CvDraftPreviewResponse)
async def preview_cv_draft(
    role_profile_id: UUID,
    document_id: UUID,
    draft_id: UUID,
    session: SessionDep,
) -> CvDraftPreviewResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        preview = await profile_cv_draft_service.preview_draft(
            session,
            role_profile_id=str(role_profile_id),
            draft_id=str(draft_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CvDraftPreviewResponse(**preview)
```

- [ ] **Step 5: Run route tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_profile_documents.py -q
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add backend/app/api/schemas.py backend/app/api/routes_profile_documents.py backend/tests/test_routes_profile_documents.py
git commit -m "feat: expose profile cv draft api"
```

---

### Task 5: Add Phase 3 Agent Tools

**Files:**
- Modify: `backend/app/services/tool_registry.py`
- Modify: `backend/app/api/routes_chat.py`
- Test: `backend/tests/test_tool_registry.py`
- Test: `backend/tests/test_routes_chat.py`

- [ ] **Step 1: Write failing tool registry tests**

In `backend/tests/test_tool_registry.py`, extend `test_registry_exposes_safe_tool_metadata`:

```python
for tool_name in [
    "suggest_cv_improvements",
    "create_cv_edit_draft",
    "preview_cv_edit_draft",
]:
    assert tool_name in tools
    assert "api_key" not in tools[tool_name].description.lower()

assert tools["suggest_cv_improvements"].requires_confirmation is False
assert tools["create_cv_edit_draft"].requires_confirmation is True
assert tools["preview_cv_edit_draft"].requires_confirmation is False
```

Add:

```python
@pytest.mark.asyncio
async def test_cv_draft_tool_handlers_return_sanitized_payloads():
    from app.services.tool_registry import (
        build_create_cv_edit_draft_handler,
        build_preview_cv_edit_draft_handler,
        build_suggest_cv_improvements_handler,
    )

    class Suggestion:
        id = "suggestion-1"
        status = "suggested"
        edit_kind = "wording_only"
        risk_level = "low"

    class Draft:
        id = "draft-1"
        status = "draft"
        title = "Draft"
        structure_status_at_creation = "reliable"

    class DraftService:
        async def create_suggestion(self, session, request):
            return Suggestion()

        async def create_draft(self, session, request):
            return Draft()

        async def preview_draft(self, session, *, role_profile_id, draft_id):
            return {
                "draft_id": draft_id,
                "title": "Draft",
                "status": "draft",
                "structure_status": "reliable",
                "recommendation": None,
                "sections": [{"heading": "Extracted CV", "content": "Private CV text"}],
                "edits": [{"requirement": "FastAPI", "proposed_edit": "Improve wording"}],
            }

    service = DraftService()
    session = object()
    context = {"role_profile_id": "profile-1", "document_id": "doc-1", "version_id": "version-1"}

    suggestion_result = await build_suggest_cv_improvements_handler(service, session)(
        ToolRequest(
            name="suggest_cv_improvements",
            arguments={
                "requirement": "FastAPI",
                "current_cv_evidence": "Evidence exists",
                "missing_or_weak_evidence": "Weak wording",
                "proposed_edit": "Improve wording",
                "edit_kind": "wording_only",
                "risk_level": "low",
            },
            context=context,
        )
    )
    assert suggestion_result.safe_payload == {
        "suggestion_id": "suggestion-1",
        "status": "suggested",
        "edit_kind": "wording_only",
        "risk_level": "low",
    }

    draft_result = await build_create_cv_edit_draft_handler(service, session)(
        ToolRequest(
            name="create_cv_edit_draft",
            arguments={"title": "Draft", "suggestion_ids": ["suggestion-1"], "confirmed": True},
            context=context,
        )
    )
    assert draft_result.safe_payload["draft_id"] == "draft-1"

    preview_result = await build_preview_cv_edit_draft_handler(service, session)(
        ToolRequest(
            name="preview_cv_edit_draft",
            arguments={"draft_id": "draft-1"},
            context={"role_profile_id": "profile-1"},
        )
    )
    assert "Private CV text" in preview_result.content
    assert "Private CV text" not in str(preview_result.safe_payload)
```

- [ ] **Step 2: Run tool tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_tool_registry.py -q
```

Expected: fail because new tools and handlers do not exist.

- [ ] **Step 3: Register Phase 3 tools and handlers**

In `backend/app/services/tool_registry.py`, import service request dataclasses:

```python
from app.services.profile_cv_draft_service import CreateCvDraftRequest, CreateCvSuggestionRequest
```

Add `ToolDefinition` entries before `retrieve_profile_documents`:

```python
"suggest_cv_improvements": ToolDefinition(
    name="suggest_cv_improvements",
    description="Store a grounded CV improvement suggestion without editing the PDF.",
    requires_confirmation=False,
    handler=_not_wired,
),
"create_cv_edit_draft": ToolDefinition(
    name="create_cv_edit_draft",
    description="Create an editable CV draft from approved wording-only suggestions.",
    requires_confirmation=True,
    handler=_not_wired,
),
"preview_cv_edit_draft": ToolDefinition(
    name="preview_cv_edit_draft",
    description="Preview an editable CV draft without exporting or activating it.",
    requires_confirmation=False,
    handler=_not_wired,
),
```

Append handlers:

```python
def build_suggest_cv_improvements_handler(
    draft_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        suggestion = await draft_service.create_suggestion(
            session,
            CreateCvSuggestionRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                document_id=str(request.context["document_id"]),
                version_id=str(request.context["version_id"]),
                job_id=request.arguments.get("job_id"),
                requirement=str(request.arguments["requirement"]),
                current_cv_evidence=str(request.arguments["current_cv_evidence"]),
                missing_or_weak_evidence=str(request.arguments["missing_or_weak_evidence"]),
                proposed_edit=str(request.arguments["proposed_edit"]),
                edit_kind=str(request.arguments["edit_kind"]),  # type: ignore[arg-type]
                risk_level=str(request.arguments["risk_level"]),  # type: ignore[arg-type]
                requires_confirmation=True,
            ),
        )
        return ToolResult(
            content="Stored 1 grounded CV improvement suggestion.",
            result_summary="Stored 1 CV suggestion",
            safe_payload={
                "suggestion_id": suggestion.id,
                "status": suggestion.status,
                "edit_kind": suggestion.edit_kind,
                "risk_level": suggestion.risk_level,
            },
        )

    return handler


def build_create_cv_edit_draft_handler(
    draft_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        draft = await draft_service.create_draft(
            session,
            CreateCvDraftRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                document_id=str(request.context["document_id"]),
                base_version_id=str(request.context["version_id"]),
                title=str(request.arguments.get("title", "CV edit draft")),
                suggestion_ids=[str(value) for value in request.arguments.get("suggestion_ids", [])],
                confirmed=bool(request.arguments.get("confirmed", False)),
                created_by="ai",
            ),
        )
        return ToolResult(
            content="Created a CV edit draft. Original PDF was not modified.",
            result_summary=f"Created CV draft: {draft.title}",
            safe_payload={
                "draft_id": draft.id,
                "status": draft.status,
                "title": draft.title,
                "structure_status": draft.structure_status_at_creation,
            },
        )

    return handler


def build_preview_cv_edit_draft_handler(
    draft_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        preview = await draft_service.preview_draft(
            session,
            role_profile_id=str(request.context["role_profile_id"]),
            draft_id=str(request.arguments["draft_id"]),
        )
        return ToolResult(
            content=json.dumps(preview, separators=(",", ":")),
            result_summary=f"Previewed CV draft: {preview['title']}",
            safe_payload={
                "draft_id": preview["draft_id"],
                "status": preview["status"],
                "structure_status": preview["structure_status"],
                "edit_count": len(preview.get("edits", [])),
                "has_template_recommendation": bool(preview.get("recommendation")),
            },
        )

    return handler
```

Ensure `json` is imported at the top of `tool_registry.py`.

- [ ] **Step 4: Wire new tools into chat registry**

In `backend/app/api/routes_chat.py`, import:

```python
from app.services.profile_cv_draft_service import ProfileCvDraftService
```

Extend tool registry imports:

```python
    build_create_cv_edit_draft_handler,
    build_preview_cv_edit_draft_handler,
    build_suggest_cv_improvements_handler,
```

Add singleton:

```python
profile_cv_draft_service = ProfileCvDraftService()
```

Add overrides:

```python
"suggest_cv_improvements": build_suggest_cv_improvements_handler(profile_cv_draft_service, session),
"create_cv_edit_draft": build_create_cv_edit_draft_handler(profile_cv_draft_service, session),
"preview_cv_edit_draft": build_preview_cv_edit_draft_handler(profile_cv_draft_service, session),
```

- [ ] **Step 5: Run tool and chat route tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_tool_registry.py tests\test_routes_chat.py -q
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 5**

```powershell
git add backend/app/services/tool_registry.py backend/app/api/routes_chat.py backend/tests/test_tool_registry.py backend/tests/test_routes_chat.py
git commit -m "feat: add profile cv draft tools"
```

---

### Task 6: Add Frontend Suggestion And Draft Preview Panels

**Files:**
- Modify: `frontend/job-agent-ui/src/types/profileDocuments.ts`
- Modify: `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`
- Modify: `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
- Test: `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`
- Test: `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`

- [ ] **Step 1: Write failing frontend client tests**

In `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`, add:

```typescript
import {
  createCvDraft,
  createCvSuggestion,
  listCvDrafts,
  listCvSuggestions,
  previewCvDraft,
} from "../api/profileDocumentsClient";
```

Add tests:

```typescript
it("creates CV suggestions and drafts through profile document routes", async () => {
  mock.onPost("/api/role-profiles/profile-1/documents/doc-1/versions/version-1/suggestions").reply(201, {
    id: "suggestion-1",
    role_profile_id: "profile-1",
    document_id: "doc-1",
    version_id: "version-1",
    job_id: null,
    requirement: "FastAPI",
    current_cv_evidence: "Evidence",
    missing_or_weak_evidence: "Weak wording",
    proposed_edit: "Improve wording",
    edit_kind: "wording_only",
    risk_level: "low",
    requires_confirmation: true,
    status: "suggested",
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
  });
  mock.onPost("/api/role-profiles/profile-1/documents/doc-1/versions/version-1/drafts").reply(201, {
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
  });

  const suggestion = await createCvSuggestion("profile-1", "doc-1", "version-1", {
    requirement: "FastAPI",
    current_cv_evidence: "Evidence",
    missing_or_weak_evidence: "Weak wording",
    proposed_edit: "Improve wording",
    edit_kind: "wording_only",
    risk_level: "low",
    requires_confirmation: true,
  });
  const draft = await createCvDraft("profile-1", "doc-1", "version-1", {
    title: "Draft",
    suggestion_ids: [suggestion.id],
    confirmed: true,
  });

  expect(suggestion.id).toBe("suggestion-1");
  expect(draft.id).toBe("draft-1");
});
```

Add:

```typescript
it("lists suggestions, drafts, and draft previews", async () => {
  mock.onGet("/api/role-profiles/profile-1/documents/doc-1/suggestions").reply(200, { suggestions: [] });
  mock.onGet("/api/role-profiles/profile-1/documents/doc-1/drafts").reply(200, { drafts: [] });
  mock.onGet("/api/role-profiles/profile-1/documents/doc-1/drafts/draft-1/preview").reply(200, {
    draft_id: "draft-1",
    title: "Draft",
    status: "draft",
    structure_status: "reliable",
    recommendation: null,
    sections: [],
    edits: [],
  });

  await expect(listCvSuggestions("profile-1", "doc-1")).resolves.toEqual([]);
  await expect(listCvDrafts("profile-1", "doc-1")).resolves.toEqual([]);
  await expect(previewCvDraft("profile-1", "doc-1", "draft-1")).resolves.toMatchObject({
    draft_id: "draft-1",
  });
});
```

- [ ] **Step 2: Run frontend client tests and verify failure**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/profileDocumentsClient.test.ts
```

Expected: fail because client functions and types do not exist.

- [ ] **Step 3: Add frontend types**

In `frontend/job-agent-ui/src/types/profileDocuments.ts`, add:

```typescript
export interface CvImprovementSuggestion {
  id: string;
  role_profile_id: string;
  document_id: string;
  version_id: string;
  job_id: string | null;
  requirement: string;
  current_cv_evidence: string;
  missing_or_weak_evidence: string;
  proposed_edit: string;
  edit_kind: "wording_only" | "requires_user_fact";
  risk_level: "low" | "medium" | "high";
  requires_confirmation: boolean;
  status: "suggested" | "accepted" | "rejected" | "drafted";
  created_at: string;
  updated_at: string;
}

export interface CvDraft {
  id: string;
  role_profile_id: string;
  document_id: string;
  base_version_id: string;
  status: "draft" | "exported" | "discarded";
  title: string;
  structure_status_at_creation: "not_extracted" | "reliable" | "partial" | "unreliable";
  created_by: "user" | "ai";
  created_at: string;
  updated_at: string;
}

export interface CvDraftPreview {
  draft_id: string;
  title: string;
  status: string;
  structure_status: string;
  recommendation: string | null;
  sections: Array<{ heading: string; content: string }>;
  edits: Array<{
    requirement: string;
    current_cv_evidence?: string;
    proposed_edit: string;
    edit_kind?: string;
    risk_level?: string;
  }>;
}

export interface CreateCvSuggestionPayload {
  requirement: string;
  current_cv_evidence: string;
  missing_or_weak_evidence: string;
  proposed_edit: string;
  edit_kind: "wording_only" | "requires_user_fact";
  risk_level: "low" | "medium" | "high";
  requires_confirmation: boolean;
  job_id?: string | null;
}

export interface CreateCvDraftPayload {
  title: string;
  suggestion_ids: string[];
  confirmed: boolean;
}
```

- [ ] **Step 4: Add frontend API client functions**

In `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`, extend imports:

```typescript
import type {
  CreateCvDraftPayload,
  CreateCvSuggestionPayload,
  CvDraft,
  CvDraftPreview,
  CvImprovementSuggestion,
  ProfileDocument,
  ProfileDocumentVersion,
} from "../types/profileDocuments";
```

Append:

```typescript
export async function createCvSuggestion(
  roleProfileId: string,
  documentId: string,
  versionId: string,
  payload: CreateCvSuggestionPayload
): Promise<CvImprovementSuggestion> {
  try {
    const response = await apiClient.post<CvImprovementSuggestion>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/versions/${versionId}/suggestions`,
      payload
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function listCvSuggestions(
  roleProfileId: string,
  documentId: string
): Promise<CvImprovementSuggestion[]> {
  try {
    const response = await apiClient.get<{ suggestions: CvImprovementSuggestion[] }>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/suggestions`
    );
    return response.data.suggestions;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function createCvDraft(
  roleProfileId: string,
  documentId: string,
  versionId: string,
  payload: CreateCvDraftPayload
): Promise<CvDraft> {
  try {
    const response = await apiClient.post<CvDraft>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/versions/${versionId}/drafts`,
      payload
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function listCvDrafts(roleProfileId: string, documentId: string): Promise<CvDraft[]> {
  try {
    const response = await apiClient.get<{ drafts: CvDraft[] }>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/drafts`
    );
    return response.data.drafts;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function previewCvDraft(
  roleProfileId: string,
  documentId: string,
  draftId: string
): Promise<CvDraftPreview> {
  try {
    const response = await apiClient.get<CvDraftPreview>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/drafts/${draftId}/preview`
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
```

- [ ] **Step 5: Write failing ProfileDocumentPanel rendering test**

In `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`, add a test that mocks:

- `GET /api/role-profiles/profile-1/documents`
- `GET /api/role-profiles/profile-1/documents/doc-1/suggestions`
- `GET /api/role-profiles/profile-1/documents/doc-1/drafts`
- `GET /api/role-profiles/profile-1/documents/doc-1/drafts/draft-1/preview`

Assert:

```typescript
expect(await screen.findByText("CV suggestions")).toBeInTheDocument();
expect(screen.getByText("FastAPI")).toBeInTheDocument();
expect(screen.getByText("Draft preview")).toBeInTheDocument();
```

- [ ] **Step 6: Add lightweight panels inside ProfileDocumentPanel**

In `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`, add imports:

```typescript
  listCvDrafts,
  listCvSuggestions,
  previewCvDraft,
```

Add types:

```typescript
import type { CvDraft, CvDraftPreview, CvImprovementSuggestion, ProfileDocument } from "../../types/profileDocuments";
```

Add state:

```typescript
const [suggestionsByDocument, setSuggestionsByDocument] = useState<Record<string, CvImprovementSuggestion[]>>({});
const [draftsByDocument, setDraftsByDocument] = useState<Record<string, CvDraft[]>>({});
const [draftPreview, setDraftPreview] = useState<CvDraftPreview | null>(null);
```

Inside `refreshDocuments`, after documents load:

```typescript
const nextDocuments = await listProfileDocuments(activeProfileId);
setDocuments(nextDocuments);
const suggestionEntries = await Promise.all(
  nextDocuments.map(async (document) => [document.id, await listCvSuggestions(activeProfileId, document.id)] as const)
);
const draftEntries = await Promise.all(
  nextDocuments.map(async (document) => [document.id, await listCvDrafts(activeProfileId, document.id)] as const)
);
setSuggestionsByDocument(Object.fromEntries(suggestionEntries));
setDraftsByDocument(Object.fromEntries(draftEntries));
```

Render under each document actions:

```tsx
{(suggestionsByDocument[document.id] ?? []).length > 0 ? (
  <div className="profile-document-subpanel">
    <div className="profile-document-subpanel-title">CV suggestions</div>
    {(suggestionsByDocument[document.id] ?? []).map((suggestion) => (
      <div key={suggestion.id} className="profile-document-suggestion">
        <strong>{suggestion.requirement}</strong>
        <span>{suggestion.proposed_edit}</span>
        <small>{suggestion.edit_kind} · {suggestion.risk_level}</small>
      </div>
    ))}
  </div>
) : null}
{(draftsByDocument[document.id] ?? []).length > 0 ? (
  <div className="profile-document-subpanel">
    <div className="profile-document-subpanel-title">Draft preview</div>
    {(draftsByDocument[document.id] ?? []).map((draft) => (
      <button
        key={draft.id}
        type="button"
        onClick={() => {
          void previewCvDraft(activeProfileId!, document.id, draft.id).then(setDraftPreview);
        }}
      >
        {draft.title}
      </button>
    ))}
    {draftPreview?.draft_id && (
      <div className="profile-document-preview">
        <strong>{draftPreview.title}</strong>
        {draftPreview.recommendation ? <p>{draftPreview.recommendation}</p> : null}
        {draftPreview.edits.map((edit) => (
          <p key={`${draftPreview.draft_id}-${edit.requirement}`}>{edit.proposed_edit}</p>
        ))}
      </div>
    )}
  </div>
) : null}
```

Keep CSS changes minimal and reuse existing document panel classes where possible.

- [ ] **Step 7: Run frontend tests**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/profileDocumentsClient.test.ts src/test/ProfileDocumentPanel.test.tsx
```

Expected: tests pass.

- [ ] **Step 8: Commit Task 6**

```powershell
git add frontend/job-agent-ui/src/types/profileDocuments.ts frontend/job-agent-ui/src/api/profileDocumentsClient.ts frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx
git commit -m "feat: show profile cv suggestions and drafts"
```

---

### Task 7: Final Phase 3 Verification

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

- [ ] **Step 3: Run Phase 3 safety scan**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
rg -n "suggest_cv_improvements|create_cv_edit_draft|preview_cv_edit_draft|safe_payload|stored_path|content_hash|OPENAI_API_KEY|api_key|requires_user_fact|POOR_STRUCTURE_RECOMMENDATION" backend\app frontend\job-agent-ui\src
```

Expected:

- tool safe payloads contain IDs, statuses, counts, titles, and risk labels only
- raw CV sections may appear in backend `ToolResult.content` and draft preview API, but not in `safe_payload`
- original PDF stored paths and content hashes remain backend-only
- no API keys appear in frontend code or tool safe payloads
- `requires_user_fact` suggestions cannot create drafts without user-provided facts

- [ ] **Step 4: Review final diff**

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
git diff --check
git status --short
git diff --stat
```

Expected:

- no whitespace errors
- only Phase 3 files changed
- no PDF export code added
- no active CV promotion from drafts added
- no OCR code added
- no runtime demo/mock data introduced

- [ ] **Step 5: Commit verification cleanup if needed**

Only if Step 1-4 required cleanup edits:

```powershell
git add backend frontend docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-3.md
git commit -m "test: verify profile cv structure drafts"
```

## Self-Review Notes

- Spec coverage: Phase 3 covers structure extraction, reliability status, drafts, suggestions, three Phase 3 tools, frontend suggestion/draft preview UI, poor-structure recommendation, and no original-PDF overwrite.
- Intentional deferrals: PDF export, exported-version view/download, active-version promotion, and job-score-driven end-to-end improvement are Phase 4/5 per roadmap.
- Safety boundary: suggestions requiring user facts are stored only after user facts are supplied in a later phase; this phase rejects direct draft creation for fact-adding edits.
