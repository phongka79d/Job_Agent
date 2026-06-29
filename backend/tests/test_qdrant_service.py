from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from qdrant_client import models as qmodels

from app.db.models import JobPost
from app.services.qdrant_service import (
    PAYLOAD_INDEX_FIELDS,
    QdrantService,
    build_job_scoring_filter,
    build_pending_review_filter,
)


class FakeQdrantClient:
    def __init__(self, *, collection_exists: bool = False, query_responses=None):
        self.collection_exists_result = collection_exists
        self.query_responses = list(query_responses or [])
        self.created_collections = []
        self.payload_indexes = []
        self.upserts = []
        self.queries = []
        self.deletes = []
        self.payload_updates = []

    async def collection_exists(self, collection_name: str, **kwargs: object) -> bool:
        return self.collection_exists_result

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: qmodels.VectorParams,
        **kwargs: object,
    ) -> object:
        self.created_collections.append((collection_name, vectors_config, kwargs))

    async def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_schema: qmodels.PayloadSchemaType,
        **kwargs: object,
    ) -> object:
        self.payload_indexes.append((collection_name, field_name, field_schema, kwargs))

    async def upsert(
        self,
        collection_name: str,
        points: list[qmodels.PointStruct],
        **kwargs: object,
    ) -> object:
        self.upserts.append((collection_name, points, kwargs))

    async def query_points(
        self,
        collection_name: str,
        query: list[float],
        **kwargs: object,
    ) -> object:
        self.queries.append((collection_name, query, kwargs))
        if self.query_responses:
            return self.query_responses.pop(0)
        return SimpleNamespace(points=[])

    async def delete(
        self,
        collection_name: str,
        points_selector: qmodels.PointIdsList,
        **kwargs: object,
    ) -> object:
        self.deletes.append((collection_name, points_selector, kwargs))

    async def set_payload(
        self,
        collection_name: str,
        payload: dict[str, str],
        points: list[str],
        **kwargs: object,
    ) -> object:
        self.payload_updates.append((collection_name, payload, points, kwargs))


def make_scorable_job() -> JobPost:
    job_id = str(uuid4())
    return JobPost(
        id=job_id,
        batch_id=str(uuid4()),
        role_profile_id=str(uuid4()),
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        level="junior",
        jd_status="full_jd",
        status="pending_review",
        source_platform="manual_text",
        should_score_similarity=True,
    )


def filter_values(query_filter: qmodels.Filter) -> dict[str, object]:
    values = {}
    for condition in query_filter.must or []:
        if isinstance(condition, qmodels.FieldCondition):
            values[condition.key] = condition.match.value
        elif isinstance(condition, qmodels.HasIdCondition):
            values["has_id"] = condition.has_id
    return values


@pytest.mark.asyncio
async def test_ensure_collection_creates_missing_collection_with_cosine_distance():
    client = FakeQdrantClient(collection_exists=False)
    service = QdrantService(client=client, vector_size=3)

    await service.ensure_collection()

    assert len(client.created_collections) == 1
    collection_name, vectors_config, kwargs = client.created_collections[0]
    assert collection_name == "job_posts"
    assert vectors_config.size == 3
    assert vectors_config.distance == qmodels.Distance.COSINE
    assert kwargs == {}


@pytest.mark.asyncio
async def test_ensure_collection_requests_payload_indexes_for_filter_fields():
    client = FakeQdrantClient(collection_exists=True)
    service = QdrantService(client=client, vector_size=3)

    await service.ensure_collection()

    assert [field for _, field, _, _ in client.payload_indexes] == list(
        PAYLOAD_INDEX_FIELDS
    )
    assert set(PAYLOAD_INDEX_FIELDS) == {
        "role_profile_id",
        "status",
        "jd_status",
        "batch_id",
        "source_platform",
    }
    assert all(
        field_schema == qmodels.PayloadSchemaType.KEYWORD
        for _, _, field_schema, _ in client.payload_indexes
    )
    assert all(kwargs == {"wait": True} for _, _, _, kwargs in client.payload_indexes)


@pytest.mark.asyncio
async def test_scorable_upsert_uses_canonical_uuid_point_id_and_waits_for_write():
    client = FakeQdrantClient()
    service = QdrantService(client=client, vector_size=3)
    job = make_scorable_job()

    upserted = await service.upsert_scorable_job(job, [1.0, 0.0, 0.0])

    assert upserted is True
    collection_name, points, kwargs = client.upserts[0]
    point = points[0]
    assert collection_name == "job_posts"
    assert str(UUID(str(point.id))) == job.id
    assert point.payload["job_id"] == job.id
    assert point.payload["role_profile_id"] == job.role_profile_id
    assert point.payload["status"] == "pending_review"
    assert kwargs == {"wait": True}


def test_pending_review_filter_includes_role_profile_and_status():
    role_profile_id = str(uuid4())

    values = filter_values(build_pending_review_filter(role_profile_id))

    assert values == {
        "role_profile_id": role_profile_id,
        "status": "pending_review",
    }


def test_job_specific_scoring_filter_includes_current_job_id():
    role_profile_id = str(uuid4())
    job_id = str(uuid4())

    values = filter_values(build_job_scoring_filter(role_profile_id, job_id))

    assert values["role_profile_id"] == role_profile_id
    assert values["status"] == "pending_review"
    assert values["job_id"] == job_id
    assert values["has_id"] == [job_id]


@pytest.mark.asyncio
async def test_query_job_similarity_uses_current_job_score_and_clamps():
    job_id = str(uuid4())
    other_job_id = str(uuid4())
    client = FakeQdrantClient(
        query_responses=[
            SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id=other_job_id,
                        payload={"job_id": other_job_id},
                        score=0.2,
                    ),
                    SimpleNamespace(id=job_id, payload={"job_id": job_id}, score=1.4),
                ]
            )
        ]
    )
    service = QdrantService(client=client, vector_size=3)

    score = await service.query_job_similarity(
        [1.0, 0.0, 0.0],
        str(uuid4()),
        job_id,
        attempts=1,
        retry_delay_seconds=0,
    )

    assert score == 1.0
    _, _, kwargs = client.queries[0]
    assert filter_values(kwargs["query_filter"])["job_id"] == job_id


@pytest.mark.asyncio
async def test_query_job_similarity_retries_and_does_not_borrow_other_job_score():
    job_id = str(uuid4())
    other_job_id = str(uuid4())
    client = FakeQdrantClient(
        query_responses=[
            SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id=other_job_id,
                        payload={"job_id": other_job_id},
                        score=0.99,
                    )
                ]
            ),
            SimpleNamespace(points=[]),
        ]
    )
    service = QdrantService(client=client, vector_size=3)

    score = await service.query_job_similarity(
        [1.0, 0.0, 0.0],
        str(uuid4()),
        job_id,
        attempts=2,
        retry_delay_seconds=0,
    )

    assert score is None
    assert len(client.queries) == 2
