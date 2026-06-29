"""Embedding service implementation for generating and validating text embeddings."""

import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Exception raised for failures within the embedding service."""
    pass


class EmbeddingService:
    """Service for managing text embeddings using LangChain's OpenAIEmbeddings."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        embedding_dimension: Optional[int] = None,
        openai_api_key: Optional[str] = None,
    ):
        self.model_name = model_name or settings.OPENAI_EMBEDDING_MODEL
        self.embedding_dimension = embedding_dimension or settings.EMBEDDING_DIMENSION
        
        # Read API key. If not provided, fetch from settings lazily.
        self._openai_api_key = openai_api_key
        self._client: Optional[OpenAIEmbeddings] = None

    def _get_client(self) -> OpenAIEmbeddings:
        """Lazily initialize the OpenAIEmbeddings client."""
        if self._client is None:
            api_key = self._openai_api_key
            if not api_key:
                api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else ""

            if not api_key or api_key == "your-openai-api-key":
                raise EmbeddingServiceError(
                    "OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable."
                )
            
            try:
                self._client = OpenAIEmbeddings(
                    openai_api_key=api_key,
                    model=self.model_name,
                )
            except Exception as e:
                logger.error("Failed to initialize OpenAIEmbeddings client")
                raise EmbeddingServiceError(f"Initialization error: {str(e)}") from e
        return self._client

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.
        
        Args:
            text: The input string to embed.
            
        Returns:
            A list of floats representing the embedding vector.
            
        Raises:
            EmbeddingServiceError: If text is blank, provider fails, or returned vector
                                   dimension doesn't match EMBEDDING_DIMENSION.
        """
        if not text or not text.strip():
            raise EmbeddingServiceError("Input text cannot be blank.")

        client = self._get_client()

        try:
            vector = await client.aembed_query(text)
        except Exception as e:
            logger.error("Error generating text embedding from provider")
            raise EmbeddingServiceError(f"Provider failed to generate embedding: {str(e)}") from e

        expected_dim = settings.EMBEDDING_DIMENSION
        if len(vector) != expected_dim:
            raise EmbeddingServiceError(
                f"Generated vector dimension mismatch: expected {expected_dim}, got {len(vector)}."
            )

        return vector


async def embed_text(text: str) -> List[float]:
    """
    Generate embedding for the given text using default service configuration.
    
    Args:
        text: The input string to embed.
        
    Returns:
        A list of floats representing the embedding vector.
    """
    service = EmbeddingService()
    return await service.embed_text(text)
