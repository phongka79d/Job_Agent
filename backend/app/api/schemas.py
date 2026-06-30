"""Pydantic request and response schemas for the Phase 4 HTTP API."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.agents.schemas import (
    validate_extraction_status,
    validate_jd_status,
    validate_parse_status,
    validate_source_platform_value,
)
from app.core import constants
from app.core.config import settings


def _enum_field(values: tuple[str, ...]) -> dict[str, list[str]]:
    return {"enum": list(values)}


def _validate_member(
    value: str | None,
    allowed_values: tuple[str, ...],
    field_name: str,
) -> str:
    if value not in allowed_values:
        raise ValueError(f"{field_name} must be one of {allowed_values}")
    return value


class ApiSchema(BaseModel):
    """Base model for route payloads serialized from ORM rows where needed."""

    model_config = ConfigDict(from_attributes=True)


class RoleProfileCreateRequest(ApiSchema):
    target_role: str = Field(min_length=1)
    level: str | None = None
    location: str | None = None
    accept_remote: bool | None = None
    skills: list[str] = Field(default_factory=list)
    resume_text: str | None = None


class RoleProfileResponse(ApiSchema):
    id: UUID
    target_role: str
    level: str | None
    location: str | None
    accept_remote: bool | None
    skills: list[str] = Field(default_factory=list)
    resume_text: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("skills", mode="before")
    @classmethod
    def parse_skills(cls, value: Any) -> list[str]:
        return _parse_string_list(value)


class RoleProfileListResponse(ApiSchema):
    role_profiles: list[RoleProfileResponse] = Field(default_factory=list)


class SearchJobsRequest(ApiSchema):
    role_profile_id: UUID
    query: str = Field(min_length=1)
    max_urls: int = Field(
        default=settings.MAX_URLS_PER_BATCH,
        ge=1,
        le=settings.MAX_URLS_PER_BATCH,
    )


class ParseJobUrlRequest(ApiSchema):
    role_profile_id: UUID
    source_url: HttpUrl


class ParseJobTextRequest(ApiSchema):
    role_profile_id: UUID
    raw_text: str = Field(min_length=1, max_length=settings.MAX_RAW_TEXT_CHARS)
    source_url: HttpUrl | None = None


class MockLoadRequest(ApiSchema):
    role_profile_id: UUID
    reset_existing_demo: bool = False


class StatusUpdateRequest(ApiSchema):
    status: Annotated[
        str,
        Field(json_schema_extra=_enum_field(constants.APPLICATION_STATUSES)),
    ]

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return _validate_member(value, constants.APPLICATION_STATUSES, "status")


class JobResponse(ApiSchema):
    id: UUID
    batch_id: UUID
    role_profile_id: UUID
    title: str | None
    company: str | None
    location: str | None
    work_mode: str | None
    level: str | None
    employment_type: str | None
    salary: str | None
    responsibilities: str | None
    requirements: str | None
    skills: list[str] = Field(default_factory=list)
    source_url: str | None
    source_platform: Annotated[
        str | None,
        Field(json_schema_extra=_enum_field(constants.SOURCE_PLATFORMS)),
    ]
    parse_status: Annotated[
        str | None,
        Field(json_schema_extra=_enum_field(constants.PARSE_STATUSES)),
    ]
    jd_status: Annotated[
        str | None,
        Field(json_schema_extra=_enum_field(constants.JD_STATUSES)),
    ]
    extraction_status: Annotated[
        str | None,
        Field(json_schema_extra=_enum_field(constants.EXTRACTION_STATUSES)),
    ]
    error_reason: str | None
    should_score_similarity: bool
    embedding_similarity: float | None
    skill_overlap_score: float | None
    location_match_score: float | None
    level_match_score: float | None
    base_score: float | None
    jd_confidence_multiplier: float | None
    final_score: float | None
    final_score_percent: float | None
    status: Annotated[
        str,
        Field(json_schema_extra=_enum_field(constants.JOB_STATUSES)),
    ]
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    extraction_time_ms: int | None
    discovered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("skills", mode="before")
    @classmethod
    def parse_skills(cls, value: Any) -> list[str]:
        return _parse_string_list(value)

    @field_validator("source_platform")
    @classmethod
    def validate_source_platform(cls, value: str | None) -> str | None:
        return None if value is None else validate_source_platform_value(value)

    @field_validator("parse_status")
    @classmethod
    def validate_parse_status_value(cls, value: str | None) -> str | None:
        return None if value is None else validate_parse_status(value)

    @field_validator("jd_status")
    @classmethod
    def validate_jd_status_value(cls, value: str | None) -> str | None:
        return None if value is None else validate_jd_status(value)

    @field_validator("extraction_status")
    @classmethod
    def validate_extraction_status_value(cls, value: str | None) -> str | None:
        return validate_extraction_status(value)

    @field_validator("status")
    @classmethod
    def validate_job_status(cls, value: str) -> str:
        return _validate_member(value, constants.JOB_STATUSES, "status")


class StatusMutationResponse(JobResponse):
    """Updated job row returned by approve, reject, and manual status routes."""


class IngestionResponse(ApiSchema):
    batch_id: UUID
    inserted_jobs: int = 0
    skipped_exact_duplicates: int = 0
    skipped_dedup_key_duplicates: int = 0
    inserted_duplicate_metadata: int = 0
    qdrant_upserted: int = 0
    qdrant_synced: bool = True
    jobs: list[JobResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class JobListResponse(ApiSchema):
    jobs: list[JobResponse] = Field(default_factory=list)


class BatchSummaryResponse(ApiSchema):
    batch_id: UUID
    total_parsed_jobs: int
    scorable_jobs: int
    failed_extractions: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    average_extraction_time_ms: float | None


def _parse_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    raise ValueError("skills must be a list of strings")
