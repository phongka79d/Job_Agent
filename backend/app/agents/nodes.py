"""LangGraph nodes for the job extraction workflow."""

from typing import Any
from langchain_core.runnables import RunnableConfig

from app.agents.schemas import (
    JobAgentState,
    preserve_required_state,
    score_placeholder_update,
    map_input_source_to_source_platform,
    build_unclear_extraction_failure_update,
)
from app.services.extraction_service import (
    prepare_manual_text,
    prepare_url_content,
    compute_content_hash,
)
from app.services.llm_client import (
    JobExtractionClientProtocol,
    LLMValidationError,
    LLMProviderError,
    OpenAIJobExtractionClient,
)
from app.core.config import settings


def _get_llm_client(config: RunnableConfig | None) -> JobExtractionClientProtocol:
    """Extract LLM client from runnable config, falling back to production client."""
    if config and "configurable" in config and "llm_client" in config["configurable"]:
        return config["configurable"]["llm_client"]
    return OpenAIJobExtractionClient()


def _accumulate_observability(
    state: JobAgentState,
    new_in: int | None,
    new_out: int | None,
    new_cost: float | None,
    new_time: int | None,
) -> dict[str, Any]:
    """Accumulate observability tokens, costs, and elapsed time."""
    res = {}
    
    old_in = state.get("input_tokens")
    if old_in is not None and new_in is not None:
        res["input_tokens"] = old_in + new_in
    else:
        res["input_tokens"] = new_in if new_in is not None else old_in

    old_out = state.get("output_tokens")
    if old_out is not None and new_out is not None:
        res["output_tokens"] = old_out + new_out
    else:
        res["output_tokens"] = new_out if new_out is not None else old_out

    old_cost = state.get("estimated_cost_usd")
    if old_cost is not None and new_cost is not None:
        res["estimated_cost_usd"] = old_cost + new_cost
    else:
        res["estimated_cost_usd"] = new_cost if new_cost is not None else old_cost

    old_time = state.get("extraction_time_ms")
    if old_time is not None and new_time is not None:
        res["extraction_time_ms"] = old_time + new_time
    else:
        res["extraction_time_ms"] = new_time if new_time is not None else old_time

    return res


async def prepare_content(state: JobAgentState, config: RunnableConfig = None) -> JobAgentState:
    """Prepare and clean text or URL content before extraction."""
    update = preserve_required_state(state)
    input_source = state.get("input_source")
    batch_id = state.get("batch_id")
    role_profile_id = state.get("role_profile_id")
    source_url = state.get("source_url")
    raw_text = state.get("raw_text")

    if input_source == "manual_text":
        prepared = prepare_manual_text(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            raw_text=raw_text or "",
            source_url=source_url,
        )
    elif input_source in ("manual_url", "tavily"):
        if not source_url:
            prepared = {
                "parse_status": "failed",
                "error_reason": "source_url is required for URL input sources",
            }
        else:
            prepared = await prepare_url_content(
                batch_id=batch_id,
                role_profile_id=role_profile_id,
                source_url=source_url,
                input_source=input_source,
            )
    elif input_source == "mock":
        clean = state.get("clean_text") or raw_text or ""
        prepared = {
            "source_url": source_url,
            "raw_text": raw_text,
            "clean_text": clean,
            "raw_content_hash": compute_content_hash(clean),
            "parse_status": state.get("parse_status") or "success",
        }
    else:
        prepared = {
            "parse_status": "failed",
            "error_reason": f"Unsupported input source: {input_source}",
        }

    return {**update, **prepared}


async def extract_job(state: JobAgentState, config: RunnableConfig = None) -> JobAgentState:
    """Attempt initial structured job extraction using the LLM client."""
    update = preserve_required_state(state)
    if state.get("parse_status") != "success":
        return update

    clean_text = state.get("clean_text")
    if not clean_text:
        return {
            **update,
            "parse_status": "failed",
            "error_reason": "No clean text available for extraction",
        }

    source_url = state.get("source_url")
    source_platform = map_input_source_to_source_platform(state["input_source"])
    client = _get_llm_client(config)

    try:
        job_post = await client.extract_job(
            clean_text=clean_text,
            source_url=source_url,
            source_platform=source_platform,
        )
        return {
            **update,
            "extracted_job": job_post.model_dump(),
            "jd_status": job_post.jd_status,
            "should_score_similarity": job_post.should_score_similarity,
            "extraction_status": "success",
            "input_tokens": getattr(job_post, "_input_tokens", None),
            "output_tokens": getattr(job_post, "_output_tokens", None),
            "estimated_cost_usd": getattr(job_post, "_estimated_cost_usd", None),
            "extraction_time_ms": getattr(job_post, "_extraction_time_ms", None),
        }
    except LLMValidationError as e:
        # Route first validation failure to repair only when retry cap allows
        limit_retry = settings.MAX_RETRY_PER_JOB >= 1
        if limit_retry:
            return {
                **update,
                "extraction_status": None,  # Signals repair is needed
                "error_reason": str(e),
                "_invalid_output": e.invalid_output,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "estimated_cost_usd": e.estimated_cost_usd,
                "extraction_time_ms": e.extraction_time_ms,
            }
        else:
            return {
                **update,
                "extraction_status": "failed",
                "error_reason": f"Validation failed and retries disabled: {e}",
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "estimated_cost_usd": e.estimated_cost_usd,
                "extraction_time_ms": e.extraction_time_ms,
            }
    except LLMProviderError as e:
        # Provider failures go straight to failure without retry
        return {
            **update,
            "extraction_status": "failed",
            "error_reason": str(e),
            "extraction_time_ms": e.extraction_time_ms,
        }


async def repair_job(state: JobAgentState, config: RunnableConfig = None) -> JobAgentState:
    """Attempt to repair invalid extraction output once using the LLM client."""
    update = preserve_required_state(state)
    if state.get("parse_status") != "success":
        return update

    clean_text = state.get("clean_text")
    if not clean_text:
        return update

    invalid_output = state.get("_invalid_output") or state.get("error_reason") or ""
    validation_error = state.get("error_reason") or "Validation failed"
    source_url = state.get("source_url")
    source_platform = map_input_source_to_source_platform(state["input_source"])
    client = _get_llm_client(config)

    try:
        job_post = await client.repair_job(
            clean_text=clean_text,
            invalid_output=invalid_output,
            validation_error=validation_error,
            source_url=source_url,
            source_platform=source_platform,
        )
        return {
            **update,
            "extracted_job": job_post.model_dump(),
            "jd_status": job_post.jd_status,
            "should_score_similarity": job_post.should_score_similarity,
            "extraction_status": "retried",
            **_accumulate_observability(
                state,
                job_post._input_tokens,
                job_post._output_tokens,
                job_post._estimated_cost_usd,
                job_post._extraction_time_ms,
            ),
        }
    except LLMValidationError as e:
        return {
            **update,
            "extraction_status": "failed",
            "error_reason": f"Repair validation failed: {e}",
            **_accumulate_observability(
                state,
                e.input_tokens,
                e.output_tokens,
                e.estimated_cost_usd,
                e.extraction_time_ms,
            ),
        }
    except LLMProviderError as e:
        return {
            **update,
            "extraction_status": "failed",
            "error_reason": f"Repair provider failed: {e}",
            **_accumulate_observability(
                state,
                None,
                None,
                None,
                e.extraction_time_ms,
            ),
        }


async def classify_jd(state: JobAgentState, config: RunnableConfig = None) -> JobAgentState:
    """Classify/normalize JD status and derive should_score_similarity."""
    update = preserve_required_state(state)
    extracted_job = state.get("extracted_job")

    if not extracted_job:
        jd_status = "unclear"
        should_score = False
    else:
        jd_status = extracted_job.get("jd_status")
        if jd_status not in ("full_jd", "partial_jd"):
            should_score = False
        else:
            should_score = True

    new_state = {
        **update,
        "jd_status": jd_status,
        "should_score_similarity": should_score,
    }

    if extracted_job:
        updated_job = dict(extracted_job)
        updated_job["jd_status"] = jd_status
        updated_job["should_score_similarity"] = should_score
        new_state["extracted_job"] = updated_job

    return new_state


async def mark_unclear(state: JobAgentState, config: RunnableConfig = None) -> JobAgentState:
    """Build the complete unclear fallback state after retry or provider failure."""
    error_reason = state.get("error_reason") or "LLM extraction failed"
    update = build_unclear_extraction_failure_update(
        state,
        extraction_note=error_reason,
        error_reason=error_reason,
    )

    # Populate observability fields or explicit None
    update["input_tokens"] = state.get("input_tokens")
    update["output_tokens"] = state.get("output_tokens")
    update["estimated_cost_usd"] = state.get("estimated_cost_usd")
    update["extraction_time_ms"] = state.get("extraction_time_ms")

    # Retain input preparation contexts
    update["source_url"] = state.get("source_url")
    update["clean_text"] = state.get("clean_text")
    update["raw_text"] = state.get("raw_text")
    update["raw_content_hash"] = state.get("raw_content_hash")

    return update
