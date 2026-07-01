# Profile CV PDF Source Of Truth Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make uploaded profile CV PDFs real source-of-truth files with original version records, active CV selection, inline PDF viewing, PDF download, and guarded deletion.

**Architecture:** Extend the existing profile document upload pipeline instead of replacing it. Add version metadata and active CV pointers in SQLite, move file-path responsibility into a focused storage service, expose thin FastAPI routes for view/download/delete/activate, and update the existing React profile document panel with View, Download, Delete, and Set active controls.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, SQLite, pypdf, Qdrant client, React, TypeScript, Vitest, oxlint.

---

## Source Spec

- `docs/superpowers/specs/2026-07-01-profile-cv-pdf-source-of-truth-design.md`
- Roadmap: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-roadmap.md`

## File Structure

Create:

- `backend/app/db/sqlite_migrations.py`
  - Owns idempotent SQLite `ALTER TABLE` additions for existing local databases.
- `backend/app/services/profile_document_storage_service.py`
  - Owns safe storage paths, filename sanitization, file lookup, copy, and deletion.
- `backend/tests/test_sqlite_migrations.py`
  - Tests idempotent migration behavior on existing tables.
- `backend/tests/test_profile_document_storage_service.py`
  - Tests path safety, safe filenames, file copy, and stored file lookup.

Modify:

- `backend/app/db/models.py`
  - Add `ProfileDocumentVersion`.
  - Add active CV pointers to `RoleProfile`.
  - Add version references to profile documents and chunks.
- `backend/app/db/session.py`
  - Add `profile_document_versions` to expected table guard.
- `backend/app/api/schemas.py`
  - Add version metadata response, active CV response, and expanded document response fields.
- `backend/app/services/profile_document_service.py`
  - Use storage service.
  - Create original version during upload.
  - Set first ready CV active.
  - Provide file metadata, active selection, and delete operations.
- `backend/app/services/qdrant_service.py`
  - Add document-vector deletion by `document_id`.
- `backend/app/api/routes_profile_documents.py`
  - Add file, download, delete, version list, active CV, and activate endpoints.
- `backend/tests/test_profile_document_service.py`
  - Extend service tests for versions, active CV, deletion, and file metadata.
- `backend/tests/test_routes_profile_documents.py`
  - Extend route tests for file, download, delete, active CV, and activate endpoints.
- `backend/tests/test_db_session.py`
  - Update expected table set behavior if asserted directly.
- `frontend/job-agent-ui/src/types/profileDocuments.ts`
  - Add version and active CV types.
- `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`
  - Add file/download URL helpers and delete/activate/list versions clients.
- `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
  - Add View, Download, Delete, Set active, active marker, and version metadata display.
- `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`
  - Test new client calls and URLs.
- `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`
  - Test new controls and active marker.

Do not modify:

- job ingestion/scoring business logic
- chat pasted job extraction behavior
- CV draft/edit/export features
- OCR behavior

---

### Task 1: Add Version And Active CV Schema

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/app/api/schemas.py`
- Test: `backend/tests/test_profile_document_service.py`
- Test: `backend/tests/test_db_session.py`

- [x] **Step 1: Write failing model registration test**

Update `backend/tests/test_profile_document_service.py` model metadata test:

```python
def test_profile_document_models_are_registered_with_metadata():
    assert "profile_documents" in Base.metadata.tables
    assert "profile_document_versions" in Base.metadata.tables
    assert "profile_document_chunks" in Base.metadata.tables
    assert ProfileDocument.__tablename__ == "profile_documents"
    assert ProfileDocumentVersion.__tablename__ == "profile_document_versions"
    assert ProfileDocumentChunk.__tablename__ == "profile_document_chunks"
```

Add the import:

```python
from app.db.models import Base, ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion
```

- [x] **Step 2: Run model test and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py::test_profile_document_models_are_registered_with_metadata -q
```

Expected: fail because `ProfileDocumentVersion` does not exist.

- [x] **Step 3: Add schema fields and version model**

In `backend/app/db/models.py`, extend `RoleProfile` with active CV pointers:

```python
    active_cv_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active_cv_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
```

Extend `ProfileDocument`:

```python
    document_kind: Mapped[str] = mapped_column(Text, nullable=False, default="cv")
    active_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
```

Add `ProfileDocumentVersion` after `ProfileDocument`:

```python
class ProfileDocumentVersion(Base):
    """Real PDF version for an uploaded or exported profile CV."""
    __tablename__ = "profile_document_versions"

    __table_args__ = (
        Index("idx_profile_document_versions_document_number", "document_id", "version_number"),
        Index("idx_profile_document_versions_role_profile_created", "role_profile_id", text("created_at DESC")),
    )

    id: Mapped[uuid_pk]
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profile_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("role_profiles.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="original_upload")
    parent_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text_chars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_status: Mapped[str] = mapped_column(Text, nullable=False, default="processing")
    structure_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_extracted")
    structure_confidence: Mapped[float | None] = mapped_column(nullable=True)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    created_at: Mapped[created_timestamp]
    updated_at: Mapped[updated_timestamp]
```

Extend `ProfileDocumentChunk`:

```python
    version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("profile_document_versions.id", ondelete="CASCADE"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="profile_cv")
```

- [x] **Step 4: Update DB table guard**

In `backend/app/db/session.py`, add `"profile_document_versions"` to `expected_tables`:

```python
        "profile_document_versions",
```

- [x] **Step 5: Add API response schemas**

In `backend/app/api/schemas.py`, add:

```python
class ProfileDocumentVersionResponse(ApiSchema):
    id: UUID
    document_id: UUID
    role_profile_id: UUID
    version_number: int
    source_type: str
    display_name: str
    filename: str
    mime_type: str
    file_size_bytes: int
    extracted_text_chars: int
    chunk_count: int
    extraction_status: str
    structure_status: str
    structure_confidence: float | None
    error_reason: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class ProfileDocumentVersionListResponse(ApiSchema):
    versions: list[ProfileDocumentVersionResponse] = Field(default_factory=list)


class ActiveCvResponse(ApiSchema):
    document: ProfileDocumentResponse | None = None
    version: ProfileDocumentVersionResponse | None = None


class ActivateCvVersionRequest(ApiSchema):
    confirmed: bool = False
```

Extend `ProfileDocumentResponse`:

```python
    document_kind: str
    active_version_id: UUID | None
    is_active: bool = False
```

- [x] **Step 6: Run model and session tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py::test_profile_document_models_are_registered_with_metadata tests\test_db_session.py -q
```

Expected: tests pass after imports and expected tables are updated.

- [x] **Step 7: Commit Task 1**

```powershell
git add backend/app/db/models.py backend/app/db/session.py backend/app/api/schemas.py backend/tests/test_profile_document_service.py backend/tests/test_db_session.py
git commit -m "feat: add profile cv version schema"
```

---

### Task 2: Add Idempotent SQLite Migration Support

**Files:**
- Create: `backend/app/db/sqlite_migrations.py`
- Modify: `backend/app/db/session.py`
- Test: `backend/tests/test_sqlite_migrations.py`

- [x] **Step 1: Write failing migration tests**

Create `backend/tests/test_sqlite_migrations.py`:

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _columns(conn, table_name: str) -> set[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table_name})"))).mappings().all()
    return {str(row["name"]) for row in rows}


@pytest.mark.asyncio
async def test_sqlite_migration_adds_profile_cv_columns():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)

        role_profile_columns = await _columns(conn, "role_profiles")
        document_columns = await _columns(conn, "profile_documents")
        chunk_columns = await _columns(conn, "profile_document_chunks")

    assert {"active_cv_document_id", "active_cv_version_id"} <= role_profile_columns
    assert {"document_kind", "active_version_id"} <= document_columns
    assert {"version_id", "source_type"} <= chunk_columns
    await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_migration_is_idempotent():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)
        await apply_sqlite_migrations(conn)

        role_profile_columns = await _columns(conn, "role_profiles")

    assert "active_cv_document_id" in role_profile_columns
    await engine.dispose()
```

- [x] **Step 2: Run migration tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_sqlite_migrations.py -q
```

Expected: fail because `app.db.sqlite_migrations` does not exist.

- [x] **Step 3: Implement migration helper**

Create `backend/app/db/sqlite_migrations.py`:

```python
"""Idempotent SQLite schema migrations for local persisted databases."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def _column_names(conn: AsyncConnection, table_name: str) -> set[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table_name})"))).mappings().all()
    return {str(row["name"]) for row in rows}


async def _add_column_if_missing(
    conn: AsyncConnection,
    table_name: str,
    column_name: str,
    ddl: str,
) -> None:
    columns = await _column_names(conn, table_name)
    if column_name in columns:
        return
    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


async def apply_sqlite_migrations(conn: AsyncConnection) -> None:
    if conn.dialect.name != "sqlite":
        return

    await _add_column_if_missing(
        conn,
        "role_profiles",
        "active_cv_document_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "role_profiles",
        "active_cv_version_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "profile_documents",
        "document_kind",
        "TEXT NOT NULL DEFAULT 'cv'",
    )
    await _add_column_if_missing(
        conn,
        "profile_documents",
        "active_version_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "profile_document_chunks",
        "version_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "profile_document_chunks",
        "source_type",
        "TEXT NOT NULL DEFAULT 'profile_cv'",
    )
```

- [x] **Step 4: Wire migrations into database initialization**

In `backend/app/db/session.py`, import:

```python
from app.db.sqlite_migrations import apply_sqlite_migrations
```

Update `init_db()` after `create_all`:

```python
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await apply_sqlite_migrations(conn)
```

- [x] **Step 5: Run migration and DB session tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_sqlite_migrations.py tests\test_db_session.py -q
```

Expected: migration tests and DB session tests pass.

- [x] **Step 6: Commit Task 2**

```powershell
git add backend/app/db/sqlite_migrations.py backend/app/db/session.py backend/tests/test_sqlite_migrations.py
git commit -m "feat: add profile cv sqlite migrations"
```

---

### Task 3: Add Safe PDF Storage Service

**Files:**
- Create: `backend/app/services/profile_document_storage_service.py`
- Test: `backend/tests/test_profile_document_storage_service.py`

- [x] **Step 1: Write failing storage service tests**

Create `backend/tests/test_profile_document_storage_service.py`:

```python
from pathlib import Path

import pytest


def test_storage_service_copies_pdf_under_profile_document_version(tmp_path):
    from app.services.profile_document_storage_service import ProfileDocumentStorageService

    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-real")
    service = ProfileDocumentStorageService(root_dir=tmp_path / "storage")

    stored = service.copy_pdf(
        source,
        role_profile_id="profile-1",
        document_id="doc-1",
        version_id="ver-1",
        directory_name="original",
    )

    assert stored.read_bytes() == b"%PDF-real"
    assert stored.name == "ver-1.pdf"
    assert "profile-1" in str(stored)
    assert "doc-1" in str(stored)
    assert "original" in str(stored)


def test_storage_service_rejects_paths_outside_root(tmp_path):
    from app.services.profile_document_storage_service import ProfileDocumentStorageService

    service = ProfileDocumentStorageService(root_dir=tmp_path / "storage")
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-real")

    with pytest.raises(ValueError, match="Stored PDF path is outside storage root"):
        service.resolve_stored_pdf(outside)


def test_storage_service_builds_safe_download_filename(tmp_path):
    from app.services.profile_document_storage_service import ProfileDocumentStorageService

    service = ProfileDocumentStorageService(root_dir=tmp_path / "storage")

    assert (
        service.safe_download_filename("AI Engineer / Intern", "My CV (final).pdf", "v1")
        == "AI_Engineer_Intern_My_CV_final_v1.pdf"
    )
```

- [x] **Step 2: Run storage tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_storage_service.py -q
```

Expected: fail because `profile_document_storage_service.py` does not exist.

- [x] **Step 3: Implement storage service**

Create `backend/app/services/profile_document_storage_service.py`:

```python
"""Safe file storage helpers for profile CV PDFs."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.core.config import settings


class ProfileDocumentStorageService:
    def __init__(self, *, root_dir: Path | None = None) -> None:
        self.root_dir = (
            root_dir
            if root_dir is not None
            else Path(settings.SQLITE_DB_PATH).resolve().parent / "uploads" / "profile_documents"
        ).resolve()

    def copy_pdf(
        self,
        source_path: Path,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        directory_name: str,
    ) -> Path:
        storage_dir = self.root_dir / role_profile_id / document_id / directory_name
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_path = storage_dir / f"{version_id}.pdf"
        shutil.copyfile(source_path, stored_path)
        return self.resolve_stored_pdf(stored_path)

    def resolve_stored_pdf(self, stored_path: str | Path) -> Path:
        resolved = Path(stored_path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError("Stored PDF file was not found")
        if self.root_dir not in resolved.parents:
            raise ValueError("Stored PDF path is outside storage root")
        if resolved.suffix.lower() != ".pdf":
            raise ValueError("Stored file is not a PDF")
        return resolved

    def delete_document_files(self, *, role_profile_id: str, document_id: str) -> None:
        document_dir = (self.root_dir / role_profile_id / document_id).resolve()
        if self.root_dir not in document_dir.parents:
            raise ValueError("Document directory is outside storage root")
        if document_dir.exists():
            shutil.rmtree(document_dir)

    @staticmethod
    def safe_download_filename(profile_label: str, document_label: str, version_label: str) -> str:
        raw = f"{profile_label}_{document_label}_{version_label}"
        raw = raw.removesuffix(".pdf")
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
        safe = re.sub(r"_+", "_", safe)
        if not safe:
            safe = "profile_cv"
        return f"{safe[:140]}.pdf"
```

- [x] **Step 4: Run storage tests and verify pass**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_storage_service.py -q
```

Expected: `3 passed`.

- [x] **Step 5: Commit Task 3**

```powershell
git add backend/app/services/profile_document_storage_service.py backend/tests/test_profile_document_storage_service.py
git commit -m "feat: add profile cv pdf storage service"
```

---

### Task 4: Create Original Versions And Active CV Selection

**Files:**
- Modify: `backend/app/services/profile_document_service.py`
- Modify: `backend/app/db/models.py`
- Test: `backend/tests/test_profile_document_service.py`

- [x] **Step 1: Write failing service test for original version and active CV**

Append to `backend/tests/test_profile_document_service.py`:

```python
@pytest.mark.asyncio
async def test_create_document_from_pdf_creates_original_version_and_sets_first_active(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    from app.db.models import ProfileDocumentVersion, RoleProfile

    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "cv.pdf"
    source_path.write_bytes(b"%PDF-test")
    service = ProfileDocumentService(
        extractor=FakeExtractor(),
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

    versions = (
        await db_session.execute(
            select(ProfileDocumentVersion).where(ProfileDocumentVersion.document_id == document.id)
        )
    ).scalars().all()
    profile = await db_session.get(RoleProfile, test_role_profile.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].source_type == "original_upload"
    assert versions[0].stored_path.endswith(".pdf")
    assert document.active_version_id == versions[0].id
    assert profile.active_cv_document_id == document.id
    assert profile.active_cv_version_id == versions[0].id
```

- [x] **Step 2: Run new service test and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py::test_create_document_from_pdf_creates_original_version_and_sets_first_active -q
```

Expected: fail because upload does not create a `ProfileDocumentVersion`.

- [x] **Step 3: Update service imports and constructor**

In `backend/app/services/profile_document_service.py`, update imports:

```python
from app.db.models import ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion, RoleProfile
from app.services.profile_document_storage_service import ProfileDocumentStorageService
```

Add a storage dependency to `ProfileDocumentService.__init__`:

```python
        storage: ProfileDocumentStorageService | None = None,
```

Set it:

```python
        self.storage = storage or ProfileDocumentStorageService()
```

- [x] **Step 4: Replace copy logic with version-aware storage**

In `create_document_from_pdf(...)`, generate `version_id` next to `document_id`:

```python
        document_id = str(uuid4())
        version_id = str(uuid4())
        stored_path = self.storage.copy_pdf(
            source_path,
            role_profile_id=role_profile_id,
            document_id=document_id,
            version_id=version_id,
            directory_name="original",
        )
```

Create a `ProfileDocumentVersion` after `document`:

```python
        version = ProfileDocumentVersion(
            id=version_id,
            document_id=document_id,
            role_profile_id=role_profile_id,
            version_number=1,
            source_type="original_upload",
            display_name="Original upload",
            filename=original_filename,
            stored_path=str(stored_path),
            content_hash=content_hash,
            mime_type=mime_type,
            file_size_bytes=size,
            extraction_status="processing",
            structure_status="not_extracted",
            created_by="user",
        )
        document.active_version_id = version_id
        session.add(version)
```

When extraction succeeds, mirror extraction counts onto version:

```python
            version.extracted_text_chars = len(text)
            version.chunk_count = len(chunks)
            version.extraction_status = "ready"
            version.error_reason = None
```

When creating `ProfileDocumentChunk`, set:

```python
                    version_id=version.id,
                    source_type="profile_cv",
```

After success and before commit, set first active CV only if none exists:

```python
            profile = await session.get(RoleProfile, role_profile_id)
            if profile and profile.active_cv_version_id is None:
                profile.active_cv_document_id = document.id
                profile.active_cv_version_id = version.id
```

In `_mark_failed(...)`, also set the version failed. Change signature:

```python
    async def _mark_failed(
        session: AsyncSession,
        document: ProfileDocument,
        reason: str,
        version: ProfileDocumentVersion | None = None,
    ) -> None:
```

Body:

```python
        document.status = "failed"
        document.error_reason = reason[:500]
        if version is not None:
            version.extraction_status = "failed"
            version.error_reason = reason[:500]
        await session.commit()
        await session.refresh(document)
```

Pass `version` from both exception handlers.

- [x] **Step 5: Remove obsolete `_copy_to_storage` helper**

Delete `_copy_to_storage(...)` from `ProfileDocumentService` after the new storage service is used.

- [x] **Step 6: Run service tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py tests\test_profile_document_storage_service.py -q
```

Expected: all tests pass.

- [x] **Step 7: Commit Task 4**

```powershell
git add backend/app/services/profile_document_service.py backend/app/db/models.py backend/tests/test_profile_document_service.py
git commit -m "feat: create original profile cv versions"
```

---

### Task 5: Add File, Download, Active, Version, And Delete Services

**Files:**
- Modify: `backend/app/services/profile_document_service.py`
- Modify: `backend/app/services/qdrant_service.py`
- Test: `backend/tests/test_profile_document_service.py`
- Test: `backend/tests/test_qdrant_service.py`

- [x] **Step 1: Add service tests for active selection and file lookup**

Append to `backend/tests/test_profile_document_service.py`:

```python
@pytest.mark.asyncio
async def test_get_document_file_returns_original_version_file_metadata(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "cv.pdf"
    source_path.write_bytes(b"%PDF-test")
    service = ProfileDocumentService(
        extractor=FakeExtractor(),
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

    file_info = await service.get_document_file(
        db_session,
        role_profile_id=test_role_profile.id,
        document_id=document.id,
    )

    assert file_info.path.read_bytes() == b"%PDF-test"
    assert file_info.media_type == "application/pdf"
    assert file_info.inline_filename.endswith(".pdf")
    assert file_info.download_filename.endswith(".pdf")
```

Append active selection test:

```python
@pytest.mark.asyncio
async def test_set_active_version_requires_existing_profile_document_and_version(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    from app.db.models import RoleProfile

    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "cv.pdf"
    source_path.write_bytes(b"%PDF-test")
    service = ProfileDocumentService(
        extractor=FakeExtractor(),
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

    version = await service.set_active_version(
        db_session,
        role_profile_id=test_role_profile.id,
        document_id=document.id,
        version_id=document.active_version_id,
    )
    profile = await db_session.get(RoleProfile, test_role_profile.id)

    assert version.id == document.active_version_id
    assert profile.active_cv_document_id == document.id
    assert profile.active_cv_version_id == version.id
```

- [x] **Step 2: Add service test for active delete guard**

Append:

```python
@pytest.mark.asyncio
async def test_delete_document_rejects_active_cv_without_clear_flag(
    db_session,
    test_role_profile,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "job_matching.db"))
    source_path = tmp_path / "cv.pdf"
    source_path.write_bytes(b"%PDF-test")
    service = ProfileDocumentService(
        extractor=FakeExtractor(),
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

    with pytest.raises(ValueError, match="Cannot delete the active CV"):
        await service.delete_document(
            db_session,
            role_profile_id=test_role_profile.id,
            document_id=document.id,
            clear_active=False,
        )
```

- [x] **Step 3: Run new service tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py -q
```

Expected: fail because service methods do not exist.

- [x] **Step 4: Add file info dataclass and service methods**

In `backend/app/services/profile_document_service.py`, add:

```python
from dataclasses import dataclass
```

Add:

```python
@dataclass(frozen=True)
class ProfileDocumentFileInfo:
    path: Path
    media_type: str
    inline_filename: str
    download_filename: str
```

Add helper:

```python
    async def _get_document_and_version(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str | None = None,
    ) -> tuple[ProfileDocument, ProfileDocumentVersion]:
        document = await session.get(ProfileDocument, document_id)
        if document is None or document.role_profile_id != role_profile_id:
            raise LookupError("profile document not found")
        selected_version_id = version_id or document.active_version_id
        if selected_version_id is None:
            raise LookupError("profile document has no active version")
        version = await session.get(ProfileDocumentVersion, selected_version_id)
        if (
            version is None
            or version.document_id != document.id
            or version.role_profile_id != role_profile_id
        ):
            raise LookupError("profile document version not found")
        return document, version
```

Add file lookup:

```python
    async def get_document_file(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str | None = None,
    ) -> ProfileDocumentFileInfo:
        document, version = await self._get_document_and_version(
            session,
            role_profile_id=role_profile_id,
            document_id=document_id,
            version_id=version_id,
        )
        path = self.storage.resolve_stored_pdf(version.stored_path)
        filename = self.storage.safe_download_filename(
            "profile_cv",
            document.original_filename,
            f"v{version.version_number}",
        )
        return ProfileDocumentFileInfo(
            path=path,
            media_type="application/pdf",
            inline_filename=filename,
            download_filename=filename,
        )
```

Add version list:

```python
    async def list_versions(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
    ) -> list[ProfileDocumentVersion]:
        result = await session.execute(
            select(ProfileDocumentVersion)
            .where(ProfileDocumentVersion.role_profile_id == role_profile_id)
            .where(ProfileDocumentVersion.document_id == document_id)
            .order_by(ProfileDocumentVersion.version_number.asc(), ProfileDocumentVersion.created_at.asc())
        )
        return list(result.scalars())
```

Add active CV lookup:

```python
    async def get_active_cv(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
    ) -> tuple[ProfileDocument | None, ProfileDocumentVersion | None]:
        profile = await session.get(RoleProfile, role_profile_id)
        if profile is None or profile.active_cv_document_id is None or profile.active_cv_version_id is None:
            return None, None
        document = await session.get(ProfileDocument, profile.active_cv_document_id)
        version = await session.get(ProfileDocumentVersion, profile.active_cv_version_id)
        if document is None or version is None:
            return None, None
        if document.role_profile_id != role_profile_id or version.role_profile_id != role_profile_id:
            return None, None
        return document, version
```

Add active setter:

```python
    async def set_active_version(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str | None,
    ) -> ProfileDocumentVersion:
        if version_id is None:
            raise LookupError("profile document version not found")
        document, version = await self._get_document_and_version(
            session,
            role_profile_id=role_profile_id,
            document_id=document_id,
            version_id=version_id,
        )
        if version.extraction_status != "ready":
            raise ValueError("Only ready CV versions can be activated")
        profile = await session.get(RoleProfile, role_profile_id)
        if profile is None:
            raise LookupError("role profile not found")
        document.active_version_id = version.id
        profile.active_cv_document_id = document.id
        profile.active_cv_version_id = version.id
        await session.commit()
        await session.refresh(version)
        return version
```

Add delete method:

```python
    async def delete_document(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        clear_active: bool = False,
    ) -> None:
        document = await session.get(ProfileDocument, document_id)
        if document is None or document.role_profile_id != role_profile_id:
            raise LookupError("profile document not found")
        profile = await session.get(RoleProfile, role_profile_id)
        is_active = bool(profile and profile.active_cv_document_id == document.id)
        if is_active and not clear_active:
            raise ValueError("Cannot delete the active CV without clearing active selection")
        if is_active and profile:
            profile.active_cv_document_id = None
            profile.active_cv_version_id = None
        await session.delete(document)
        await session.commit()
        self.storage.delete_document_files(role_profile_id=role_profile_id, document_id=document_id)
```

- [x] **Step 5: Add Qdrant document deletion method**

In `backend/app/services/qdrant_service.py`, add a method:

```python
    async def delete_profile_document_points(self, *, document_id: str) -> None:
        await self.ensure_profile_document_collection()
        try:
            await self.client.delete(
                collection_name=PROFILE_DOCUMENT_COLLECTION_NAME,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except (UnexpectedResponse, ResponseHandlingException, Exception) as exc:
            self._log_qdrant_error("delete_profile_document_points", exc)
            raise QdrantServiceError("Qdrant profile document delete failed") from exc
```

Use the existing `qmodels` alias already imported by `backend/app/services/qdrant_service.py`.

Add a protocol method to `ProfileDocumentVectorStore`:

```python
    async def delete_profile_document_points(self, *, document_id: str) -> None:
        ...
```

Update test fakes with:

```python
    async def delete_profile_document_points(self, *, document_id: str) -> None:
        return None
```

Call it in `delete_document(...)` before deleting the DB row:

```python
        await self.vector_store.delete_profile_document_points(document_id=document.id)
```

- [x] **Step 6: Run service and qdrant tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_profile_document_service.py tests\test_qdrant_service.py -q
```

Expected: tests pass.

- [x] **Step 7: Commit Task 5**

```powershell
git add backend/app/services/profile_document_service.py backend/app/services/qdrant_service.py backend/tests/test_profile_document_service.py backend/tests/test_qdrant_service.py
git commit -m "feat: manage active profile cv files"
```

---

### Task 6: Add Backend Routes For View, Download, Delete, Versions, And Active CV

**Files:**
- Modify: `backend/app/api/routes_profile_documents.py`
- Test: `backend/tests/test_routes_profile_documents.py`

- [x] **Step 1: Write failing route tests**

Append to `backend/tests/test_routes_profile_documents.py`:

```python
@pytest.mark.asyncio
async def test_view_profile_document_returns_inline_pdf(client, role_profile):
    upload = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )
    document_id = upload.json()["id"]

    response = await client.get(
        f"/api/role-profiles/{role_profile.id}/documents/{document_id}/file"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "inline" in response.headers["content-disposition"]
    assert response.content == b"%PDF-test"


@pytest.mark.asyncio
async def test_download_profile_document_returns_attachment_pdf(client, role_profile):
    upload = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )
    document_id = upload.json()["id"]

    response = await client.get(
        f"/api/role-profiles/{role_profile.id}/documents/{document_id}/download"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]
    assert response.content == b"%PDF-test"


@pytest.mark.asyncio
async def test_delete_active_profile_document_requires_clear_active(client, role_profile):
    upload = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )
    document_id = upload.json()["id"]

    response = await client.delete(
        f"/api/role-profiles/{role_profile.id}/documents/{document_id}"
    )

    assert response.status_code == 409
    assert "active CV" in response.json()["detail"]
```

Add activate test:

```python
@pytest.mark.asyncio
async def test_activate_profile_cv_version_requires_confirmation(client, role_profile):
    upload = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents",
        files={"file": ("cv.pdf", b"%PDF-test", "application/pdf")},
    )
    document = upload.json()
    version_id = document["active_version_id"]

    response = await client.post(
        f"/api/role-profiles/{role_profile.id}/documents/{document['id']}/versions/{version_id}/activate",
        json={"confirmed": False},
    )

    assert response.status_code == 409
    assert "requires confirmation" in response.json()["detail"]
```

- [x] **Step 2: Run route tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_profile_documents.py -q
```

Expected: fail because routes do not exist.

- [x] **Step 3: Add route imports**

In `backend/app/api/routes_profile_documents.py`, update imports:

```python
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
```

Import new schemas:

```python
from app.api.schemas import (
    ActivateCvVersionRequest,
    ActiveCvResponse,
    ProfileDocumentListResponse,
    ProfileDocumentResponse,
    ProfileDocumentVersionResponse,
    ProfileDocumentVersionListResponse,
)
```

- [x] **Step 4: Add helper for FileResponse**

Add:

```python
def _pdf_file_response(file_info, *, as_attachment: bool) -> FileResponse:
    filename = file_info.download_filename if as_attachment else file_info.inline_filename
    disposition = "attachment" if as_attachment else "inline"
    return FileResponse(
        path=file_info.path,
        media_type=file_info.media_type,
        filename=filename,
        content_disposition_type=disposition,
    )
```

- [x] **Step 5: Add file and download endpoints**

Add:

```python
@router.get("/{document_id}/file")
async def view_profile_document(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=False)


@router.get("/{document_id}/download")
async def download_profile_document(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=True)
```

Add version file/download endpoints similarly using `version_id`:

```python
@router.get("/{document_id}/versions/{version_id}/file")
async def view_profile_document_version(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            version_id=str(version_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=False)
```

```python
@router.get("/{document_id}/versions/{version_id}/download")
async def download_profile_document_version(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    try:
        file_info = await profile_document_service.get_document_file(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            version_id=str(version_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _pdf_file_response(file_info, as_attachment=True)
```

- [x] **Step 6: Add active CV, versions, activate, and delete routes**

Add a second router for active CV routes near the existing `router`:

```python
active_cv_router = APIRouter(
    prefix="/role-profiles/{role_profile_id}/active-cv",
    tags=["profile-documents"],
)
```

Add active CV endpoint to `active_cv_router`:

```python
@active_cv_router.get("", response_model=ActiveCvResponse)
async def get_active_cv(
    role_profile_id: UUID,
    session: SessionDep,
) -> ActiveCvResponse:
    await _require_profile(session, str(role_profile_id))
    document, version = await profile_document_service.get_active_cv(
        session,
        role_profile_id=str(role_profile_id),
    )
    return ActiveCvResponse(document=document, version=version)
```

Add active CV file and download endpoints:

```python
@active_cv_router.get("/file")
async def view_active_cv(
    role_profile_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    document, version = await profile_document_service.get_active_cv(
        session,
        role_profile_id=str(role_profile_id),
    )
    if document is None or version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active CV not found")
    file_info = await profile_document_service.get_document_file(
        session,
        role_profile_id=str(role_profile_id),
        document_id=document.id,
        version_id=version.id,
    )
    return _pdf_file_response(file_info, as_attachment=False)


@active_cv_router.get("/download")
async def download_active_cv(
    role_profile_id: UUID,
    session: SessionDep,
) -> FileResponse:
    await _require_profile(session, str(role_profile_id))
    document, version = await profile_document_service.get_active_cv(
        session,
        role_profile_id=str(role_profile_id),
    )
    if document is None or version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active CV not found")
    file_info = await profile_document_service.get_document_file(
        session,
        role_profile_id=str(role_profile_id),
        document_id=document.id,
        version_id=version.id,
    )
    return _pdf_file_response(file_info, as_attachment=True)
```

Update `backend/app/main.py` imports:

```python
from app.api.routes_profile_documents import (
    active_cv_router,
    router as profile_documents_router,
)
```

Include the active CV router:

```python
app.include_router(profile_documents_router, prefix="/api")
app.include_router(active_cv_router, prefix="/api")
```

Add versions:

```python
@router.get("/{document_id}/versions", response_model=ProfileDocumentVersionListResponse)
async def list_profile_document_versions(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
) -> ProfileDocumentVersionListResponse:
    await _require_profile(session, str(role_profile_id))
    versions = await profile_document_service.list_versions(
        session,
        role_profile_id=str(role_profile_id),
        document_id=str(document_id),
    )
    return ProfileDocumentVersionListResponse(versions=versions)
```

Add activate:

```python
@router.post("/{document_id}/versions/{version_id}/activate", response_model=ProfileDocumentVersionResponse)
async def activate_profile_cv_version(
    role_profile_id: UUID,
    document_id: UUID,
    version_id: UUID,
    request: ActivateCvVersionRequest,
    session: SessionDep,
):
    await _require_profile(session, str(role_profile_id))
    if not request.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setting the active CV requires confirmation",
        )
    try:
        return await profile_document_service.set_active_version(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            version_id=str(version_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
```

Add delete:

```python
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_document(
    role_profile_id: UUID,
    document_id: UUID,
    session: SessionDep,
    clear_active: bool = Query(False),
) -> None:
    await _require_profile(session, str(role_profile_id))
    try:
        await profile_document_service.delete_document(
            session,
            role_profile_id=str(role_profile_id),
            document_id=str(document_id),
            clear_active=clear_active,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
```

- [x] **Step 7: Run route tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests\test_routes_profile_documents.py -q
```

Expected: all profile document route tests pass.

- [x] **Step 8: Commit Task 6**

```powershell
git add backend/app/api/routes_profile_documents.py backend/app/main.py backend/tests/test_routes_profile_documents.py
git commit -m "feat: serve profile cv pdf files"
```

---

### Task 7: Add Frontend Client Types And API Calls

**Files:**
- Modify: `frontend/job-agent-ui/src/types/profileDocuments.ts`
- Modify: `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`
- Test: `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`

- [x] **Step 1: Write failing client tests**

Append to `frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts`:

```ts
import {
  activateProfileDocumentVersion,
  deleteProfileDocument,
  getProfileDocumentDownloadUrl,
  getProfileDocumentFileUrl,
  listProfileDocumentVersions,
} from "../api/profileDocumentsClient";
```

Add tests:

```ts
it("builds view and download URLs for real PDF files", () => {
  expect(getProfileDocumentFileUrl("profile-1", "doc-1")).toBe(
    "/api/role-profiles/profile-1/documents/doc-1/file"
  );
  expect(getProfileDocumentDownloadUrl("profile-1", "doc-1")).toBe(
    "/api/role-profiles/profile-1/documents/doc-1/download"
  );
});

it("lists profile document versions", async () => {
  getSpy.mockResolvedValueOnce({ data: { versions: [{ id: "version-1" }] } });

  const result = await listProfileDocumentVersions("profile-1", "doc-1");

  expect(getSpy).toHaveBeenCalledWith(
    "/api/role-profiles/profile-1/documents/doc-1/versions"
  );
  expect(result[0].id).toBe("version-1");
});

it("activates a profile document version with confirmation", async () => {
  postSpy.mockResolvedValueOnce({ data: { id: "version-1" } });

  await activateProfileDocumentVersion("profile-1", "doc-1", "version-1");

  expect(postSpy).toHaveBeenCalledWith(
    "/api/role-profiles/profile-1/documents/doc-1/versions/version-1/activate",
    { confirmed: true }
  );
});

it("deletes a profile document", async () => {
  deleteSpy.mockResolvedValueOnce({});

  await deleteProfileDocument("profile-1", "doc-1", { clearActive: true });

  expect(deleteSpy).toHaveBeenCalledWith(
    "/api/role-profiles/profile-1/documents/doc-1",
    { params: { clear_active: true } }
  );
});
```

Ensure `deleteSpy` exists in the test setup:

```ts
const deleteSpy = vi.spyOn(apiClient, "delete");
```

- [x] **Step 2: Run client tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/profileDocumentsClient.test.ts
```

Expected: fail because client functions/types do not exist.

- [x] **Step 3: Update frontend types**

Update `frontend/job-agent-ui/src/types/profileDocuments.ts`:

```ts
export interface ProfileDocumentVersion {
  id: string;
  document_id: string;
  role_profile_id: string;
  version_number: number;
  source_type: "original_upload" | "exported_draft";
  display_name: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  extracted_text_chars: number;
  chunk_count: number;
  extraction_status: "processing" | "ready" | "failed";
  structure_status: "not_extracted" | "reliable" | "partial" | "unreliable";
  structure_confidence: number | null;
  error_reason: string | null;
  created_by: "user" | "ai" | "system";
  created_at: string;
  updated_at: string;
}

export interface ProfileDocument {
  id: string;
  role_profile_id: string;
  original_filename: string;
  document_kind: "cv";
  active_version_id: string | null;
  is_active: boolean;
  mime_type: string;
  file_size_bytes: number;
  extracted_text_chars: number;
  chunk_count: number;
  status: "processing" | "ready" | "failed";
  error_reason: string | null;
  created_at: string;
  updated_at: string;
}
```

- [x] **Step 4: Add API client functions**

In `frontend/job-agent-ui/src/api/profileDocumentsClient.ts`, add:

```ts
import type { ProfileDocument, ProfileDocumentVersion } from "../types/profileDocuments";
```

Add URL helpers:

```ts
export function getProfileDocumentFileUrl(roleProfileId: string, documentId: string): string {
  return `/api/role-profiles/${roleProfileId}/documents/${documentId}/file`;
}

export function getProfileDocumentDownloadUrl(roleProfileId: string, documentId: string): string {
  return `/api/role-profiles/${roleProfileId}/documents/${documentId}/download`;
}
```

Add version list:

```ts
export async function listProfileDocumentVersions(
  roleProfileId: string,
  documentId: string
): Promise<ProfileDocumentVersion[]> {
  try {
    const response = await apiClient.get<{ versions: ProfileDocumentVersion[] }>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/versions`
    );
    return response.data.versions;
  } catch (error) {
    throw normalizeError(error);
  }
}
```

Add activate:

```ts
export async function activateProfileDocumentVersion(
  roleProfileId: string,
  documentId: string,
  versionId: string
): Promise<ProfileDocumentVersion> {
  try {
    const response = await apiClient.post<ProfileDocumentVersion>(
      `/api/role-profiles/${roleProfileId}/documents/${documentId}/versions/${versionId}/activate`,
      { confirmed: true }
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
```

Add delete:

```ts
export async function deleteProfileDocument(
  roleProfileId: string,
  documentId: string,
  options: { clearActive?: boolean } = {}
): Promise<void> {
  try {
    await apiClient.delete(`/api/role-profiles/${roleProfileId}/documents/${documentId}`, {
      params: { clear_active: Boolean(options.clearActive) },
    });
  } catch (error) {
    throw normalizeError(error);
  }
}
```

- [x] **Step 5: Run frontend client tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/profileDocumentsClient.test.ts
```

Expected: profile document client tests pass.

- [x] **Step 6: Commit Task 7**

```powershell
git add frontend/job-agent-ui/src/types/profileDocuments.ts frontend/job-agent-ui/src/api/profileDocumentsClient.ts frontend/job-agent-ui/src/test/profileDocumentsClient.test.ts
git commit -m "feat(ui): add profile cv document client actions"
```

---

### Task 8: Add Profile CV UI Controls

**Files:**
- Modify: `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
- Modify: `frontend/job-agent-ui/src/styles/app.css`
- Test: `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`

- [x] **Step 1: Write failing UI tests**

Update the mock in `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`:

```ts
vi.mock("../api/profileDocumentsClient", () => ({
  activateProfileDocumentVersion: vi.fn(),
  deleteProfileDocument: vi.fn(),
  getProfileDocumentDownloadUrl: vi.fn((profileId, documentId) => `/api/role-profiles/${profileId}/documents/${documentId}/download`),
  getProfileDocumentFileUrl: vi.fn((profileId, documentId) => `/api/role-profiles/${profileId}/documents/${documentId}/file`),
  listProfileDocuments: vi.fn(),
  uploadProfileDocument: vi.fn(),
}));
```

Update `readyDocument`:

```ts
  document_kind: "cv",
  active_version_id: "version-1",
  is_active: true,
```

Add tests:

```ts
it("renders view download active and delete controls", async () => {
  vi.mocked(listProfileDocuments).mockResolvedValue([readyDocument]);

  render(<ProfileDocumentPanel activeProfileId="profile-1" />);

  await waitFor(() => {
    expect(screen.getByText("Active CV")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view cv.pdf/i })).toHaveAttribute(
      "href",
      "/api/role-profiles/profile-1/documents/doc-1/file"
    );
    expect(screen.getByRole("link", { name: /download cv.pdf/i })).toHaveAttribute(
      "href",
      "/api/role-profiles/profile-1/documents/doc-1/download"
    );
    expect(screen.getByRole("button", { name: /delete cv.pdf/i })).toBeInTheDocument();
  });
});

it("activates a non-active ready cv", async () => {
  const inactiveDocument = { ...readyDocument, is_active: false };
  vi.mocked(listProfileDocuments)
    .mockResolvedValueOnce([inactiveDocument])
    .mockResolvedValueOnce([{ ...inactiveDocument, is_active: true }]);
  vi.mocked(activateProfileDocumentVersion).mockResolvedValue({
    id: "version-1",
  } as never);

  render(<ProfileDocumentPanel activeProfileId="profile-1" />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /set cv.pdf active/i })).toBeInTheDocument();
  });
  fireEvent.click(screen.getByRole("button", { name: /set cv.pdf active/i }));

  await waitFor(() => {
    expect(activateProfileDocumentVersion).toHaveBeenCalledWith("profile-1", "doc-1", "version-1");
    expect(listProfileDocuments).toHaveBeenCalledTimes(2);
  });
});
```

- [x] **Step 2: Run UI tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/ProfileDocumentPanel.test.tsx
```

Expected: fail because controls are not rendered.

- [x] **Step 3: Update panel imports**

In `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`, import:

```ts
import { Download, Eye, Star, Trash2 } from "lucide-react";
import {
  activateProfileDocumentVersion,
  deleteProfileDocument,
  getProfileDocumentDownloadUrl,
  getProfileDocumentFileUrl,
  listProfileDocuments,
  uploadProfileDocument,
} from "../../api/profileDocumentsClient";
```

- [x] **Step 4: Add refresh helper and handlers**

Inside `ProfileDocumentPanel`, add:

```ts
  const refreshDocuments = async () => {
    if (!activeProfileId) return;
    setDocuments(await listProfileDocuments(activeProfileId));
  };
```

Update upload success:

```ts
      await uploadProfileDocument(activeProfileId, file);
      await refreshDocuments();
```

Add handlers:

```ts
  const handleActivate = async (document: ProfileDocument) => {
    if (!activeProfileId || !document.active_version_id) return;
    setError(null);
    try {
      await activateProfileDocumentVersion(activeProfileId, document.id, document.active_version_id);
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set active CV");
    }
  };

  const handleDelete = async (document: ProfileDocument) => {
    if (!activeProfileId) return;
    const clearActive = document.is_active;
    const confirmed = window.confirm(
      clearActive
        ? "Delete the active CV and clear active selection?"
        : "Delete this CV PDF?"
    );
    if (!confirmed) return;
    setError(null);
    try {
      await deleteProfileDocument(activeProfileId, document.id, { clearActive });
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete CV");
    }
  };
```

- [x] **Step 5: Render controls**

Inside each document row, below metadata, render:

```tsx
                  {document.is_active ? (
                    <span className="document-active-badge">Active CV</span>
                  ) : null}
                  <div className="profile-document-actions">
                    <a
                      href={getProfileDocumentFileUrl(activeProfileId, document.id)}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`View ${document.original_filename}`}
                    >
                      <Eye size={14} /> View
                    </a>
                    <a
                      href={getProfileDocumentDownloadUrl(activeProfileId, document.id)}
                      aria-label={`Download ${document.original_filename}`}
                    >
                      <Download size={14} /> Download
                    </a>
                    {!document.is_active && document.active_version_id ? (
                      <button
                        type="button"
                        onClick={() => void handleActivate(document)}
                        aria-label={`Set ${document.original_filename} active`}
                      >
                        <Star size={14} /> Set active
                      </button>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => void handleDelete(document)}
                      aria-label={`Delete ${document.original_filename}`}
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
```

Add these compact right-rail styles to `frontend/job-agent-ui/src/styles/app.css` near the existing `.profile-facts` and `.active-profile-meta` rules:

```css
.document-active-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  margin-top: 6px;
  padding: 2px 6px;
  border: 1px solid rgba(0, 231, 254, 0.25);
  border-radius: var(--radius-sm);
  color: var(--accent);
  background: var(--accent-muted);
  font-size: 11px;
  font-weight: 600;
}

.profile-document-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.profile-document-actions a,
.profile-document-actions button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: 12px;
  text-decoration: none;
  cursor: pointer;
}

.profile-document-actions a:hover,
.profile-document-actions button:hover {
  color: var(--text-primary);
  background: var(--bg-surface-hover);
}
```

- [x] **Step 6: Run panel tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/ProfileDocumentPanel.test.tsx
```

Expected: panel tests pass.

- [x] **Step 7: Commit Task 8**

```powershell
git add frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx frontend/job-agent-ui/src/styles/app.css frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx
git commit -m "feat(ui): manage active profile cv pdfs"
```

---

### Task 9: Final Phase 1 Verification And Safety Sweep

**Files:**
- Modify only if verification finds breakage.

- [x] **Step 1: Run backend verification**

Run:

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

- [x] **Step 2: Run frontend verification**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Expected:

- lint exits `0`; unchanged existing warnings are acceptable
- typecheck exits `0`
- tests pass
- build exits `0`

- [x] **Step 3: Run source-of-truth safety scan**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
rg -n "stored_path|content_hash|raw_text|OPENAI_API_KEY|api_key|safe_payload|FileResponse|Content-Disposition|active_cv" backend\app frontend\job-agent-ui\src
```

Expected:

- `stored_path` and `content_hash` appear only in backend models/services, not API response schemas or frontend types.
- file endpoints use `FileResponse`.
- download endpoints use attachment disposition.
- frontend does not receive storage paths.
- no API keys appear in frontend code or tool safe payloads.

- [x] **Step 4: Review final diff**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Expected:

- no whitespace errors
- only Phase 1 files changed
- no CV editing/export/OCR code added
- no runtime demo/mock data introduced

- [x] **Step 5: Commit verification cleanup if needed**

Only if Step 1-4 required cleanup edits:

```powershell
git add backend frontend
git commit -m "test: verify profile cv pdf foundation"
```

## Phase 1 Completion Criteria

Phase 1 is complete only when:

- uploaded PDFs are stored as real files
- upload creates an original version record
- first ready CV becomes active when the profile has no active CV
- View returns the real PDF with inline disposition
- Download returns the real PDF with attachment disposition
- active CV can be queried
- active CV version can be set only with confirmation
- deleting active CV without clear flag is rejected
- deleting inactive CV removes DB metadata, chunks, Qdrant points, and stored files
- frontend provides View, Download, Delete, and Set active controls
- full backend and frontend verification passes
