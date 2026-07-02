import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def _columns(conn, table_name: str) -> set[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table_name})"))).mappings().all()
    return {str(row["name"]) for row in rows}


async def _table_names(conn):
    rows = (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))).all()
    return {row[0] for row in rows}


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


@pytest.mark.asyncio
async def test_sqlite_migration_adds_draft_and_suggestion_tables():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_versions (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)

        tables = await _table_names(conn)
        draft_columns = await _columns(conn, "profile_cv_drafts")
        suggestion_columns = await _columns(conn, "profile_cv_improvement_suggestions")

    assert "profile_cv_drafts" in tables
    assert "profile_cv_improvement_suggestions" in tables
    assert {
        "id",
        "role_profile_id",
        "document_id",
        "base_version_id",
        "status",
        "title",
        "structure_json",
        "edit_plan_json",
        "structure_status_at_creation",
        "created_by",
        "created_at",
        "updated_at",
    } <= draft_columns
    assert {
        "id",
        "role_profile_id",
        "document_id",
        "version_id",
        "job_id",
        "requirement",
        "current_cv_evidence",
        "missing_or_weak_evidence",
        "proposed_edit",
        "edit_kind",
        "risk_level",
        "requires_confirmation",
        "status",
        "created_at",
        "updated_at",
    } <= suggestion_columns
    await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_draft_migration_is_idempotent():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_versions (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)
        await apply_sqlite_migrations(conn)

        tables = await _table_names(conn)

    assert "profile_cv_drafts" in tables
    assert "profile_cv_improvement_suggestions" in tables
    await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_migration_adds_profile_cv_templates_table():
    from app.db.sqlite_migrations import apply_sqlite_migrations

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE role_profiles (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_documents (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_chunks (id VARCHAR(36) PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE profile_document_versions (id VARCHAR(36) PRIMARY KEY)"))

        await apply_sqlite_migrations(conn)

        tables = await _table_names(conn)
        columns = await _columns(conn, "profile_cv_templates")

    assert "profile_cv_templates" in tables
    assert {
        "id",
        "role_profile_id",
        "name",
        "template_format",
        "template_source",
        "is_active",
        "created_at",
        "updated_at",
    } <= columns
    await engine.dispose()
