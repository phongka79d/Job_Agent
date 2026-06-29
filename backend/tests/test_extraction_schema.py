"""Tests for extraction schemas, mapping helpers, and fallback contracts."""

import pytest
from pydantic import ValidationError

from app.core import constants
from app.agents.schemas import (
    JobAgentState,
    JobPostExtract,
    map_input_source_to_source_platform,
    preserve_required_state,
    score_placeholder_update,
    build_unclear_job,
    build_unclear_extraction_failure_update,
    validate_parse_status,
    validate_extraction_status,
    validate_jd_status,
)


def test_job_post_extract_valid():
    """Assert valid JobPostExtract construct and model_dump works with default fields."""
    job = JobPostExtract(
        title="Software Engineer",
        company="Tech Corp",
        source_platform="manual_text",
        jd_status="full_jd",
        should_score_similarity=True,
    )
    
    assert job.title == "Software Engineer"
    assert job.company == "Tech Corp"
    assert job.work_mode == "unknown"  # default
    assert job.level == "unknown"  # default
    assert job.employment_type == "unknown"  # default
    assert job.source_platform == "manual_text"
    assert job.jd_status == "full_jd"
    assert job.should_score_similarity is True
    
    dumped = job.model_dump()
    assert dumped["work_mode"] == "unknown"
    assert dumped["level"] == "unknown"
    assert dumped["employment_type"] == "unknown"
    assert dumped["skills"] == []


def test_job_post_extract_invalid_source_platform():
    """Assert invalid source_platform raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        JobPostExtract(
            title="Engineer",
            company="Tech",
            source_platform="invalid_platform",
            jd_status="full_jd",
            should_score_similarity=True,
        )
    assert "source_platform" in str(exc_info.value)


def test_job_post_extract_invalid_jd_status():
    """Assert invalid jd_status raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        JobPostExtract(
            title="Engineer",
            company="Tech",
            source_platform="manual_text",
            jd_status="invalid_jd_status",
            should_score_similarity=True,
        )
    assert "jd_status" in str(exc_info.value)


@pytest.mark.parametrize(
    "input_source,expected_platform",
    [
        ("tavily", "tavily"),
        ("manual_url", "manual_url"),
        ("manual_text", "manual_text"),
        ("mock", "mock"),
    ],
)
def test_source_mapping_valid(input_source: str, expected_platform: str):
    """Prove that map_input_source_to_source_platform performs correctly for all allowed inputs."""
    assert map_input_source_to_source_platform(input_source) == expected_platform


def test_source_mapping_invalid():
    """Assert mapping helper rejects input sources outside the constants.INPUT_SOURCES."""
    with pytest.raises(ValueError) as exc_info:
        map_input_source_to_source_platform("invalid_input_source")
    assert "input_source must be one of" in str(exc_info.value)


@pytest.mark.parametrize("parse_status", constants.PARSE_STATUSES)
def test_validate_parse_status_accepts_phase_one_constants(parse_status: str):
    assert validate_parse_status(parse_status) == parse_status


@pytest.mark.parametrize("extraction_status", constants.EXTRACTION_STATUSES)
def test_validate_extraction_status_accepts_phase_one_constants(extraction_status: str):
    assert validate_extraction_status(extraction_status) == extraction_status


@pytest.mark.parametrize("jd_status", constants.JD_STATUSES)
def test_validate_jd_status_accepts_phase_one_constants(jd_status: str):
    assert validate_jd_status(jd_status) == jd_status


def test_status_validation_helpers_reject_values_outside_phase_one_constants():
    with pytest.raises(ValueError, match="parse_status must be one of"):
        validate_parse_status("invalid_parse_status")

    with pytest.raises(ValueError, match="extraction_status must be one of"):
        validate_extraction_status("invalid_extraction_status")

    with pytest.raises(ValueError, match="jd_status must be one of"):
        validate_jd_status("invalid_jd_status")


def test_preserve_required_state():
    """Assert preserve_required_state copies correct identifiers and validates input_source."""
    state: JobAgentState = {
        "batch_id": "batch-123",
        "role_profile_id": "role-456",
        "input_source": "manual_text",
        "clean_text": "Some text",
        "jd_status": "full_jd",
    }
    preserved = preserve_required_state(state)
    assert preserved == {
        "batch_id": "batch-123",
        "role_profile_id": "role-456",
        "input_source": "manual_text",
    }
    
    # Test validation of input_source within preserve_required_state
    invalid_state: JobAgentState = {
        "batch_id": "batch-123",
        "role_profile_id": "role-456",
        "input_source": "invalid_source",  # type: ignore
    }
    with pytest.raises(ValueError):
        preserve_required_state(invalid_state)


def test_score_placeholder_update():
    """Assert score_placeholder_update populates all score fields as None and preserves required state."""
    state: JobAgentState = {
        "batch_id": "batch-789",
        "role_profile_id": "role-012",
        "input_source": "mock",
        "final_score": 0.95,
        "embedding_similarity": 0.88,
    }
    updated = score_placeholder_update(state)
    
    assert updated["batch_id"] == "batch-789"
    assert updated["role_profile_id"] == "role-012"
    assert updated["input_source"] == "mock"
    
    # Assert score fields are set to None
    score_fields = [
        "embedding_text",
        "embedding_similarity",
        "skill_overlap_score",
        "location_match_score",
        "level_match_score",
        "base_score",
        "jd_confidence_multiplier",
        "final_score",
        "final_score_percent",
    ]
    for field in score_fields:
        assert updated[field] is None  # type: ignore


def test_build_unclear_job():
    """Assert build_unclear_job produces all JobPostExtract defaults with unclear status."""
    job_dict = build_unclear_job(
        source_url="http://example.com/job",
        source_platform="manual_url",
        extraction_note="Failed extraction",
    )
    
    # Check fallback defaults
    assert job_dict["title"] is None
    assert job_dict["company"] is None
    assert job_dict["location"] is None
    assert job_dict["work_mode"] == "unknown"
    assert job_dict["level"] == "unknown"
    assert job_dict["employment_type"] == "unknown"
    assert job_dict["salary"] is None
    assert job_dict["responsibilities"] is None
    assert job_dict["requirements"] is None
    assert job_dict["skills"] == []
    assert job_dict["source_url"] == "http://example.com/job"
    assert job_dict["source_platform"] == "manual_url"
    assert job_dict["jd_status"] == "unclear"
    assert job_dict["should_score_similarity"] is False
    assert job_dict["extraction_notes"] == "Failed extraction"


def test_build_unclear_job_invalid_platform():
    """Assert build_unclear_job rejects platforms outside mapping."""
    with pytest.raises(ValueError) as exc_info:
        build_unclear_job(
            source_url="http://example.com/job",
            source_platform="job_board",  # Valid constant, but not in input_source mapping!
            extraction_note="Fail",
        )
    assert "source_platform must be produced by the approved Plan 2 source mapping" in str(exc_info.value)


def test_build_unclear_extraction_failure_update():
    """Assert complete state update for post-parse extraction failure."""
    state: JobAgentState = {
        "batch_id": "batch-321",
        "role_profile_id": "role-654",
        "input_source": "manual_url",
        "source_url": "http://example.com/job",
    }
    
    update = build_unclear_extraction_failure_update(
        state,
        extraction_note="LLM failed",
        error_reason="JSON invalid",
    )
    
    assert update["batch_id"] == "batch-321"
    assert update["role_profile_id"] == "role-654"
    assert update["input_source"] == "manual_url"
    
    assert update["parse_status"] == "success"
    assert update["extraction_status"] == "failed"
    assert update["jd_status"] == "unclear"
    assert update["should_score_similarity"] is False
    assert update["error_reason"] == "JSON invalid"
    
    extracted_job = update["extracted_job"]
    assert extracted_job is not None
    assert extracted_job["jd_status"] == "unclear"
    assert extracted_job["should_score_similarity"] is False
    assert extracted_job["source_platform"] == "manual_url"
    assert extracted_job["extraction_notes"] == "LLM failed"
    
    # Assert score fields are set to None
    score_fields = [
        "embedding_text",
        "embedding_similarity",
        "skill_overlap_score",
        "location_match_score",
        "level_match_score",
        "base_score",
        "jd_confidence_multiplier",
        "final_score",
        "final_score_percent",
    ]
    for field in score_fields:
        assert update[field] is None  # type: ignore
