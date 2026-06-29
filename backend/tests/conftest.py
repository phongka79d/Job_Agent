import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, JobPost, RoleProfile


class FakeEmbeddingService:
    def __init__(self, db_session: AsyncSession | None = None, fail: bool = False):
        self.calls: list[str] = []
        self.db_session = db_session
        self.fail = fail
        self.row_count_at_first_call: int | None = None

    async def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.db_session and self.row_count_at_first_call is None:
            result = await self.db_session.execute(select(JobPost))
            self.row_count_at_first_call = len(result.scalars().all())
        if self.fail:
            raise RuntimeError("fake provider failure with no secrets")
        return [1.0, 0.0, 0.0]


class FakeQdrantService:
    def __init__(self, similarity: float | None = 0.8, db_session: AsyncSession | None = None):
        self.similarity = similarity
        self.db_session = db_session
        self.row_count_at_first_upsert: int | None = None
        self.upserted_job_ids: list[str] = []
        self.queried_job_ids: list[str] = []
        self.status_payload_updates: list[tuple[str, str]] = []
        self.deleted_job_ids: list[str] = []

    async def upsert_scorable_job(self, job: JobPost, vector: list[float]) -> bool:
        self.upserted_job_ids.append(job.id)
        if self.db_session and self.row_count_at_first_upsert is None:
            result = await self.db_session.execute(select(JobPost))
            self.row_count_at_first_upsert = len(result.scalars().all())
        assert job.status == "pending_review"
        return True

    async def query_job_similarity(
        self,
        query_vector: list[float],
        role_profile_id: str,
        job_id: str,
    ) -> float | None:
        self.queried_job_ids.append(job_id)
        return self.similarity

    async def update_job_status_payload(self, job_id: str, status: str) -> None:
        self.status_payload_updates.append((job_id, status))

    async def delete_point_if_exists(self, job_id: str) -> None:
        self.deleted_job_ids.append(job_id)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_role_profile(db_session: AsyncSession):
    profile = RoleProfile(
        id="rp-test-id",
        target_role="Software Engineer",
        level="junior",
        location="San Francisco",
        accept_remote=True,
        skills='["python", "fastapi"]',
        resume_text="Experienced developer",
    )
    db_session.add(profile)
    await db_session.commit()
    return profile
