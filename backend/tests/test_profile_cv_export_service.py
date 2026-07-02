from __future__ import annotations

from pathlib import Path

import pytest

from app.db.models import (
    ProfileCvDraft,
    ProfileCvTemplate,
    ProfileDocument,
    ProfileDocumentVersion,
    RoleProfile,
)
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


class FakeLatexRenderer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def write_pdf(self, output_path: Path, *, template_source: str, preview: dict[str, object]) -> Path:
        self.calls.append({"template_source": template_source, "preview": preview})
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-latex-template")
        return output_path


@pytest.mark.asyncio
async def test_export_draft_creates_exported_version_without_activating(db_session, tmp_path: Path) -> None:
    profile = RoleProfile(id="profile-1", target_role="AI Engineer")
    db_session.add(profile)
    await db_session.commit()
    document = ProfileDocument(
        id="doc-1",
        role_profile_id="profile-1",
        original_filename="cv.pdf",
        stored_path=str(tmp_path / "original.pdf"),
        content_hash="original",
        mime_type="application/pdf",
        file_size_bytes=100,
        document_kind="cv",
        active_version_id=None,
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
    document.active_version_id = "version-1"
    db_session.add_all([document, version])
    await db_session.flush()
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
    db_session.add(draft)
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
async def test_export_draft_uses_active_latex_template_when_available(db_session, tmp_path: Path) -> None:
    profile = RoleProfile(id="profile-1", target_role="AI Engineer")
    db_session.add(profile)
    await db_session.commit()
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
    template = ProfileCvTemplate(
        id="template-1",
        role_profile_id="profile-1",
        name="Harvard style",
        template_format="latex",
        template_source="\\documentclass{article}\\begin{document}{{AI_TARGETED_EDITS}}\\end{document}",
        is_active=True,
    )
    db_session.add_all([document, version])
    await db_session.flush()
    db_session.add_all([draft, template])
    await db_session.commit()

    renderer = FakeLatexRenderer()
    service = ProfileCvExportService(
        latex_renderer=renderer,
        storage=ProfileDocumentStorageService(root_dir=tmp_path / "storage"),
        extractor=FakeExtractor(),
        structure_extractor=FakeStructureExtractor(),
        indexing_service=FakeIndexer(),
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
    assert renderer.calls[0]["template_source"] == template.template_source
    assert Path(exported.stored_path).read_bytes() == b"%PDF-latex-template"


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
    profile = RoleProfile(id="profile-1", target_role="AI Engineer")
    document = ProfileDocument(
        id="doc-2",
        role_profile_id="profile-1",
        original_filename="cv.pdf",
        stored_path="stored.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=100,
        document_kind="cv",
        status="ready",
    )
    version = ProfileDocumentVersion(
        id="version-1",
        document_id="doc-2",
        role_profile_id="profile-1",
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path="stored.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=100,
        extraction_status="ready",
        structure_status="reliable",
        created_by="user",
    )
    db_session.add(profile)
    await db_session.flush()
    db_session.add_all([document, version])
    await db_session.flush()
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
