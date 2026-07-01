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


class ChatConversationCreateRequest(ApiSchema):
    role_profile_id: UUID
    title: str | None = Field(default=None, max_length=200)


class ChatConversationResponse(ApiSchema):
    id: UUID
    role_profile_id: UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ChatConversationListResponse(ApiSchema):
    conversations: list[ChatConversationResponse] = Field(default_factory=list)


class ChatMessageCreateRequest(ApiSchema):
    content: str = Field(min_length=1, max_length=20000)


class ChatMessageResponse(ApiSchema):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    token_count: int | None
    metadata_json: str | None
    created_at: datetime


class ChatMessageListResponse(ApiSchema):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ChatMessageCreateResponse(ApiSchema):
    message: ChatMessageResponse
    stream_url: str


class AgentToolCallResponse(ApiSchema):
    id: UUID
    conversation_id: UUID
    assistant_message_id: UUID | None
    tool_name: str
    status: str
    input_summary: str
    result_summary: str | None
    safe_payload_json: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentToolCallListResponse(ApiSchema):
    tool_calls: list[AgentToolCallResponse] = Field(default_factory=list)


class ProfileDocumentResponse(ApiSchema):
    id: UUID
    role_profile_id: UUID
    original_filename: str
    document_kind: str
    active_version_id: UUID | None
    is_active: bool = False
    mime_type: str
    file_size_bytes: int
    extracted_text_chars: int
    chunk_count: int
    status: str
    error_reason: str | None
    created_at: datetime
    updated_at: datetime


class ProfileDocumentListResponse(ApiSchema):
    documents: list[ProfileDocumentResponse] = Field(default_factory=list)


class ProfileDocumentVersionResponse(ApiSchema):
    id: UUID
    document_id: UUID
    role_profile_id: UUID
    version_number: int
    source_type: str
    parent_version_id: UUID | None = None
    draft_id: UUID | None = None
    display_name: str
    filename: str
    mime_type: str
    file_size_bytes: int
    extracted_text_chars: int
    chunk_count: int
    extraction_status: str
    structure_status: str
    structure_confidence: float | None
    error_reason: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class ProfileDocumentVersionListResponse(ApiSchema):
    versions: list[ProfileDocumentVersionResponse] = Field(default_factory=list)


class ActiveCvResponse(ApiSchema):
    document: ProfileDocumentResponse | None = None
    version: ProfileDocumentVersionResponse | None = None


class ActivateCvVersionRequest(ApiSchema):
    confirmed: bool = False


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


class CvImprovementSuggestionCreateRequest(ApiSchema):
    requirement: str = Field(min_length=1)
    current_cv_evidence: str = Field(min_length=1)
    missing_or_weak_evidence: str = Field(min_length=1)
    proposed_edit: str = Field(min_length=1)
    edit_kind: str = Field(pattern="^(wording_only|requires_user_fact)$")
    risk_level: str = Field(pattern="^(low|medium|high)$")
    requires_confirmation: bool = True
    job_id: UUID | None = None


class CvImprovementSuggestionResponse(ApiSchema):
    id: UUID
    role_profile_id: UUID
    document_id: UUID
    version_id: UUID
    job_id: UUID | None
    requirement: str
    current_cv_evidence: str
    missing_or_weak_evidence: str
    proposed_edit: str
    edit_kind: str
    risk_level: str
    requires_confirmation: bool
    status: str
    created_at: datetime
    updated_at: datetime


class CvImprovementSuggestionListResponse(ApiSchema):
    suggestions: list[CvImprovementSuggestionResponse] = Field(default_factory=list)


class CvDraftCreateRequest(ApiSchema):
    title: str = Field(min_length=1, max_length=200)
    suggestion_ids: list[UUID] = Field(default_factory=list)
    confirmed: bool = False


class CvDraftResponse(ApiSchema):
    id: UUID
    role_profile_id: UUID
    document_id: UUID
    base_version_id: UUID
    status: str
    title: str
    structure_status_at_creation: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class CvDraftListResponse(ApiSchema):
    drafts: list[CvDraftResponse] = Field(default_factory=list)


class CvDraftExportRequest(ApiSchema):
    confirmed: bool = False


class CvDraftPreviewResponse(ApiSchema):
    draft_id: UUID
    title: str
    status: str
    structure_status: str
    recommendation: str | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    edits: list[dict[str, Any]] = Field(default_factory=list)
