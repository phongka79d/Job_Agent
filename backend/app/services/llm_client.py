"""Mockable LLM extraction client boundary implementation."""

from decimal import Decimal
from typing import Any, Mapping, Optional, Protocol

from pydantic import SecretStr, ValidationError
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agents.prompts import build_extraction_prompt, build_repair_prompt
from app.agents.schemas import JobPostExtract
from app.core.config import settings
from app.services.cost_service import TokenPricing, normalize_usage, track_extraction_time


class LLMExtractionError(Exception):
    """Base exception for LLM extraction and validation failures."""

    def __init__(self, message: str, extraction_time_ms: int | None = None):
        super().__init__(message)
        self.extraction_time_ms = extraction_time_ms


class LLMProviderError(LLMExtractionError):
    """Raised when the LLM provider fails (e.g., API error, timeout, quota)."""
    pass


class LLMValidationError(LLMExtractionError):
    """Raised when the LLM response fails validation (e.g., invalid JSON or Pydantic error)."""

    def __init__(
        self,
        message: str,
        invalid_output: str | None = None,
        extraction_time_ms: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
    ):
        super().__init__(message, extraction_time_ms)
        self.invalid_output = invalid_output
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.estimated_cost_usd = estimated_cost_usd


class JobExtractionClientProtocol(Protocol):
    """Protocol defining the operations for LLM job extraction."""

    async def extract_job(
        self,
        *,
        clean_text: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        ...

    async def repair_job(
        self,
        *,
        clean_text: str,
        invalid_output: str,
        validation_error: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        ...


# Explicit per-million-token prices for supported models
_MODEL_PRICING = {
    "gpt-4o-mini": TokenPricing(
        input_cost_per_million_tokens=Decimal("0.150"),
        output_cost_per_million_tokens=Decimal("0.600"),
    ),
    "gpt-4o": TokenPricing(
        input_cost_per_million_tokens=Decimal("2.50"),
        output_cost_per_million_tokens=Decimal("10.00"),
    ),
}


class OpenAIJobExtractionClient(JobExtractionClientProtocol):
    """Production implementation of the LLM extraction client using OpenAI/LangChain."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[SecretStr] = None,
    ):
        self.model_name = model_name or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._llm = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            # Lazy initialization to avoid validation failure on import if API key is not present.
            api_key_str = self.api_key.get_secret_value() if self.api_key else ""
            if not api_key_str or api_key_str == "your-openai-api-key":
                raise LLMProviderError("Valid OPENAI_API_KEY is not configured.")

            try:
                # Requesting both parsed output and raw response metadata (include_raw=True)
                self._llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=api_key_str,
                    temperature=0.0,
                ).with_structured_output(JobPostExtract, include_raw=True)
            except Exception as e:
                raise LLMProviderError(f"Failed to initialize ChatOpenAI: {e}") from e
        return self._llm

    async def extract_job(
        self,
        *,
        clean_text: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        prompt_text = build_extraction_prompt(
            clean_text=clean_text,
            source_url=source_url,
            source_platform=source_platform,
        )
        prompt = ChatPromptTemplate.from_messages([("user", prompt_text)])
        llm = self._get_llm()

        with track_extraction_time() as timing:
            try:
                response = await llm.ainvoke(prompt)
            except (ValidationError, OutputParserException) as e:
                invalid_output = getattr(e, "llm_output", None)
                if not invalid_output and hasattr(e, "observation"):
                    invalid_output = str(e.observation)
                if not invalid_output:
                    invalid_output = str(e)
                raise LLMValidationError(
                    f"Extraction output failed validation: {e}",
                    invalid_output=invalid_output,
                    extraction_time_ms=timing.extraction_time_ms,
                ) from e
            except Exception as e:
                raise LLMProviderError(
                    f"LLM provider call failed: {e}",
                    extraction_time_ms=timing.extraction_time_ms,
                ) from e

        if response.get("parsed") is None:
            raw_message = response.get("raw")
            raw_content = raw_message.content if raw_message else ""
            usage_metadata = self._get_usage_metadata(raw_message)
            usage_res = normalize_usage(
                usage_metadata,
                pricing=_MODEL_PRICING.get(self.model_name),
                extraction_time_ms=timing.extraction_time_ms,
            )
            raise LLMValidationError(
                "LLM output could not be parsed into JobPostExtract schema.",
                invalid_output=raw_content,
                extraction_time_ms=timing.extraction_time_ms,
                input_tokens=usage_res["input_tokens"],
                output_tokens=usage_res["output_tokens"],
                estimated_cost_usd=usage_res["estimated_cost_usd"],
            )

        parsed_result = response["parsed"]
        raw_message = response.get("raw")
        usage_metadata = self._get_usage_metadata(raw_message)
        usage_res = normalize_usage(
            usage_metadata,
            pricing=_MODEL_PRICING.get(self.model_name),
            extraction_time_ms=timing.extraction_time_ms,
        )

        parsed_result._input_tokens = usage_res["input_tokens"]
        parsed_result._output_tokens = usage_res["output_tokens"]
        parsed_result._estimated_cost_usd = usage_res["estimated_cost_usd"]
        parsed_result._extraction_time_ms = usage_res["extraction_time_ms"]

        return parsed_result

    async def repair_job(
        self,
        *,
        clean_text: str,
        invalid_output: str,
        validation_error: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        prompt_text = build_repair_prompt(
            clean_text=clean_text,
            invalid_output=invalid_output,
            validation_error=validation_error,
            source_url=source_url,
            source_platform=source_platform,
        )
        prompt = ChatPromptTemplate.from_messages([("user", prompt_text)])
        llm = self._get_llm()

        with track_extraction_time() as timing:
            try:
                response = await llm.ainvoke(prompt)
            except (ValidationError, OutputParserException) as e:
                invalid_output = getattr(e, "llm_output", None)
                if not invalid_output and hasattr(e, "observation"):
                    invalid_output = str(e.observation)
                if not invalid_output:
                    invalid_output = str(e)
                raise LLMValidationError(
                    f"Repair output failed validation: {e}",
                    invalid_output=invalid_output,
                    extraction_time_ms=timing.extraction_time_ms,
                ) from e
            except Exception as e:
                raise LLMProviderError(
                    f"LLM provider call failed: {e}",
                    extraction_time_ms=timing.extraction_time_ms,
                ) from e

        if response.get("parsed") is None:
            raw_message = response.get("raw")
            raw_content = raw_message.content if raw_message else ""
            usage_metadata = self._get_usage_metadata(raw_message)
            usage_res = normalize_usage(
                usage_metadata,
                pricing=_MODEL_PRICING.get(self.model_name),
                extraction_time_ms=timing.extraction_time_ms,
            )
            raise LLMValidationError(
                "LLM repair output could not be parsed into JobPostExtract schema.",
                invalid_output=raw_content,
                extraction_time_ms=timing.extraction_time_ms,
                input_tokens=usage_res["input_tokens"],
                output_tokens=usage_res["output_tokens"],
                estimated_cost_usd=usage_res["estimated_cost_usd"],
            )

        parsed_result = response["parsed"]
        raw_message = response.get("raw")
        usage_metadata = self._get_usage_metadata(raw_message)
        usage_res = normalize_usage(
            usage_metadata,
            pricing=_MODEL_PRICING.get(self.model_name),
            extraction_time_ms=timing.extraction_time_ms,
        )

        parsed_result._input_tokens = usage_res["input_tokens"]
        parsed_result._output_tokens = usage_res["output_tokens"]
        parsed_result._estimated_cost_usd = usage_res["estimated_cost_usd"]
        parsed_result._extraction_time_ms = usage_res["extraction_time_ms"]

        return parsed_result

    def _get_usage_metadata(self, raw_message: Any) -> Optional[Mapping[str, int]]:
        if raw_message and hasattr(raw_message, "response_metadata"):
            token_usage = raw_message.response_metadata.get("token_usage")
            if token_usage:
                return {
                    "input_tokens": token_usage.get("prompt_tokens"),
                    "output_tokens": token_usage.get("completion_tokens"),
                }
        return None


class FakeJobExtractionClient(JobExtractionClientProtocol):
    """Mockable LLM extraction client for isolated unit and graph testing."""

    def __init__(self):
        self.extract_responses: list[Any] = []
        self.repair_responses: list[Any] = []
        self.extract_calls: list[dict[str, Any]] = []
        self.repair_calls: list[dict[str, Any]] = []
        self.default_extract_response: Optional[Any] = None
        self.default_repair_response: Optional[Any] = None

    def add_extract_response(self, response: Any) -> None:
        """Queue a mock response or Exception for the next extract_job call."""
        self.extract_responses.append(response)

    def add_repair_response(self, response: Any) -> None:
        """Queue a mock response or Exception for the next repair_job call."""
        self.repair_responses.append(response)

    async def extract_job(
        self,
        *,
        clean_text: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        self.extract_calls.append({
            "clean_text": clean_text,
            "source_url": source_url,
            "source_platform": source_platform,
        })

        if self.extract_responses:
            res = self.extract_responses.pop(0)
        else:
            res = self.default_extract_response

        if isinstance(res, Exception):
            raise res
        elif res is not None:
            return res

        # Return a valid default JobPostExtract if no canned response is set
        default_job = JobPostExtract(
            title="Fake Software Engineer",
            company="Fake Corp",
            location="Remote",
            work_mode="remote",
            level="mid",
            employment_type="full-time",
            salary="100k-120k",
            responsibilities="Write fake code.",
            requirements="Know how to fake.",
            skills=["Python", "Testing"],
            source_url=source_url,
            source_platform=source_platform,
            jd_status="full_jd",
            should_score_similarity=True,
            extraction_notes="Mocked success",
        )
        default_job._input_tokens = 100
        default_job._output_tokens = 50
        default_job._estimated_cost_usd = 0.0001
        default_job._extraction_time_ms = 10
        return default_job

    async def repair_job(
        self,
        *,
        clean_text: str,
        invalid_output: str,
        validation_error: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        self.repair_calls.append({
            "clean_text": clean_text,
            "invalid_output": invalid_output,
            "validation_error": validation_error,
            "source_url": source_url,
            "source_platform": source_platform,
        })

        if self.repair_responses:
            res = self.repair_responses.pop(0)
        else:
            res = self.default_repair_response

        if isinstance(res, Exception):
            raise res
        elif res is not None:
            return res

        # Return a valid default repaired JobPostExtract if no canned response is set
        repaired_job = JobPostExtract(
            title="Fake Software Engineer",
            company="Fake Corp",
            location="Remote",
            work_mode="remote",
            level="mid",
            employment_type="full-time",
            salary="100k-120k",
            responsibilities="Write fake code.",
            requirements="Know how to fake.",
            skills=["Python", "Testing"],
            source_url=source_url,
            source_platform=source_platform,
            jd_status="full_jd",
            should_score_similarity=True,
            extraction_notes="Mocked repaired success",
        )
        repaired_job._input_tokens = 120
        repaired_job._output_tokens = 60
        repaired_job._estimated_cost_usd = 0.00015
        repaired_job._extraction_time_ms = 15
        return repaired_job
