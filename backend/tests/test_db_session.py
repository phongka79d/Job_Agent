import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import session as db_session_module
from app.db.models import Base


@pytest.mark.asyncio
async def test_init_db_accepts_current_metadata_tables(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    monkeypatch.setattr(db_session_module, "engine", engine)

    try:
        await db_session_module.init_db()
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
            created_tables = set(result.scalars())
    finally:
        await engine.dispose()

    assert created_tables == set(Base.metadata.tables)
