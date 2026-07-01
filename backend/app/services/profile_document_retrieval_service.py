"""Profile document retrieval service for chat memory and tools."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfileDocumentChunk


class ProfileDocumentRetrievalService:
    async def retrieve(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        query: str,
        limit: int = 5,
    ) -> list[ProfileDocumentChunk]:
        terms = [term.lower() for term in query.split() if len(term) >= 3]
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.role_profile_id == role_profile_id)
            .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
            .limit(100)
        )
        chunks = list(result.scalars())
        if not terms:
            return chunks[:limit]

        def score(chunk: ProfileDocumentChunk) -> int:
            text = chunk.text.lower()
            return sum(1 for term in terms if term in text)

        ranked = sorted(chunks, key=score, reverse=True)
        return [chunk for chunk in ranked if score(chunk) > 0][:limit]
