"""Test-only doubles for external service boundaries."""

from __future__ import annotations

from typing import Any

from app.agents.schemas import JobPostExtract
from app.services.llm_client import JobExtractionClientProtocol


class ScriptedJobExtractionClient(JobExtractionClientProtocol):
    """Deterministic LLM client double confined to backend tests."""

    def __init__(self) -> None:
        self.extract_responses: list[Any] = []
        self.repair_responses: list[Any] = []
        self.extract_calls: list[dict[str, Any]] = []
        self.repair_calls: list[dict[str, Any]] = []
        self.default_extract_response: Any | None = None
        self.default_repair_response: Any | None = None

    def add_extract_response(self, response: Any) -> None:
        self.extract_responses.append(response)

    def add_repair_response(self, response: Any) -> None:
        self.repair_responses.append(response)

    async def extract_job(
        self,
        *,
        clean_text: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        self.extract_calls.append(
            {
                "clean_text": clean_text,
                "source_url": source_url,
                "source_platform": source_platform,
            }
        )
        response = (
            self.extract_responses.pop(0)
            if self.extract_responses
            else self.default_extract_response
        )
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        return _job_post_extract(source_url=source_url, source_platform=source_platform)

    async def repair_job(
        self,
        *,
        clean_text: str,
        invalid_output: str,
        validation_error: str,
        source_url: str | None,
        source_platform: str,
    ) -> JobPostExtract:
        self.repair_calls.append(
            {
                "clean_text": clean_text,
                "invalid_output": invalid_output,
                "validation_error": validation_error,
                "source_url": source_url,
                "source_platform": source_platform,
            }
        )
        response = (
            self.repair_responses.pop(0)
            if self.repair_responses
            else self.default_repair_response
        )
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        return _job_post_extract(
            source_url=source_url,
            source_platform=source_platform,
            title="Repaired Test Engineer",
            input_tokens=120,
            output_tokens=60,
            estimated_cost_usd=0.00015,
            extraction_time_ms=15,
            extraction_notes="Repaired deterministic response",
        )


def _job_post_extract(
    *,
    source_url: str | None,
    source_platform: str,
    title: str = "Test Engineer",
    input_tokens: int = 100,
    output_tokens: int = 50,
    estimated_cost_usd: float = 0.0001,
    extraction_time_ms: int = 10,
    extraction_notes: str = "Deterministic response",
) -> JobPostExtract:
    job = JobPostExtract(
        title=title,
        company="Example Company",
        location="Remote",
        work_mode="remote",
        level="mid",
        employment_type="full-time",
        salary="100000-120000",
        responsibilities="Build production services.",
        requirements="Python and testing experience.",
        skills=["Python", "Testing"],
        source_url=source_url,
        source_platform=source_platform,
        jd_status="full_jd",
        should_score_similarity=True,
        extraction_notes=extraction_notes,
    )
    job._input_tokens = input_tokens
    job._output_tokens = output_tokens
    job._estimated_cost_usd = estimated_cost_usd
    job._extraction_time_ms = extraction_time_ms
    return job
