"""
Unit Tests for Embedding Service.

Verifies async embedding generation, vector validation, blank text handling,
lazy initialization, and error wrapping without making actual API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.embedding_service import EmbeddingService, EmbeddingServiceError, embed_text
from app.core.config import settings


@pytest.mark.asyncio
async def test_embed_text_blank_input():
    """Verify that blank or empty text throws an EmbeddingServiceError immediately."""
    with pytest.raises(EmbeddingServiceError, match="Input text cannot be blank."):
        await embed_text("")
    with pytest.raises(EmbeddingServiceError, match="Input text cannot be blank."):
        await embed_text("   ")


@pytest.mark.asyncio
async def test_embed_text_success():
    """Verify embedding is generated successfully and matches dimension when api key is present."""
    mock_vector = [0.1] * settings.EMBEDDING_DIMENSION
    
    with patch("app.services.embedding_service.OpenAIEmbeddings") as mock_embeddings_class:
        mock_instance = MagicMock()
        mock_instance.aembed_query = AsyncMock(return_value=mock_vector)
        mock_embeddings_class.return_value = mock_instance
        
        with patch.object(settings.OPENAI_API_KEY, "get_secret_value", return_value="test-api-key"):
            result = await embed_text("This is a valid JD text to embed.")
            
            assert result == mock_vector
            assert len(result) == settings.EMBEDDING_DIMENSION
            mock_instance.aembed_query.assert_called_once_with("This is a valid JD text to embed.")


@pytest.mark.asyncio
async def test_embed_text_dimension_mismatch():
    """Verify dimension mismatch throws an EmbeddingServiceError."""
    # Return vector size smaller than configured
    mock_vector = [0.1] * (settings.EMBEDDING_DIMENSION - 1)
    
    with patch("app.services.embedding_service.OpenAIEmbeddings") as mock_embeddings_class:
        mock_instance = MagicMock()
        mock_instance.aembed_query = AsyncMock(return_value=mock_vector)
        mock_embeddings_class.return_value = mock_instance
        
        with patch.object(settings.OPENAI_API_KEY, "get_secret_value", return_value="test-api-key"):
            with pytest.raises(EmbeddingServiceError, match="Generated vector dimension mismatch"):
                await embed_text("Valid JD text")


@pytest.mark.asyncio
async def test_embed_text_provider_error():
    """Verify that OpenAI API errors are wrapped in EmbeddingServiceError without leaking secrets."""
    secret_value = "sk-test-secret-value"

    with patch("app.services.embedding_service.OpenAIEmbeddings") as mock_embeddings_class:
        mock_instance = MagicMock()
        mock_instance.aembed_query = AsyncMock(side_effect=Exception(f"provider failed for {secret_value}"))
        mock_embeddings_class.return_value = mock_instance
        
        with patch.object(settings.OPENAI_API_KEY, "get_secret_value", return_value=secret_value):
            with pytest.raises(EmbeddingServiceError, match="Provider failed to generate embedding") as exc_info:
                await embed_text("Valid JD text")

            assert secret_value not in str(exc_info.value)


@pytest.mark.asyncio
async def test_lazy_initialization_no_api_key():
    """Verify lazy initialization and correct error when API key is missing or is default."""
    with patch.object(settings.OPENAI_API_KEY, "get_secret_value", return_value="your-openai-api-key"):
        # Creating service should not fail on import/instantiation
        service = EmbeddingService()
        
        # Calling embedding function without key should raise error
        with pytest.raises(EmbeddingServiceError, match="OpenAI API key is not configured"):
            await service.embed_text("Valid JD text")


@pytest.mark.asyncio
async def test_lazy_initialization_empty_api_key():
    """Verify that empty API key raises appropriate error."""
    with patch.object(settings.OPENAI_API_KEY, "get_secret_value", return_value=""):
        service = EmbeddingService()
        with pytest.raises(EmbeddingServiceError, match="OpenAI API key is not configured"):
            await service.embed_text("Valid JD text")
