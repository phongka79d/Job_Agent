"""Idempotent SQLite schema migrations for local persisted databases."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def _column_names(conn: AsyncConnection, table_name: str) -> set[str]:
    rows = (await conn.execute(text(f"PRAGMA table_info({table_name})"))).mappings().all()
    return {str(row["name"]) for row in rows}


async def _add_column_if_missing(
    conn: AsyncConnection,
    table_name: str,
    column_name: str,
    ddl: str,
) -> None:
    columns = await _column_names(conn, table_name)
    if column_name in columns:
        return
    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


async def apply_sqlite_migrations(conn: AsyncConnection) -> None:
    if conn.dialect.name != "sqlite":
        return

    await _add_column_if_missing(
        conn,
        "role_profiles",
        "active_cv_document_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "role_profiles",
        "active_cv_version_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "profile_documents",
        "document_kind",
        "TEXT NOT NULL DEFAULT 'cv'",
    )
    await _add_column_if_missing(
        conn,
        "profile_documents",
        "active_version_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "profile_document_chunks",
        "version_id",
        "VARCHAR(36)",
    )
    await _add_column_if_missing(
        conn,
        "profile_document_chunks",
        "source_type",
        "TEXT NOT NULL DEFAULT 'profile_cv'",
    )
