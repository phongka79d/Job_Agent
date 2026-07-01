"""Generate the frontend API contract from backend-owned sources."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Type

from pydantic import BaseModel

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.schemas import (
    AgentToolCallListResponse,
    AgentToolCallResponse,
    BatchSummaryResponse,
    ChatConversationCreateRequest,
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    IngestionResponse,
    JobListResponse,
    JobResponse,
    ParseJobTextRequest,
    ParseJobUrlRequest,
    ProfileDocumentListResponse,
    ProfileDocumentResponse,
    RoleProfileCreateRequest,
    RoleProfileListResponse,
    RoleProfileResponse,
    SearchJobsRequest,
    StatusMutationResponse,
    StatusUpdateRequest,
)
from app.core import constants
from app.services.job_processing_service import ALLOWED_STATUS_TRANSITIONS


REPOSITORY_ROOT = BACKEND_ROOT.parent
CONTRACT_PATH = REPOSITORY_ROOT / "shared" / "api-contract.json"
logger = logging.getLogger(__name__)

ENDPOINTS = {
    "createRoleProfile": {
        "method": "POST",
        "path": "/api/role-profiles",
        "request_schema": "RoleProfileCreateRequest",
        "response_schema": "RoleProfileResponse",
    },
    "listRoleProfiles": {
        "method": "GET",
        "path": "/api/role-profiles",
        "response_schema": "RoleProfileListResponse",
    },
    "searchJobs": {
        "method": "POST",
        "path": "/api/jobs/search",
        "request_schema": "SearchJobsRequest",
        "response_schema": "IngestionResponse",
    },
    "parseJobUrl": {
        "method": "POST",
        "path": "/api/jobs/parse-url",
        "request_schema": "ParseJobUrlRequest",
        "response_schema": "IngestionResponse",
    },
    "parseJobText": {
        "method": "POST",
        "path": "/api/jobs/parse-text",
        "request_schema": "ParseJobTextRequest",
        "response_schema": "IngestionResponse",
    },
    "getReviewJobs": {
        "method": "GET",
        "path": "/api/jobs/review",
        "response_schema": "JobListResponse",
    },
    "approveJob": {
        "method": "POST",
        "path": "/api/jobs/{id}/approve",
        "response_schema": "StatusMutationResponse",
    },
    "rejectJob": {
        "method": "POST",
        "path": "/api/jobs/{id}/reject",
        "response_schema": "StatusMutationResponse",
    },
    "updateJobStatus": {
        "method": "PATCH",
        "path": "/api/jobs/{id}/status",
        "request_schema": "StatusUpdateRequest",
        "response_schema": "StatusMutationResponse",
    },
    "getJobs": {
        "method": "GET",
        "path": "/api/jobs",
        "response_schema": "JobListResponse",
    },
    "getJobDetail": {
        "method": "GET",
        "path": "/api/jobs/{id}",
        "response_schema": "JobResponse",
    },
    "getBatchSummary": {
        "method": "GET",
        "path": "/api/batches/{batch_id}/summary",
        "response_schema": "BatchSummaryResponse",
    },
    "createConversation": {
        "method": "POST",
        "path": "/api/chat/conversations",
        "request_schema": "ChatConversationCreateRequest",
        "response_schema": "ChatConversationResponse",
    },
    "listConversations": {
        "method": "GET",
        "path": "/api/chat/conversations",
        "response_schema": "ChatConversationListResponse",
    },
    "sendChatMessage": {
        "method": "POST",
        "path": "/api/chat/conversations/{conversation_id}/messages",
        "request_schema": "ChatMessageCreateRequest",
        "response_schema": "ChatMessageCreateResponse",
    },
    "listChatMessages": {
        "method": "GET",
        "path": "/api/chat/conversations/{conversation_id}/messages",
        "response_schema": "ChatMessageListResponse",
    },
    "listAgentToolCalls": {
        "method": "GET",
        "path": "/api/chat/conversations/{conversation_id}/tool-calls",
        "response_schema": "AgentToolCallListResponse",
    },
    "uploadProfileDocument": {
        "method": "POST",
        "path": "/api/role-profiles/{role_profile_id}/documents",
        "response_schema": "ProfileDocumentResponse",
    },
    "listProfileDocuments": {
        "method": "GET",
        "path": "/api/role-profiles/{role_profile_id}/documents",
        "response_schema": "ProfileDocumentListResponse",
    },
}

SCHEMA_MODELS: tuple[Type[BaseModel], ...] = (
    RoleProfileCreateRequest,
    RoleProfileResponse,
    RoleProfileListResponse,
    SearchJobsRequest,
    ParseJobUrlRequest,
    ParseJobTextRequest,
    StatusUpdateRequest,
    JobResponse,
    StatusMutationResponse,
    IngestionResponse,
    JobListResponse,
    BatchSummaryResponse,
    ChatConversationCreateRequest,
    ChatConversationResponse,
    ChatConversationListResponse,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatMessageListResponse,
    ChatMessageCreateResponse,
    AgentToolCallResponse,
    AgentToolCallListResponse,
    ProfileDocumentResponse,
    ProfileDocumentListResponse,
)


def _ordered_transition_targets(targets: frozenset[str]) -> list[str]:
    return [status for status in constants.JOB_STATUSES if status in targets]


def build_api_contract() -> dict[str, object]:
    return {
        "job_statuses": list(constants.JOB_STATUSES),
        "tracked_job_statuses": list(constants.TRACKED_JOB_STATUSES),
        "application_statuses": list(constants.APPLICATION_STATUSES),
        "jd_statuses": list(constants.JD_STATUSES),
        "parse_statuses": list(constants.PARSE_STATUSES),
        "extraction_statuses": list(constants.EXTRACTION_STATUSES),
        "source_platforms": list(constants.SOURCE_PLATFORMS),
        "input_sources": list(constants.INPUT_SOURCES),
        "allowed_status_transitions": {
            status: _ordered_transition_targets(ALLOWED_STATUS_TRANSITIONS[status])
            for status in constants.JOB_STATUSES
        },
        "endpoints": ENDPOINTS,
        "schemas": {
            model.__name__: model.model_json_schema()
            for model in SCHEMA_MODELS
        },
    }


def write_api_contract() -> Path:
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(
        json.dumps(build_api_contract(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return CONTRACT_PATH


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output_path = write_api_contract()
    logger.info("Wrote %s", output_path.relative_to(REPOSITORY_ROOT))


if __name__ == "__main__":
    main()
