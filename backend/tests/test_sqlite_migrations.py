import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _columns(conn, table_name: str) -> set[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table_name})"))).mappings().all()
    return {str(row["name"]) for row in rows}


@pytest.mark.asyncio
async def test_sqlite_migration_adds_profile_cv_columns():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)

        role_profile_columns = await _columns(conn, "role_profiles")
        document_columns = await _columns(conn, "profile_documents")
        chunk_columns = await _columns(conn, "profile_document_chunks")

    assert {"active_cv_document_id", "active_cv_version_id"} <= role_profile_columns
    assert {"document_kind", "active_version_id"} <= document_columns
    assert {"version_id", "source_type"} <= chunk_columns
    await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_migration_is_idempotent():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)
        await apply_sqlite_migrations(conn)

        role_profile_columns = await _columns(conn, "role_profiles")

    assert "active_cv_document_id" in role_profile_columns
    await engine.dispose()
