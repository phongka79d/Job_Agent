"""Focused unit tests for the LLM client boundary."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from app.agents.schemas import JobPostExtract
from app.core.config import settings
from app.services.llm_client import (
    LLMProviderError,
    LLMValidationError,
    OpenAIJobExtractionClient,
)


class _RawMessage:
    response_metadata = {
        "token_usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        }
    }


class _StructuredLLMDouble:
    def __init__(self, parsed: JobPostExtract):
        self.parsed = parsed
        self.prompts: list[Any] = []

    async def ainvoke(self, prompt: Any) -> dict[str, Any]:
        if not isinstance(prompt, str):
            raise ValueError(f"invalid prompt type: {type(prompt).__name__}")
        self.prompts.append(prompt)
        return {
            "parsed": self.parsed,
            "raw": _RawMessage(),
        }


def test_production_client_lazy_initialization() -> None:
    # Creating the production client should not construct ChatOpenAI immediately.
    client = OpenAIJobExtractionClient(
        model_name="test-model",
        api_key=SecretStr("your-openai-api-key"),
    )
    
    assert client.model_name == "test-model"
    assert client._llm is None


def test_production_client_passes_configured_base_url() -> None:
    structured_llm = MagicMock()

    with patch("app.services.llm_client.ChatOpenAI") as chat_openai:
        chat_openai.return_value.with_structured_output.return_value = structured_llm

        client = OpenAIJobExtractionClient(
            model_name="test-model",
            api_key=SecretStr("test-api-key"),
            base_url="https://llm-gateway.test/v1",
        )
        llm = client._get_llm()

    assert llm is structured_llm
    chat_openai.assert_called_once_with(
        model="test-model",
        api_key="test-api-key",
        base_url="https://llm-gateway.test/v1",
        temperature=0.0,
    )
    chat_openai.return_value.with_structured_output.assert_called_once_with(
        JobPostExtract,
        include_raw=True,
    )


def test_production_client_uses_llm_base_url_from_settings(monkeypatch) -> None:
    structured_llm = MagicMock()
    monkeypatch.setattr(settings, "OPENAI_BASE_URL", "https://common-gateway.test/v1", raising=False)
    monkeypatch.setattr(settings, "OPENAI_LLM_BASE_URL", "https://settings-llm-gateway.test/v1", raising=False)

    with patch("app.services.llm_client.ChatOpenAI") as chat_openai:
        chat_openai.return_value.with_structured_output.return_value = structured_llm

        client = OpenAIJobExtractionClient(
            model_name="test-model",
            api_key=SecretStr("test-api-key"),
        )
        client._get_llm()

    assert chat_openai.call_args.kwargs["base_url"] == "https://settings-llm-gateway.test/v1"


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


@pytest.mark.asyncio
async def test_production_client_invokes_structured_llm_with_prompt_text() -> None:
    parsed = JobPostExtract(
        title="Production Engineer",
        source_platform="manual_text",
        jd_status="full_jd",
        should_score_similarity=True,
    )
    llm = _StructuredLLMDouble(parsed)
    client = OpenAIJobExtractionClient(
        model_name="gpt-4o-mini",
        api_key=SecretStr("test-api-key"),
    )
    client._llm = llm

    job = await client.extract_job(
        clean_text="Hiring a Production Engineer with Python experience.",
        source_url=None,
        source_platform="manual_text",
    )

    assert job == parsed
    assert llm.prompts
    assert "Hiring a Production Engineer" in llm.prompts[0]
    assert job._input_tokens == 100
    assert job._output_tokens == 50


@pytest.mark.asyncio
async def test_production_client_repair_invokes_structured_llm_with_prompt_text() -> None:
    parsed = JobPostExtract(
        title="Repaired Engineer",
        source_platform="manual_url",
        jd_status="partial_jd",
        should_score_similarity=True,
    )
    llm = _StructuredLLMDouble(parsed)
    client = OpenAIJobExtractionClient(
        model_name="gpt-4o-mini",
        api_key=SecretStr("test-api-key"),
    )
    client._llm = llm

    job = await client.repair_job(
        clean_text="Hiring a Repaired Engineer. Python required.",
        invalid_output="{}",
        validation_error="missing required fields",
        source_url="https://example.com/job",
        source_platform="manual_url",
    )

    assert job == parsed
    assert llm.prompts
    assert "missing required fields" in llm.prompts[0]
    assert job._input_tokens == 100
    assert job._output_tokens == 50
