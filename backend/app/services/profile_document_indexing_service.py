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
