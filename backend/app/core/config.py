from pathlib import Path
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """
    Application settings for the Agentic Job Matching System backend.
    Loads values from the root .env file, falling back to sensible defaults.
    """
    ENV: str = Field(default="development", description="Deployment environment")
    BACKEND_PORT: int = Field(default=8000, description="Backend API port")
    FRONTEND_PORT: int = Field(default=5173, description="Frontend development server port")

    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/job_matching.db",
        description="SQLAlchemy database connection string"
    )
    SQLITE_DB_PATH: str = Field(
        default="./data/job_matching.db",
        description="Path to the SQLite database file"
    )

    QDRANT_URL: str = Field(default="http://localhost:6333", description="Qdrant API URL")
    QDRANT_API_KEY: Optional[SecretStr] = Field(default=None, description="Qdrant API Key")

    OPENAI_API_KEY: SecretStr = Field(
        default=SecretStr("your-openai-api-key"),
        description="OpenAI API key for LLM and embedding operations"
    )
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI chat model name")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model name"
    )
    OPENAI_BASE_URL: Optional[str] = Field(
        default=None,
        description="Optional shared OpenAI-compatible API base URL"
    )
    OPENAI_LLM_BASE_URL: Optional[str] = Field(
        default=None,
        description="Optional OpenAI-compatible API base URL for chat/LLM calls"
    )
    OPENAI_EMBEDDING_BASE_URL: Optional[str] = Field(
        default=None,
        description="Optional OpenAI-compatible API base URL for embedding calls"
    )
    EMBEDDING_DIMENSION: int = Field(default=1536, description="Dimension of embedding vectors")

    TAVILY_API_KEY: SecretStr = Field(
        default=SecretStr("your-tavily-api-key"),
        description="Tavily API key for search queries"
    )

    MAX_URLS_PER_BATCH: int = Field(default=10, description="Maximum URLs to process per batch")
    MAX_RAW_TEXT_CHARS: int = Field(default=20000, description="Max characters for raw page content")
    MAX_CLEAN_TEXT_CHARS: int = Field(default=12000, description="Max characters for cleaned page content")
    MAX_RETRY_PER_JOB: int = Field(default=1, description="Max retry attempts for failed tasks")
    REQUEST_TIMEOUT_SECONDS: int = Field(default=10, description="HTTP request timeout in seconds")
    MAX_RESPONSE_SIZE_MB: int = Field(default=2, description="Max HTTP response size allowed in MB")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
