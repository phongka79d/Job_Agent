"""Profile PDF upload, extraction, chunking, embedding, and metadata persistence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion, RoleProfile
from app.services.profile_document_storage_service import ProfileDocumentStorageService
from app.services.embedding_service import EmbeddingService
from app.services.pdf_text_extraction_service import (
    PdfTextExtractionError,
    PdfTextExtractionService,
)
from app.services.qdrant_service import QdrantService
from app.services.token_budget_service import SimpleTokenCounter


MAX_PROFILE_PDF_BYTES = 10 * 1024 * 1024


class TextExtractor(Protocol):
    def extract_text(self, path: Path) -> str:
        ...


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

    async def delete_profile_document_points(self, *, document_id: str) -> None:
        ...


@dataclass(frozen=True)
class ProfileDocumentFileInfo:
    path: Path
    media_type: str
    inline_filename: str
    download_filename: str


class ProfileDocumentService:
    def __init__(
        self,
        *,
        extractor: TextExtractor | None = None,
        token_counter: SimpleTokenCounter | None = None,
        embedder: TextEmbedder | None = None,
        vector_store: ProfileDocumentVectorStore | None = None,
        storage: ProfileDocumentStorageService | None = None,
    ) -> None:
        self.extractor = extractor or PdfTextExtractionService()
        self.token_counter = token_counter or SimpleTokenCounter()
        self.embedder = embedder or EmbeddingService()
        self.vector_store = vector_store or QdrantService()
        self.storage = storage or ProfileDocumentStorageService()

    async def list_documents(
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

    async def create_document_from_pdf(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        source_path: Path,
        original_filename: str,
        mime_type: str,
    ) -> ProfileDocument:
        self._validate_upload(source_path, original_filename, mime_type)
        size = source_path.stat().st_size
        content_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        document_id = str(uuid4())
        version_id = str(uuid4())
        stored_path = self.storage.copy_pdf(
            source_path,
            role_profile_id=role_profile_id,
            document_id=document_id,
            version_id=version_id,
            directory_name="original",
        )
        document = ProfileDocument(
            id=document_id,
            role_profile_id=role_profile_id,
            original_filename=original_filename,
            stored_path=str(stored_path),
            content_hash=content_hash,
            mime_type=mime_type,
            file_size_bytes=size,
            document_kind="cv",
            status="processing",
        )
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
        session.add(document)
        session.add(version)
        await session.commit()
        await session.refresh(document)

        try:
            text = self.extractor.extract_text(stored_path)
            chunks = self._chunk_text(text)
            if not chunks:
                raise ValueError("PDF does not contain enough extractable text")
            for index, chunk_text in enumerate(chunks):
                chunk_id = str(uuid4())
                chunk = ProfileDocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    role_profile_id=role_profile_id,
                    version_id=version.id,
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
                    document_id=document.id,
                    chunk_id=chunk_id,
                    chunk_index=index,
                    vector=vector,
                )
                session.add(chunk)
            document.extracted_text_chars = len(text)
            document.chunk_count = len(chunks)
            version.extracted_text_chars = len(text)
            version.chunk_count = len(chunks)
            version.extraction_status = "ready"
            version.error_reason = None
            document.status = "ready"
            document.error_reason = None
            profile = await session.get(RoleProfile, role_profile_id)
            if profile and profile.active_cv_version_id is None:
                profile.active_cv_document_id = document.id
                profile.active_cv_version_id = version.id
            await session.commit()
            await session.refresh(document)
            return document
        except (PdfTextExtractionError, ValueError) as exc:
            await self._mark_failed(session, document, str(exc), version)
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            await self._mark_failed(session, document, "Profile document indexing failed", version)
            raise RuntimeError("Profile document indexing failed") from exc

    @staticmethod
    def _validate_upload(source_path: Path, original_filename: str, mime_type: str) -> None:
        if mime_type != "application/pdf" or not original_filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF uploads are supported")
        size = source_path.stat().st_size
        if size <= 0 or size > MAX_PROFILE_PDF_BYTES:
            raise ValueError("PDF file size is outside the allowed range")

    def _chunk_text(
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

    @staticmethod
    async def _mark_failed(
        session: AsyncSession,
        document: ProfileDocument,
        reason: str,
        version: ProfileDocumentVersion | None = None,
    ) -> None:
        document.status = "failed"
        document.error_reason = reason[:500]
        if version is not None:
            version.extraction_status = "failed"
            version.error_reason = reason[:500]
        await session.commit()
        await session.refresh(document)

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
        await self.vector_store.delete_profile_document_points(document_id=document.id)
        await session.delete(document)
        await session.commit()
        self.storage.delete_document_files(role_profile_id=role_profile_id, document_id=document_id)
