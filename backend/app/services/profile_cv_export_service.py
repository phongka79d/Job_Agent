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
from app.services.latex_cv_render_service import LatexCvRenderService
from app.services.profile_cv_template_service import ProfileCvTemplateService
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
        template_service: ProfileCvTemplateService | None = None,
        latex_renderer: LatexCvRenderService | None = None,
    ) -> None:
        self.pdf_exporter = pdf_exporter or CvPdfExportService()
        self.storage = storage or ProfileDocumentStorageService()
        self.extractor = extractor or PdfTextExtractionService()
        self.structure_extractor = structure_extractor or CvStructureExtractionService()
        self.indexing_service = indexing_service or ProfileDocumentIndexingService()
        self.template_service = template_service or ProfileCvTemplateService()
        self.latex_renderer = latex_renderer or LatexCvRenderService()

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
            template = await self.template_service.get_active_template(
                session,
                role_profile_id=request.role_profile_id,
            )
            if template is None:
                self.pdf_exporter.write_pdf(rendered_path, preview)
            else:
                self.latex_renderer.write_pdf(
                    rendered_path,
                    template_source=template.template_source,
                    preview=preview,
                )
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
