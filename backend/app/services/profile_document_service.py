"""Profile PDF upload, extraction, chunking, embedding, and metadata persistence."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ProfileDocument, ProfileDocumentChunk
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
        chunk_id: str,
        chunk_index: int,
        vector: list[float],
    ) -> None:
        ...


class ProfileDocumentService:
    def __init__(
        self,
        *,
        extractor: TextExtractor | None = None,
        token_counter: SimpleTokenCounter | None = None,
        embedder: TextEmbedder | None = None,
        vector_store: ProfileDocumentVectorStore | None = None,
    ) -> None:
        self.extractor = extractor or PdfTextExtractionService()
        self.token_counter = token_counter or SimpleTokenCounter()
        self.embedder = embedder or EmbeddingService()
        self.vector_store = vector_store or QdrantService()

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
        stored_path = self._copy_to_storage(
            source_path,
            role_profile_id=role_profile_id,
            document_id=document_id,
        )
        document = ProfileDocument(
            id=document_id,
            role_profile_id=role_profile_id,
            original_filename=original_filename,
            stored_path=str(stored_path),
            content_hash=content_hash,
            mime_type=mime_type,
            file_size_bytes=size,
            status="processing",
        )
        session.add(document)
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
            document.status = "ready"
            document.error_reason = None
            await session.commit()
            await session.refresh(document)
            return document
        except (PdfTextExtractionError, ValueError) as exc:
            await self._mark_failed(session, document, str(exc))
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            await self._mark_failed(session, document, "Profile document indexing failed")
            raise RuntimeError("Profile document indexing failed") from exc

    @staticmethod
    def _validate_upload(source_path: Path, original_filename: str, mime_type: str) -> None:
        if mime_type != "application/pdf" or not original_filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF uploads are supported")
        size = source_path.stat().st_size
        if size <= 0 or size > MAX_PROFILE_PDF_BYTES:
            raise ValueError("PDF file size is outside the allowed range")

    @staticmethod
    def _copy_to_storage(
        source_path: Path,
        *,
        role_profile_id: str,
        document_id: str,
    ) -> Path:
        storage_dir = (
            Path(settings.SQLITE_DB_PATH).resolve().parent
            / "uploads"
            / "profile_documents"
            / role_profile_id
        )
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_path = storage_dir / f"{document_id}.pdf"
        shutil.copyfile(source_path, stored_path)
        return stored_path

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
    ) -> None:
        document.status = "failed"
        document.error_reason = reason[:500]
        await session.commit()
        await session.refresh(document)
