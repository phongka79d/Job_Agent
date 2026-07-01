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


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    row = (
        await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        )
    ).first()
    return row is not None


async def _create_table_if_missing(
    conn: AsyncConnection,
    table_name: str,
    ddl: str,
) -> None:
    if await _table_exists(conn, table_name):
        return
    await conn.execute(text(ddl))


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
    await _create_table_if_missing(
        conn,
        "profile_cv_drafts",
        """
        CREATE TABLE profile_cv_drafts (
            id VARCHAR(36) PRIMARY KEY,
            role_profile_id VARCHAR(36) NOT NULL,
            document_id VARCHAR(36) NOT NULL,
            base_version_id VARCHAR(36) NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            title TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            edit_plan_json TEXT NOT NULL,
            structure_status_at_creation TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'ai',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """,
    )
    await _create_table_if_missing(
        conn,
        "profile_cv_improvement_suggestions",
        """
        CREATE TABLE profile_cv_improvement_suggestions (
            id VARCHAR(36) PRIMARY KEY,
            role_profile_id VARCHAR(36) NOT NULL,
            document_id VARCHAR(36) NOT NULL,
            version_id VARCHAR(36) NOT NULL,
            job_id VARCHAR(36),
            requirement TEXT NOT NULL,
            current_cv_evidence TEXT NOT NULL,
            missing_or_weak_evidence TEXT NOT NULL,
            proposed_edit TEXT NOT NULL,
            edit_kind TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            requires_confirmation BOOLEAN NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'suggested',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """,
    )
