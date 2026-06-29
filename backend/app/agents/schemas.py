"""Shared state and structured-output contracts for job extraction."""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator

from app.core import constants


_SOURCE_PLATFORM_BY_INPUT_SOURCE = {
    "tavily": "tavily",
    "manual_url": "manual_url",
    "manual_text": "manual_text",
    "mock": "mock",
}


def _validate_constant_value(
    value: str | None,
    allowed_values: tuple[str, ...],
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    if value is None and allow_none:
        return None
    if value not in allowed_values:
        raise ValueError(f"{field_name} must be one of {allowed_values}")
    return value


def validate_input_source(input_source: str | None) -> str:
    value = _validate_constant_value(
        input_source,
        constants.INPUT_SOURCES,
        "input_source",
    )
    assert value is not None
    return value


def validate_source_platform_value(source_platform: str | None) -> str:
    value = _validate_constant_value(
        source_platform,
        constants.SOURCE_PLATFORMS,
        "source_platform",
    )
    assert value is not None
    return value


def validate_parse_status(parse_status: str | None) -> str:
    value = _validate_constant_value(
        parse_status,
        constants.PARSE_STATUSES,
        "parse_status",
    )
    assert value is not None
    return value


def validate_extraction_status(extraction_status: str | None) -> str | None:
    return _validate_constant_value(
        extraction_status,
        constants.EXTRACTION_STATUSES,
        "extraction_status",
        allow_none=True,
    )


def validate_jd_status(jd_status: str | None) -> str:
    value = _validate_constant_value(
        jd_status,
        constants.JD_STATUSES,
        "jd_status",
    )
    assert value is not None
    return value


def map_input_source_to_source_platform(input_source: str) -> str:
    """Return the approved Plan 2 source platform for an input source."""

    validate_input_source(input_source)

    try:
        source_platform = _SOURCE_PLATFORM_BY_INPUT_SOURCE[input_source]
    except KeyError as exc:
        raise ValueError(
            f"input_source has no approved source platform mapping: {input_source}"
        ) from exc

    validate_source_platform_value(source_platform)
    return source_platform


class JobAgentState(TypedDict, total=False):
    """Partial state passed between nodes in the extraction graph."""

    batch_id: str
    role_profile_id: str
    input_source: Literal["tavily", "manual_url", "manual_text", "mock"]

    source_url: str | None
    raw_text: str | None
    raw_content_hash: str | None

    clean_text: str | None
    parse_status: Literal["success", "needs_manual_input", "failed"]
    extracted_job: dict[str, Any] | None
    jd_status: Literal[
        "full_jd",
        "partial_jd",
        "contact_for_jd",
        "no_jd",
        "unclear",
    ] | None
    should_score_similarity: bool | None

    embedding_text: str | None
    embedding_similarity: float | None
    skill_overlap_score: float | None
    location_match_score: float | None
    level_match_score: float | None
    base_score: float | None
    jd_confidence_multiplier: float | None
    final_score: float | None
    final_score_percent: float | None

    extraction_status: Literal["success", "retried", "failed"] | None
    error_reason: str | None
    user_warning: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    extraction_time_ms: int | None


def preserve_required_state(state: JobAgentState) -> JobAgentState:
    """Copy the identifiers and validated input source required in every update."""

    input_source = state["input_source"]
    map_input_source_to_source_platform(input_source)
    return {
        "batch_id": state["batch_id"],
        "role_profile_id": state["role_profile_id"],
        "input_source": input_source,
    }


def score_placeholder_update(state: JobAgentState) -> JobAgentState:
    """Build a required-state-preserving update with all score fields unset."""

    return {
        **preserve_required_state(state),
        "embedding_text": None,
        "embedding_similarity": None,
        "skill_overlap_score": None,
        "location_match_score": None,
        "level_match_score": None,
        "base_score": None,
        "jd_confidence_multiplier": None,
        "final_score": None,
        "final_score_percent": None,
    }


class JobPostExtract(BaseModel):
    """Validated structured job data emitted by the extraction graph."""

    title: str | None = None
    company: str | None = None
    location: str | None = None
    work_mode: Literal["onsite", "remote", "hybrid", "unknown"] = "unknown"
    level: Literal["intern", "fresher", "junior", "mid", "senior", "unknown"] = (
        "unknown"
    )
    employment_type: Literal[
        "internship",
        "full-time",
        "part-time",
        "contract",
        "unknown",
    ] = "unknown"
    salary: str | None = None

    responsibilities: str | None = None
    requirements: str | None = None
    skills: list[str] = Field(default_factory=list)

    source_url: str | None = None
    source_platform: str

    jd_status: str
    should_score_similarity: bool

    extraction_notes: str | None = None

    @field_validator("source_platform")
    @classmethod
    def validate_source_platform(cls, value: str) -> str:
        """Reject source platforms outside the Phase 1 shared contract."""

        return validate_source_platform_value(value)

    @field_validator("jd_status")
    @classmethod
    def validate_jd_status(cls, value: str) -> str:
        """Reject JD statuses outside the Phase 1 shared contract."""

        return validate_jd_status(value)


def build_unclear_job(
    *,
    source_url: str | None,
    source_platform: str,
    extraction_note: str,
) -> dict[str, Any]:
    """Build the complete validated job shape used by unclear fallbacks."""

    if source_platform not in _SOURCE_PLATFORM_BY_INPUT_SOURCE.values():
        raise ValueError(
            "source_platform must be produced by the approved Plan 2 source mapping"
        )

    return JobPostExtract(
        source_url=source_url,
        source_platform=source_platform,
        jd_status="unclear",
        should_score_similarity=False,
        extraction_notes=extraction_note,
    ).model_dump()


def build_unclear_extraction_failure_update(
    state: JobAgentState,
    *,
    extraction_note: str,
    error_reason: str | None = None,
) -> JobAgentState:
    """Build the complete state update for a post-parse extraction failure."""

    source_platform = map_input_source_to_source_platform(state["input_source"])
    return {
        **score_placeholder_update(state),
        "parse_status": "success",
        "extracted_job": build_unclear_job(
            source_url=state.get("source_url"),
            source_platform=source_platform,
            extraction_note=extraction_note,
        ),
        "jd_status": "unclear",
        "should_score_similarity": False,
        "extraction_status": "failed",
        "error_reason": error_reason or extraction_note,
    }
