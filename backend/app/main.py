import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_batches import router as batches_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_role_profiles import router as role_profiles_router
from app.core.logging import setup_logging
from app.db.session import init_db
from app.services.qdrant_service import ensure_collection


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Initializing application database")
    await init_db()
    logger.info("Application database initialization complete")
    logger.info("Initializing Qdrant collection")
    await ensure_collection()
    logger.info("Qdrant collection initialization complete")
    yield


app = FastAPI(
    title="Agentic Job Matching System",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(role_profiles_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(batches_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
