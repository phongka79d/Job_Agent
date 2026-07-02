"""
Async database session configuration, connection pragmas, and initialization utilities.

This module establishes the SQLAlchemy async engine and session maker for SQLite via
aiosqlite. It configures startup SQLite PRAGMAs (foreign keys and WAL mode) via
event listeners, and provides a database initialization function with safety guards
to ensure only the persisted application tables are created.
"""

from pathlib import Path
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.db.models import Base
from app.db.sqlite_migrations import apply_sqlite_migrations

if settings.DATABASE_URL.startswith("sqlite"):
    db_path = Path(settings.SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configure SQLite connection pragmas for foreign keys and WAL journal mode.
    
    This hook runs synchronously on the underlying DBAPI connection when a connection is made.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Initialize the database, creating the schema for persisted application models.
    
    Guards against creating any out-of-scope tables and verifies table names before creation.
    """
    expected_tables = {
        "agent_tool_calls",
        "applications",
        "chat_conversations",
        "chat_messages",
        "job_posts",
        "memory_summaries",
        "profile_cv_drafts",
        "profile_cv_improvement_suggestions",
        "profile_cv_templates",
        "profile_document_chunks",
        "profile_document_versions",
        "profile_documents",
        "role_profiles",
    }
    metadata_tables = set(Base.metadata.tables.keys())
    
    if metadata_tables != expected_tables:
        raise ValueError(
            f"Database metadata verification failed.\n"
            f"Expected table set: {expected_tables}\n"
            f"Metadata table set: {metadata_tables}"
        )
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await apply_sqlite_migrations(conn)
