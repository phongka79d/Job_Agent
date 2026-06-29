"""Focused unit tests for the mockable LLM client boundary."""

import pytest
from pydantic import SecretStr

from app.agents.schemas import JobPostExtract
from app.services.llm_client import (
    FakeJobExtractionClient,
    LLMProviderError,
    LLMValidationError,
    OpenAIJobExtractionClient,
)


@pytest.mark.asyncio
async def test_fake_client_default_behavior() -> None:
    client = FakeJobExtractionClient()

    # Default extract behavior
    job = await client.extract_job(
        clean_text="Python Developer Job",
        source_url="https://example.com/job",
        source_platform="manual_url",
    )

    assert isinstance(job, JobPostExtract)
    assert job.title == "Fake Software Engineer"
    assert job.jd_status == "full_jd"
    assert job.should_score_similarity is True
    assert job._input_tokens == 100
    assert job._output_tokens == 50
    assert job._estimated_cost_usd == 0.0001
    assert job._extraction_time_ms == 10

    # Default repair behavior
    repaired_job = await client.repair_job(
        clean_text="Python Developer Job",
        invalid_output="{}",
        validation_error="Validation failed",
        source_url="https://example.com/job",
        source_platform="manual_url",
    )

    assert isinstance(repaired_job, JobPostExtract)
    assert repaired_job.title == "Fake Software Engineer"
    assert repaired_job.extraction_notes == "Mocked repaired success"
    assert repaired_job._input_tokens == 120
    assert repaired_job._output_tokens == 60
    assert repaired_job._estimated_cost_usd == 0.00015
    assert repaired_job._extraction_time_ms == 15

    # Check call history
    assert len(client.extract_calls) == 1
    assert client.extract_calls[0]["clean_text"] == "Python Developer Job"
    assert len(client.repair_calls) == 1
    assert client.repair_calls[0]["invalid_output"] == "{}"


@pytest.mark.asyncio
async def test_fake_client_canned_responses() -> None:
    client = FakeJobExtractionClient()

    # Add canned exception for extraction, then valid job for repair
    client.add_extract_response(LLMValidationError("Invalid JSON"))
    
    custom_job = JobPostExtract(
        title="Custom Engineer",
        source_platform="manual_url",
        jd_status="partial_jd",
        should_score_similarity=True,
    )
    client.add_repair_response(custom_job)

    with pytest.raises(LLMValidationError, match="Invalid JSON"):
        await client.extract_job(
            clean_text="Python Developer Job",
            source_url="https://example.com/job",
            source_platform="manual_url",
        )

    repaired = await client.repair_job(
        clean_text="Python Developer Job",
        invalid_output="{}",
        validation_error="Invalid JSON",
        source_url="https://example.com/job",
        source_platform="manual_url",
    )

    assert repaired == custom_job


def test_production_client_lazy_initialization() -> None:
    # Creating the production client should not crash or construct ChatOpenAI immediately,
    # even with placeholder/invalid configurations.
    client = OpenAIJobExtractionClient(
        model_name="test-model",
        api_key=SecretStr("your-openai-api-key"),
    )
    
    assert client.model_name == "test-model"
    assert client._llm is None


@pytest.mark.asyncio
async def test_production_client_raises_provider_error_on_missing_key() -> None:
    # A client configured with default or empty key should raise LLMProviderError on invocation.
    client = OpenAIJobExtractionClient(
        model_name="test-model",
        api_key=SecretStr("your-openai-api-key"),
    )
    
    with pytest.raises(LLMProviderError, match="Valid OPENAI_API_KEY is not configured"):
        await client.extract_job(
            clean_text="test text",
            source_url=None,
            source_platform="manual_text",
        )
