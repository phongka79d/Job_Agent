"""
Async database session configuration, connection pragmas, and initialization utilities.

This module establishes the SQLAlchemy async engine and session maker for SQLite via
aiosqlite. It configures startup SQLite PRAGMAs (foreign keys and WAL mode) via
event listeners, and provides a database initialization function with safety guards
to ensure only the three MVP tables are created.
"""

from pathlib import Path
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.db.models import Base

# 6. Add a local data directory creation guard if needed for backend/data/job_matching.db
if settings.DATABASE_URL.startswith("sqlite"):
    db_path = Path(settings.SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

# 1. Create async engine using settings.DATABASE_URL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# 3 & 4. Add connection event handling so SQLite foreign keys and WAL mode are enabled
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

# 2. Create async session maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 5. Implement init_db() that creates metadata for exactly the three MVP models
async def init_db() -> None:
    """
    Initialize the database, creating the schema for exactly the three MVP models.
    
    Guards against creating any out-of-scope tables and verifies table names before creation.
    """
    # 7. Verify metadata table names are exactly 'applications', 'job_posts', and 'role_profiles'
    expected_tables = {"applications", "job_posts", "role_profiles"}
    metadata_tables = set(Base.metadata.tables.keys())
    
    if metadata_tables != expected_tables:
        raise ValueError(
            f"Database metadata verification failed.\n"
            f"Expected table set: {expected_tables}\n"
            f"Metadata table set: {metadata_tables}"
        )
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
