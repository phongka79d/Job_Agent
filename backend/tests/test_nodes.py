"""Tests for LangGraph extraction workflow nodes and graph routing."""

import pytest
from unittest.mock import patch
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from app.agents.schemas import JobAgentState
from app.agents.nodes import (
    prepare_content,
    extract_job,
    repair_job,
    classify_jd,
    mark_unclear,
)
from app.services.llm_client import (
    LLMValidationError,
    LLMProviderError,
)
from app.core.config import settings
from tests.fakes import ScriptedJobExtractionClient


# Helper to build a test graph compiled with the nodes
def get_test_graph():
    workflow = StateGraph(JobAgentState)
    workflow.add_node("prepare_content", prepare_content)
    workflow.add_node("extract_job", extract_job)
    workflow.add_node("repair_job", repair_job)
    workflow.add_node("classify_jd", classify_jd)
    workflow.add_node("mark_unclear", mark_unclear)

    workflow.set_entry_point("prepare_content")

    def route_after_prepare(state: JobAgentState):
        if state.get("parse_status") == "success":
            return "extract_job"
        return "classify_jd"

    def route_after_extract(state: JobAgentState):
        status = state.get("extraction_status")
        if status == "success":
            return "classify_jd"
        elif status == "failed":
            return "mark_unclear"
        else:
            return "repair_job"

    def route_after_repair(state: JobAgentState):
        status = state.get("extraction_status")
        if status in ("success", "retried"):
            return "classify_jd"
        return "mark_unclear"

    workflow.add_conditional_edges("prepare_content", route_after_prepare)
    workflow.add_conditional_edges("extract_job", route_after_extract)
    workflow.add_conditional_edges("repair_job", route_after_repair)
    
    workflow.add_edge("classify_jd", END)
    workflow.add_edge("mark_unclear", END)

    return workflow.compile()


@pytest.mark.asyncio
async def test_prepare_content_manual_text():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "raw_text": "Need a senior python developer.",
        "source_url": None,
    }
    res = await prepare_content(state)
    assert res["batch_id"] == "b1"
    assert res["role_profile_id"] == "rp1"
    assert res["input_source"] == "manual_text"
    assert res["parse_status"] == "success"
    assert res["clean_text"] == "Need a senior python developer."
    assert res["raw_content_hash"] is not None


@pytest.mark.asyncio
async def test_extract_job_success():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "parse_status": "success",
        "clean_text": "Valid job description content.",
    }
    
    client = ScriptedJobExtractionClient()
    config = RunnableConfig(configurable={"llm_client": client})

    res = await extract_job(state, config=config)
    assert res["extraction_status"] == "success"
    assert res["extracted_job"] is not None
    assert res["extracted_job"]["title"] == "Test Engineer"
    assert res["jd_status"] == "full_jd"
    assert res["should_score_similarity"] is True
    assert res["input_tokens"] == 100
    assert res["output_tokens"] == 50
    assert res["estimated_cost_usd"] == 0.0001
    assert res["extraction_time_ms"] == 10


@pytest.mark.asyncio
async def test_extract_job_validation_error_with_retry():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "parse_status": "success",
        "clean_text": "Invalid content that triggers schema error.",
    }

    client = ScriptedJobExtractionClient()
    client.add_extract_response(LLMValidationError(
        "Schema failed",
        invalid_output="{}",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.00001,
        extraction_time_ms=5,
    ))
    config = RunnableConfig(configurable={"llm_client": client})

    with patch.object(settings, "MAX_RETRY_PER_JOB", 1):
        res = await extract_job(state, config=config)
        assert res["extraction_status"] is None  # Signals retry
        assert res["error_reason"] == "Schema failed"
        assert res["_invalid_output"] == "{}"
        assert res["input_tokens"] == 10


@pytest.mark.asyncio
async def test_extract_job_validation_error_no_retry():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "parse_status": "success",
        "clean_text": "Invalid content.",
    }

    client = ScriptedJobExtractionClient()
    client.add_extract_response(LLMValidationError(
        "Schema failed",
        invalid_output="{}",
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.00001,
        extraction_time_ms=5,
    ))
    config = RunnableConfig(configurable={"llm_client": client})

    with patch.object(settings, "MAX_RETRY_PER_JOB", 0):
        res = await extract_job(state, config=config)
        assert res["extraction_status"] == "failed"
        assert "Validation failed and retries disabled" in res["error_reason"]


@pytest.mark.asyncio
async def test_extract_job_provider_error():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "parse_status": "success",
        "clean_text": "Valid content.",
    }

    client = ScriptedJobExtractionClient()
    client.add_extract_response(LLMProviderError("API Key Expired", extraction_time_ms=8))
    config = RunnableConfig(configurable={"llm_client": client})

    res = await extract_job(state, config=config)
    assert res["extraction_status"] == "failed"
    assert res["error_reason"] == "API Key Expired"
    assert res["extraction_time_ms"] == 8


@pytest.mark.asyncio
async def test_repair_job_success():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "parse_status": "success",
        "clean_text": "Content",
        "input_tokens": 10,
        "output_tokens": 5,
        "estimated_cost_usd": 0.00001,
        "extraction_time_ms": 5,
        "_invalid_output": "{}",
        "error_reason": "Schema failed",
    }

    client = ScriptedJobExtractionClient()
    config = RunnableConfig(configurable={"llm_client": client})

    res = await repair_job(state, config=config)
    assert res["extraction_status"] == "retried"
    assert res["extracted_job"] is not None
    # Observability should accumulate
    assert res["input_tokens"] == 10 + 120
    assert res["output_tokens"] == 5 + 60
    assert res["estimated_cost_usd"] == 0.00001 + 0.00015
    assert res["extraction_time_ms"] == 5 + 15


@pytest.mark.asyncio
async def test_repair_job_failure():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "parse_status": "success",
        "clean_text": "Content",
        "input_tokens": 10,
        "output_tokens": 5,
        "estimated_cost_usd": 0.00001,
        "extraction_time_ms": 5,
    }

    client = ScriptedJobExtractionClient()
    client.add_repair_response(LLMValidationError(
        "Still invalid",
        invalid_output="{}",
        input_tokens=20,
        output_tokens=10,
        estimated_cost_usd=0.00002,
        extraction_time_ms=6,
    ))
    config = RunnableConfig(configurable={"llm_client": client})

    res = await repair_job(state, config=config)
    assert res["extraction_status"] == "failed"
    assert "Repair validation failed" in res["error_reason"]
    assert res["input_tokens"] == 10 + 20
    assert res["output_tokens"] == 5 + 10
    assert res["estimated_cost_usd"] == 0.00001 + 0.00002
    assert res["extraction_time_ms"] == 5 + 6


@pytest.mark.asyncio
async def test_classify_jd():
    state_scorable: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "extracted_job": {"jd_status": "full_jd", "should_score_similarity": False},
    }
    res = await classify_jd(state_scorable)
    assert res["jd_status"] == "full_jd"
    assert res["should_score_similarity"] is True
    assert res["extracted_job"]["should_score_similarity"] is True

    state_non_scorable: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "extracted_job": {"jd_status": "no_jd", "should_score_similarity": True},
    }
    res2 = await classify_jd(state_non_scorable)
    assert res2["jd_status"] == "no_jd"
    assert res2["should_score_similarity"] is False
    assert res2["extracted_job"]["should_score_similarity"] is False


@pytest.mark.asyncio
async def test_classify_jd_rejects_status_outside_phase_one_constants():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "extracted_job": {
            "jd_status": "invalid_jd_status",
            "should_score_similarity": False,
        },
    }

    with pytest.raises(ValueError, match="jd_status must be one of"):
        await classify_jd(state)


@pytest.mark.asyncio
async def test_mark_unclear():
    state: JobAgentState = {
        "batch_id": "b1",
        "role_profile_id": "rp1",
        "input_source": "manual_text",
        "source_url": "http://example.com",
        "clean_text": "Parsed raw text.",
        "input_tokens": 15,
        "output_tokens": 8,
        "estimated_cost_usd": 0.00002,
        "extraction_time_ms": 7,
        "error_reason": "Failed extraction twice",
    }
    res = await mark_unclear(state)
    assert res["batch_id"] == "b1"
    assert res["role_profile_id"] == "rp1"
    assert res["input_source"] == "manual_text"
    assert res["parse_status"] == "success"
    assert res["extraction_status"] == "failed"
    assert res["jd_status"] == "unclear"
    assert res["should_score_similarity"] is False
    assert res["extracted_job"]["jd_status"] == "unclear"
    assert res["extracted_job"]["should_score_similarity"] is False
    assert res["extracted_job"]["extraction_notes"] == "Failed extraction twice"
    assert res["input_tokens"] == 15
    assert res["output_tokens"] == 8
    assert res["estimated_cost_usd"] == 0.00002
    assert res["extraction_time_ms"] == 7
    # Score fields must be None
    assert res["embedding_text"] is None
    assert res["final_score"] is None


# Compiled Graph Terminal Path Tests
@pytest.mark.asyncio
async def test_graph_path_success():
    graph = get_test_graph()
    client = ScriptedJobExtractionClient()
    config = RunnableConfig(configurable={"llm_client": client})

    initial_state: JobAgentState = {
        "batch_id": "b_success",
        "role_profile_id": "rp_success",
        "input_source": "manual_text",
        "raw_text": "This is a real job description text.",
    }

    final_state = await graph.ainvoke(initial_state, config=config)
    assert final_state["batch_id"] == "b_success"
    assert final_state["parse_status"] == "success"
    assert final_state["extraction_status"] == "success"
    assert final_state["jd_status"] == "full_jd"
    assert final_state["should_score_similarity"] is True
    assert final_state["extracted_job"]["title"] == "Test Engineer"


@pytest.mark.asyncio
async def test_graph_path_retry_success():
    graph = get_test_graph()
    client = ScriptedJobExtractionClient()
    # First extract call fails validation, repair succeeds
    client.add_extract_response(LLMValidationError("First try failed schema validation", invalid_output="{}"))
    config = RunnableConfig(configurable={"llm_client": client})

    initial_state: JobAgentState = {
        "batch_id": "b_retry_success",
        "role_profile_id": "rp_retry_success",
        "input_source": "manual_text",
        "raw_text": "Job description text needing repair.",
    }

    with patch.object(settings, "MAX_RETRY_PER_JOB", 1):
        final_state = await graph.ainvoke(initial_state, config=config)
        assert final_state["batch_id"] == "b_retry_success"
        assert final_state["parse_status"] == "success"
        assert final_state["extraction_status"] == "retried"
        assert final_state["jd_status"] == "full_jd"
        assert final_state["should_score_similarity"] is True


@pytest.mark.asyncio
async def test_graph_path_retry_failure():
    graph = get_test_graph()
    client = ScriptedJobExtractionClient()
    # Both initial and repair calls fail validation
    client.add_extract_response(LLMValidationError("First try failed", invalid_output="{}"))
    client.add_repair_response(LLMValidationError("Repair try failed", invalid_output="{}"))
    config = RunnableConfig(configurable={"llm_client": client})

    initial_state: JobAgentState = {
        "batch_id": "b_retry_fail",
        "role_profile_id": "rp_retry_fail",
        "input_source": "manual_text",
        "raw_text": "Job description text that cannot be repaired.",
    }

    with patch.object(settings, "MAX_RETRY_PER_JOB", 1):
        final_state = await graph.ainvoke(initial_state, config=config)
        assert final_state["batch_id"] == "b_retry_fail"
        assert final_state["parse_status"] == "success"
        assert final_state["extraction_status"] == "failed"
        assert final_state["jd_status"] == "unclear"
        assert final_state["should_score_similarity"] is False
        assert final_state["extracted_job"]["jd_status"] == "unclear"
        assert "Repair validation failed" in final_state["extracted_job"]["extraction_notes"]


@pytest.mark.asyncio
async def test_graph_path_provider_failure():
    graph = get_test_graph()
    client = ScriptedJobExtractionClient()
    client.add_extract_response(LLMProviderError("Timeout reaching LLM provider"))
    config = RunnableConfig(configurable={"llm_client": client})

    initial_state: JobAgentState = {
        "batch_id": "b_prov_fail",
        "role_profile_id": "rp_prov_fail",
        "input_source": "manual_text",
        "raw_text": "Job description.",
    }

    final_state = await graph.ainvoke(initial_state, config=config)
    assert final_state["batch_id"] == "b_prov_fail"
    assert final_state["parse_status"] == "success"
    assert final_state["extraction_status"] == "failed"
    assert final_state["jd_status"] == "unclear"
    assert final_state["should_score_similarity"] is False
    assert "Timeout reaching LLM provider" in final_state["extracted_job"]["extraction_notes"]


@pytest.mark.asyncio
async def test_graph_path_parser_fallback():
    graph = get_test_graph()
    
    # We trigger parser fallback (needs_manual_input) by providing an empty raw_text URL or low-content URL.
    # To test easily without network, we can set input_source = "manual_url" and mock the httpx client stream call,
    # or we can test prepare_url_content's fallback by using a short URL content.
    # But even simpler, let's test with a mocked prepare_url_content or just mock HTTP.
    # Actually, we can use manual_url, and patch the httpx Client.stream to return low content.
    # Let's mock prepare_url_content in prepare_content node, or mock httpx in extraction_service.
    
    # Let's patch `prepare_url_content` to return needs_manual_input directly.
    with patch("app.agents.nodes.prepare_url_content") as mock_prep:
        mock_prep.return_return_value = None # not used
        # We will mock it to return the exact manual input state
        mock_prep.return_value = {
            "batch_id": "b_parse_fail",
            "role_profile_id": "rp_parse_fail",
            "input_source": "manual_url",
            "source_url": "http://short.com",
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

        initial_state: JobAgentState = {
            "batch_id": "b_parse_fail",
            "role_profile_id": "rp_parse_fail",
            "input_source": "manual_url",
            "source_url": "http://short.com",
        }

        final_state = await graph.ainvoke(initial_state)
        assert final_state["batch_id"] == "b_parse_fail"
        assert final_state["parse_status"] == "needs_manual_input"
        assert final_state["extraction_status"] is None  # Never attempted LLM
        assert final_state["jd_status"] == "unclear"
        assert final_state["should_score_similarity"] is False
        assert final_state["extracted_job"]["extraction_notes"] == "URL content was too short or unreliable for extraction"
