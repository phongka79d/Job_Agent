"""Qdrant collection, payload, filter, and point operation service."""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol, Sequence
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models as qmodels

from app.core.config import settings
from app.core.constants import JOB_STATUSES
from app.db.models import JobPost
from app.services.scoring_service import clamp_score

logger = logging.getLogger(__name__)

COLLECTION_NAME = "job_posts"
PROFILE_DOCUMENT_COLLECTION_NAME = "profile_documents"
PAYLOAD_INDEX_FIELDS = (
    "role_profile_id",
    "status",
    "jd_status",
    "batch_id",
    "source_platform",
)
PROFILE_DOCUMENT_PAYLOAD_INDEX_FIELDS = (
    "role_profile_id",
    "document_id",
    "source_type",
)
SCORABLE_JD_STATUSES = ("full_jd", "partial_jd")
PENDING_REVIEW_STATUS = "pending_review"
SAVED_STATUS = "saved"


class QdrantServiceError(Exception):
    """Raised when a Qdrant operation fails at the service boundary."""


class QdrantClientProtocol(Protocol):
    """Subset of AsyncQdrantClient methods used by QdrantService."""

    async def collection_exists(self, collection_name: str, **kwargs: object) -> bool:
        ...

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: qmodels.VectorParams,
        **kwargs: object,
    ) -> object:
        ...

    async def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_schema: qmodels.PayloadSchemaType,
        **kwargs: object,
    ) -> object:
        ...

    async def upsert(
        self,
        collection_name: str,
        points: Sequence[qmodels.PointStruct],
        **kwargs: object,
    ) -> object:
        ...

    async def query_points(
        self,
        collection_name: str,
        query: Sequence[float],
        **kwargs: object,
    ) -> object:
        ...

    async def delete(
        self,
        collection_name: str,
        points_selector: qmodels.PointIdsList,
        **kwargs: object,
    ) -> object:
        ...

    async def set_payload(
        self,
        collection_name: str,
        payload: dict[str, str],
        points: Sequence[str],
        **kwargs: object,
    ) -> object:
        ...


def canonical_uuid(value: str) -> str:
    """Validate and return the canonical UUID string used as Qdrant point ID."""
    return str(UUID(str(value)))


def build_job_payload(job: JobPost) -> dict[str, str | None]:
    """Build the approved lightweight Qdrant payload for a JobPost row."""
    return {
        "job_id": canonical_uuid(job.id),
        "role_profile_id": job.role_profile_id,
        "batch_id": job.batch_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "level": job.level,
        "jd_status": job.jd_status,
        "status": job.status,
        "source_platform": job.source_platform,
    }


def build_profile_document_payload(
    *,
    role_profile_id: str,
    document_id: str,
    chunk_id: str,
    chunk_index: int,
) -> dict[str, str | int]:
    """Build the approved lightweight Qdrant payload for profile PDF chunks."""
    return {
        "role_profile_id": role_profile_id,
        "document_id": document_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "source_type": "profile_document",
    }


def build_status_filter(role_profile_id: str, status: str) -> qmodels.Filter:
    """Build a role-profile/status isolation filter."""
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="role_profile_id",
                match=qmodels.MatchValue(value=role_profile_id),
            ),
            qmodels.FieldCondition(
                key="status",
                match=qmodels.MatchValue(value=status),
            ),
        ]
    )


def build_pending_review_filter(role_profile_id: str) -> qmodels.Filter:
    """Build the pending-review query isolation filter."""
    return build_status_filter(role_profile_id, PENDING_REVIEW_STATUS)


def build_saved_jobs_filter(role_profile_id: str) -> qmodels.Filter:
    """Build the saved-job query isolation filter."""
    return build_status_filter(role_profile_id, SAVED_STATUS)


def build_job_scoring_filter(role_profile_id: str, job_id: str) -> qmodels.Filter:
    """Build the current-job-only similarity scoring filter."""
    return qmodels.Filter(
        must=[
            *build_pending_review_filter(role_profile_id).must,
            qmodels.FieldCondition(
                key="job_id",
                match=qmodels.MatchValue(value=canonical_uuid(job_id)),
            ),
            qmodels.HasIdCondition(has_id=[canonical_uuid(job_id)]),
        ]
    )


def is_scorable_job(job: JobPost) -> bool:
    """Return whether a persisted job row is eligible for Qdrant scoring."""
    return (
        bool(job.should_score_similarity)
        and job.jd_status in SCORABLE_JD_STATUSES
        and job.status == PENDING_REVIEW_STATUS
    )


class QdrantService:
    """Owns Qdrant collection setup and point operations for job posts."""

    def __init__(
        self,
        client: QdrantClientProtocol | None = None,
        collection_name: str = COLLECTION_NAME,
        vector_size: int | None = None,
    ) -> None:
        self._client = client
        self.collection_name = collection_name
        self.vector_size = vector_size or settings.EMBEDDING_DIMENSION

    @property
    def client(self) -> QdrantClientProtocol:
        """Return a lazily configured Qdrant client."""
        if self._client is None:
            api_key = (
                settings.QDRANT_API_KEY.get_secret_value()
                if settings.QDRANT_API_KEY
                else None
            )
            self._client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=api_key or None,
            )
        return self._client

    async def ensure_collection(self) -> None:
        """Idempotently create the job_posts collection and payload indexes."""
        try:
            exists = await self.client.collection_exists(self.collection_name)
            if not exists:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            await self.ensure_payload_indexes()
        except Exception as exc:
            self._log_qdrant_error("ensure_collection", exc)
            raise QdrantServiceError("Qdrant collection initialization failed") from exc

    async def ensure_profile_document_collection(self) -> None:
        """Idempotently create the profile_documents collection and payload indexes."""
        try:
            exists = await self.client.collection_exists(PROFILE_DOCUMENT_COLLECTION_NAME)
            if not exists:
                await self.client.create_collection(
                    collection_name=PROFILE_DOCUMENT_COLLECTION_NAME,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            for field_name in PROFILE_DOCUMENT_PAYLOAD_INDEX_FIELDS:
                await self.client.create_payload_index(
                    collection_name=PROFILE_DOCUMENT_COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
        except Exception as exc:
            self._log_qdrant_error("ensure_profile_document_collection", exc)
            raise QdrantServiceError(
                "Qdrant profile document collection initialization failed"
            ) from exc

    async def ensure_payload_indexes(self) -> None:
        """Idempotently create approved keyword payload indexes."""
        try:
            for field_name in PAYLOAD_INDEX_FIELDS:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
        except Exception as exc:
            self._log_qdrant_error("ensure_payload_indexes", exc)
            raise QdrantServiceError("Qdrant payload index initialization failed") from exc

    async def upsert_scorable_job(
        self,
        job: JobPost,
        vector: Sequence[float],
    ) -> bool:
        """Upsert a scorable job point with write acknowledgement."""
        if not is_scorable_job(job):
            return False

        try:
            point = qmodels.PointStruct(
                id=canonical_uuid(job.id),
                vector=self._validate_vector(vector),
                payload=build_job_payload(job),
            )
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=True,
            )
            return True
        except Exception as exc:
            self._log_qdrant_error("upsert_scorable_job", exc)
            raise QdrantServiceError("Qdrant upsert failed") from exc

    async def upsert_profile_document_chunk(
        self,
        *,
        point_id: str,
        role_profile_id: str,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
        vector: Sequence[float],
    ) -> None:
        """Upsert one embedded profile document chunk into Qdrant."""
        try:
            point = qmodels.PointStruct(
                id=canonical_uuid(point_id),
                vector=self._validate_vector(vector),
                payload=build_profile_document_payload(
                    role_profile_id=role_profile_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                ),
            )
            await self.client.upsert(
                collection_name=PROFILE_DOCUMENT_COLLECTION_NAME,
                points=[point],
                wait=True,
            )
        except Exception as exc:
            self._log_qdrant_error("upsert_profile_document_chunk", exc)
            raise QdrantServiceError("Qdrant profile document upsert failed") from exc

    async def query_job_similarity(
        self,
        query_vector: Sequence[float],
        role_profile_id: str,
        job_id: str,
        attempts: int = 3,
        retry_delay_seconds: float = 0.1,
    ) -> float | None:
        """Query Qdrant for the current job only and return a clamped score."""
        point_id = canonical_uuid(job_id)
        query_filter = build_job_scoring_filter(role_profile_id, point_id)
        vector = self._validate_vector(query_vector)

        try:
            for attempt in range(1, attempts + 1):
                response = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    query_filter=query_filter,
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )
                score = self._extract_current_job_score(response, point_id)
                if score is not None:
                    return clamp_score(score)
                if attempt < attempts:
                    await asyncio.sleep(retry_delay_seconds)
            return None
        except Exception as exc:
            self._log_qdrant_error("query_job_similarity", exc)
            raise QdrantServiceError("Qdrant similarity query failed") from exc

    async def delete_point_if_exists(self, job_id: str) -> None:
        """Idempotently delete a Qdrant point by canonical job ID."""
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.PointIdsList(points=[canonical_uuid(job_id)]),
                wait=True,
            )
        except Exception as exc:
            self._log_qdrant_error("delete_point_if_exists", exc)
            raise QdrantServiceError("Qdrant point delete failed") from exc

    async def update_job_status_payload(self, job_id: str, status: str) -> None:
        """Idempotently update a job point's status payload field."""
        if status not in JOB_STATUSES:
            raise ValueError(f"Invalid job status for Qdrant payload: {status}")
        await self.update_payload_fields(job_id, {"status": status})

    async def update_payload_fields(self, job_id: str, payload: dict[str, str]) -> None:
        """Idempotently update selected payload fields for a job point."""
        try:
            await self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=[canonical_uuid(job_id)],
                wait=True,
            )
        except Exception as exc:
            self._log_qdrant_error("update_payload_fields", exc)
            raise QdrantServiceError("Qdrant payload update failed") from exc

    def _validate_vector(self, vector: Sequence[float]) -> list[float]:
        values = [float(value) for value in vector]
        if len(values) != self.vector_size:
            raise ValueError(
                f"Qdrant vector dimension mismatch: expected {self.vector_size}, got {len(values)}."
            )
        return values

    @staticmethod
    def _extract_current_job_score(response: object, job_id: str) -> float | None:
        points = getattr(response, "points", response)
        if points is None:
            return None

        for point in points:
            point_id = str(getattr(point, "id", ""))
            payload = getattr(point, "payload", {}) or {}
            payload_job_id = payload.get("job_id") if isinstance(payload, dict) else None
            if point_id == job_id or payload_job_id == job_id:
                score = getattr(point, "score", None)
                return float(score) if score is not None else None
        return None

    @staticmethod
    def _log_qdrant_error(operation: str, exc: Exception) -> None:
        logger.warning(
            "Qdrant operation failed",
            extra={
                "operation": operation,
                "error_type": exc.__class__.__name__,
            },
        )


async def ensure_collection() -> None:
    """Initialize default Qdrant collections for app startup."""
    service = QdrantService()
    await service.ensure_collection()
    await service.ensure_profile_document_collection()
