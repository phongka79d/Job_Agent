"""Tests for compiled extraction graph and public service entrypoints."""

import pytest
from unittest.mock import patch

from app.agents.schemas import JobAgentState
from app.services import (
    run_extraction_graph,
    extract_from_raw_text,
    extract_from_url,
    FakeJobExtractionClient,
    LLMValidationError,
    LLMProviderError,
)
from app.agents.graph import route_after_prepare, route_after_extract, route_after_repair
from app.core.config import settings


@pytest.mark.asyncio
async def test_run_extraction_graph_success():
    client = FakeJobExtractionClient()
    initial_state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "raw_text": "Looking for a python developer.",
    }
    
    final_state = await run_extraction_graph(initial_state, llm_client=client)
    assert final_state["batch_id"] == "b1"
    assert final_state["parse_status"] == "success"
    assert final_state["extraction_status"] == "success"
    assert final_state["jd_status"] == "full_jd"
    assert final_state["should_score_similarity"] is True
    assert final_state["extracted_job"]["title"] == "Fake Software Engineer"
    assert len(client.extract_calls) == 1
    assert len(client.repair_calls) == 0


def test_graph_routes_reject_statuses_outside_phase_one_constants():
    with pytest.raises(ValueError, match="parse_status must be one of"):
        route_after_prepare({"parse_status": "invalid_parse_status"})  # type: ignore

    with pytest.raises(ValueError, match="extraction_status must be one of"):
        route_after_extract({"extraction_status": "invalid_extraction_status"})  # type: ignore

    with pytest.raises(ValueError, match="extraction_status must be one of"):
        route_after_repair({"extraction_status": "invalid_extraction_status"})  # type: ignore


@pytest.mark.asyncio
async def test_run_extraction_graph_retry_success():
    client = FakeJobExtractionClient()
    # First try validation fails, second try repair succeeds
    client.add_extract_response(
        LLMValidationError("Invalid format", invalid_output="{}")
    )
    initial_state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "raw_text": "Looking for a python developer.",
    }

    with patch.object(settings, "MAX_RETRY_PER_JOB", 1):
        final_state = await run_extraction_graph(initial_state, llm_client=client)
        assert final_state["batch_id"] == "b1"
        assert final_state["parse_status"] == "success"
        assert final_state["extraction_status"] == "retried"
        assert final_state["jd_status"] == "full_jd"
        assert final_state["should_score_similarity"] is True
        assert len(client.extract_calls) == 1
        assert len(client.repair_calls) == 1


@pytest.mark.asyncio
async def test_run_extraction_graph_retry_failure():
    client = FakeJobExtractionClient()
    # Both fail validation
    client.add_extract_response(
        LLMValidationError("Invalid format", invalid_output="{}")
    )
    client.add_repair_response(
        LLMValidationError("Still invalid format", invalid_output="{}")
    )
    initial_state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "raw_text": "Looking for a python developer.",
    }

    with patch.object(settings, "MAX_RETRY_PER_JOB", 1):
        final_state = await run_extraction_graph(initial_state, llm_client=client)
        assert final_state["batch_id"] == "b1"
        assert final_state["parse_status"] == "success"
        assert final_state["extraction_status"] == "failed"
        assert final_state["jd_status"] == "unclear"
        assert final_state["should_score_similarity"] is False
        assert "Repair validation failed" in final_state["extracted_job"]["extraction_notes"]
        assert len(client.extract_calls) == 1
        assert len(client.repair_calls) == 1


@pytest.mark.asyncio
async def test_run_extraction_graph_provider_failure():
    client = FakeJobExtractionClient()
    # Provider error (e.g. rate limit) during extraction - no retry
    client.add_extract_response(
        LLMProviderError("Rate limit reached")
    )
    initial_state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "raw_text": "Looking for a python developer.",
    }

    final_state = await run_extraction_graph(initial_state, llm_client=client)
    assert final_state["batch_id"] == "b1"
    assert final_state["parse_status"] == "success"
    assert final_state["extraction_status"] == "failed"
    assert final_state["jd_status"] == "unclear"
    assert final_state["should_score_similarity"] is False
    assert "Rate limit reached" in final_state["extracted_job"]["extraction_notes"]
    assert len(client.extract_calls) == 1
    assert len(client.repair_calls) == 0


@pytest.mark.asyncio
async def test_extract_from_raw_text():
    client = FakeJobExtractionClient()
    final_state = await extract_from_raw_text(
        batch_id="b2",
        role_profile_id="rp2",
        raw_text="This is a test raw text for extraction.",
        source_url="http://manual-post.com",
        llm_client=client,
    )
    assert final_state["batch_id"] == "b2"
    assert final_state["role_profile_id"] == "rp2"
    assert final_state["input_source"] == "manual_text"
    assert final_state["source_url"] == "http://manual-post.com"
    assert final_state["parse_status"] == "success"
    assert final_state["extraction_status"] == "success"
    assert final_state["extracted_job"]["source_platform"] == "manual_text"


@pytest.mark.asyncio
async def test_extract_from_url_success():
    client = FakeJobExtractionClient()
    
    # We mock prepare_url_content inside nodes or in extraction_service
    # Since extraction_service.py has prepare_url_content that performs httpx call,
    # let's mock prepare_url_content to return a success state.
    with patch("app.agents.nodes.prepare_url_content") as mock_prep:
        mock_prep.return_value = {
            "batch_id": "b3",
            "role_profile_id": "rp3",
            "input_source": "manual_url",
            "source_url": "http://google.com/careers/123",
            "clean_text": "Google is looking for a software engineer.",
            "raw_content_hash": "dummy_hash",
            "parse_status": "success",
        }
        
        final_state = await extract_from_url(
            batch_id="b3",
            role_profile_id="rp3",
            source_url="http://google.com/careers/123",
            input_source="manual_url",
            llm_client=client,
        )
        
        assert final_state["batch_id"] == "b3"
        assert final_state["role_profile_id"] == "rp3"
        assert final_state["input_source"] == "manual_url"
        assert final_state["source_url"] == "http://google.com/careers/123"
        assert final_state["parse_status"] == "success"
        assert final_state["extraction_status"] == "success"
        assert final_state["extracted_job"]["source_platform"] == "manual_url"


@pytest.mark.asyncio
async def test_extract_from_url_invalid_input_source():
    with pytest.raises(ValueError, match="input_source for extract_from_url must be"):
        await extract_from_url(
            batch_id="b4",
            role_profile_id="rp4",
            source_url="http://invalid.com",
            input_source="manual_text",  # Not allowed here
        )


@pytest.mark.asyncio
async def test_extract_from_url_parser_fallback():
    client = FakeJobExtractionClient()
    
    # Mock prepare_url_content to return needs_manual_input (low content / blocked page)
    # The graph should route immediately to END and skip LLM.
    with patch("app.agents.nodes.prepare_url_content") as mock_prep:
        mock_prep.return_value = {
            "batch_id": "b5",
            "role_profile_id": "rp5",
            "input_source": "manual_url",
            "source_url": "http://short.com",
            "clean_text": "Short JD",
            "raw_content_hash": "dummy_hash",
            "parse_status": "needs_manual_input",
            "extracted_job": {
                "title": None,
                "company": None,
                "location": None,
                "work_mode": "unknown",
                "level": "unknown",
                "employment_type": "unknown",
                "salary": None,
                "responsibilities": None,
                "requirements": None,
                "skills": [],
                "source_url": "http://short.com",
                "source_platform": "manual_url",
                "jd_status": "unclear",
                "should_score_similarity": False,
                "extraction_notes": "URL content was too short or unreliable for extraction",
            },
            "jd_status": "unclear",
            "should_score_similarity": False,
            "extraction_status": None,
            "error_reason": "URL content was too short or unreliable for extraction",
            "user_warning": "Warning message",
        }
        
        final_state = await extract_from_url(
            batch_id="b5",
            role_profile_id="rp5",
            source_url="http://short.com",
            input_source="manual_url",
            llm_client=client,
        )
        
        assert final_state["batch_id"] == "b5"
        assert final_state["parse_status"] == "needs_manual_input"
        assert final_state["extraction_status"] is None  # Never called LLM
        assert final_state["jd_status"] == "unclear"
        assert final_state["should_score_similarity"] is False
        assert final_state["extracted_job"]["extraction_notes"] == "URL content was too short or unreliable for extraction"
        # Verify LLM was never called
        assert len(client.extract_calls) == 0
        assert len(client.repair_calls) == 0
