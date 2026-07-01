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
            chunks = await self._chunks_by_ids(
                session,
                chunk_ids,
                role_profile_id=role_profile_id,
                document_id=document.id,
                version_id=version.id,
            )
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
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
    ) -> list[ProfileDocumentChunk]:
        if not chunk_ids:
            return []
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.id.in_(chunk_ids))
            .where(ProfileDocumentChunk.role_profile_id == role_profile_id)
            .where(ProfileDocumentChunk.document_id == document_id)
            .where(ProfileDocumentChunk.version_id == version_id)
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
