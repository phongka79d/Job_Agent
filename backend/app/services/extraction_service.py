"""Deterministic input preparation helpers for job extraction."""

import hashlib
import re
from typing import Literal
from urllib.parse import urlparse

import httpx
import trafilatura

from app.agents.schemas import (
    JobAgentState,
    build_unclear_job,
    map_input_source_to_source_platform,
    score_placeholder_update,
)
from app.core.config import settings
from app.services.llm_client import JobExtractionClientProtocol


_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\r\n]+")
_MIN_RELIABLE_CLEAN_CHARS = 150
_UNRELIABLE_EXTRACTION_NOTE = "URL content was too short or unreliable for extraction"
MANUAL_INPUT_WARNING = (
    "We could not extract enough job content from this URL.\n"
    "The page may require JavaScript rendering, login, or cookie acceptance.\n"
    "Please paste the job description text manually."
)
_LOW_SIGNAL_LINES = {
    "accept all cookies",
    "cookie settings",
    "privacy policy",
    "terms of service",
    "terms of use",
    "sign in",
    "log in",
    "create account",
    "subscribe to our newsletter",
}
_UNRELIABLE_PAGE_SIGNALS = (
    "enable javascript",
    "please enable javascript",
    "javascript is disabled",
    "sign in to view",
    "sign in to continue",
    "log in to view",
    "log in to continue",
    "login to view",
    "login to continue",
    "accept cookies",
    "cookie acceptance",
    "checking your browser",
    "access denied",
)


def _failed_url_state(
    *,
    batch_id: str,
    role_profile_id: str,
    source_url: str,
    input_source: str,
    error_reason: str,
) -> JobAgentState:
    return {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": input_source,
        "source_url": source_url,
        "raw_text": None,
        "clean_text": None,
        "raw_content_hash": None,
        "parse_status": "failed",
        "error_reason": error_reason,
    }


def _manual_input_url_state(
    *,
    batch_id: str,
    role_profile_id: str,
    source_url: str,
    input_source: str,
    clean_text: str | None,
) -> JobAgentState:
    base_state: JobAgentState = {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": input_source,
    }
    source_platform = map_input_source_to_source_platform(input_source)
    return {
        **score_placeholder_update(base_state),
        "source_url": source_url,
        "raw_text": None,
        "clean_text": clean_text,
        "raw_content_hash": compute_content_hash(clean_text),
        "parse_status": "needs_manual_input",
        "extracted_job": build_unclear_job(
            source_url=source_url,
            source_platform=source_platform,
            extraction_note=_UNRELIABLE_EXTRACTION_NOTE,
        ),
        "jd_status": "unclear",
        "should_score_similarity": False,
        "extraction_status": None,
        "error_reason": _UNRELIABLE_EXTRACTION_NOTE,
        "user_warning": MANUAL_INPUT_WARNING,
        "input_tokens": None,
        "output_tokens": None,
        "estimated_cost_usd": None,
        "extraction_time_ms": None,
    }


def bound_raw_text(raw_text: str) -> str:
    """Apply the configured raw-input limit before further processing."""

    return raw_text[: settings.MAX_RAW_TEXT_CHARS]


def truncate_clean_text(clean_text: str) -> str:
    """Bound clean text at a readable boundary when practical."""

    limit = settings.MAX_CLEAN_TEXT_CHARS
    if len(clean_text) <= limit:
        return clean_text

    signal_text = "\n".join(
        line
        for line in clean_text.splitlines()
        if line.casefold() not in _LOW_SIGNAL_LINES
    ).strip()
    if signal_text:
        clean_text = signal_text
    if len(clean_text) <= limit:
        return clean_text

    bounded = clean_text[:limit].rstrip()
    minimum_boundary = limit // 2
    boundary = max(
        bounded.rfind("\n\n"),
        bounded.rfind("\n"),
        bounded.rfind(" "),
    )
    if boundary >= minimum_boundary:
        bounded = bounded[:boundary].rstrip()
    return bounded


def clean_text_content(raw_text: str) -> str | None:
    """Normalize whitespace while preserving meaningful line boundaries."""

    bounded_raw_text = bound_raw_text(raw_text)
    normalized_lines: list[str] = []
    previous_line_was_blank = False

    for line in bounded_raw_text.splitlines():
        normalized_line = _HORIZONTAL_WHITESPACE.sub(" ", line).strip()
        if normalized_line:
            normalized_lines.append(normalized_line)
            previous_line_was_blank = False
        elif normalized_lines and not previous_line_was_blank:
            normalized_lines.append("")
            previous_line_was_blank = True

    normalized_text = "\n".join(normalized_lines).strip()
    if not normalized_text:
        return None

    clean_text = truncate_clean_text(normalized_text)
    return clean_text or None


def compute_content_hash(clean_text: str | None) -> str | None:
    """Return a stable SHA-256 hash for non-empty clean content."""

    if not clean_text:
        return None
    return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()


def is_unreliable_extraction(clean_text: str | None) -> bool:
    """Return whether URL-extracted clean text is too weak for LLM extraction."""

    if clean_text is None:
        return True
    if len(clean_text) < _MIN_RELIABLE_CLEAN_CHARS:
        return True

    normalized = clean_text.casefold()
    return any(signal in normalized for signal in _UNRELIABLE_PAGE_SIGNALS)


def should_run_llm_extraction(state: JobAgentState) -> bool:
    """Return whether parser output is terminal or ready for extraction."""

    return state.get("parse_status") == "success" and bool(state.get("clean_text"))


def prepare_manual_text(
    *,
    batch_id: str,
    role_profile_id: str,
    raw_text: str,
    source_url: str | None = None,
) -> JobAgentState:
    """Build the bounded parser state for network-free manual text input."""

    bounded_raw_text = bound_raw_text(raw_text)
    clean_text = clean_text_content(bounded_raw_text)
    return {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": "manual_text",
        "source_url": source_url,
        "raw_text": bounded_raw_text,
        "clean_text": clean_text,
        "raw_content_hash": compute_content_hash(clean_text),
        "parse_status": "success" if clean_text is not None else "failed",
    }


async def prepare_url_content(
    *,
    batch_id: str,
    role_profile_id: str,
    source_url: str,
    input_source: str = "manual_url",
) -> JobAgentState:
    """Fetch a public URL with configured bounds and extract readable text."""

    map_input_source_to_source_platform(input_source)
    parsed_url = urlparse(source_url)
    if parsed_url.scheme not in {"http", "https"}:
        return _failed_url_state(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            source_url=source_url,
            input_source=input_source,
            error_reason="unsupported_url_scheme",
        )

    max_response_bytes = settings.MAX_RESPONSE_SIZE_MB * 1024 * 1024
    response_body = bytearray()

    # Production note: Implement SSRF mitigation for URL parsing endpoints.
    # Block localhost, private IPs, link-local metadata IPs, unsafe redirects, and internal network targets.
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        ) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    response_body.extend(chunk)
                    if len(response_body) > max_response_bytes:
                        return _failed_url_state(
                            batch_id=batch_id,
                            role_profile_id=role_profile_id,
                            source_url=source_url,
                            input_source=input_source,
                            error_reason="response_size_limit_exceeded",
                        )
                encoding = response.charset_encoding or "utf-8"
    except httpx.TimeoutException:
        return _failed_url_state(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            source_url=source_url,
            input_source=input_source,
            error_reason="request_timeout",
        )
    except httpx.HTTPStatusError:
        return _failed_url_state(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            source_url=source_url,
            input_source=input_source,
            error_reason="http_error",
        )
    except httpx.HTTPError:
        return _failed_url_state(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            source_url=source_url,
            input_source=input_source,
            error_reason="request_failed",
        )

    html = bytes(response_body).decode(encoding, errors="replace")
    extracted_text = trafilatura.extract(html) or ""
    raw_text = bound_raw_text(extracted_text)
    clean_text = clean_text_content(raw_text)
    if is_unreliable_extraction(clean_text):
        return _manual_input_url_state(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            source_url=source_url,
            input_source=input_source,
            clean_text=clean_text,
        )

    return {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": input_source,
        "source_url": source_url,
        "raw_text": raw_text,
        "clean_text": clean_text,
        "raw_content_hash": compute_content_hash(clean_text),
        "parse_status": "success" if clean_text is not None else "failed",
    }


async def run_extraction_graph(
    initial_state: JobAgentState,
    *,
    llm_client: JobExtractionClientProtocol | None = None,
) -> JobAgentState:
    """Run the compiled extraction graph and return a complete extraction state."""
    from app.agents.graph import graph

    config = None
    if llm_client is not None:
        config = {"configurable": {"llm_client": llm_client}}

    return await graph.ainvoke(initial_state, config=config)


async def extract_from_raw_text(
    *,
    batch_id: str,
    role_profile_id: str,
    raw_text: str,
    source_url: str | None = None,
    llm_client: JobExtractionClientProtocol | None = None,
) -> JobAgentState:
    """Prepare a manual_text state, clean/truncate raw text, and run extraction."""
    initial_state: JobAgentState = {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": "manual_text",
        "raw_text": raw_text,
        "source_url": source_url,
    }
    return await run_extraction_graph(initial_state, llm_client=llm_client)


async def extract_from_url(
    *,
    batch_id: str,
    role_profile_id: str,
    source_url: str,
    input_source: Literal["manual_url", "tavily"] = "manual_url",
    llm_client: JobExtractionClientProtocol | None = None,
) -> JobAgentState:
    """Prepare a manual_url or tavily state, fetch/clean URL content, and run extraction or fallback."""
    if input_source not in ("manual_url", "tavily"):
        raise ValueError(
            f"input_source for extract_from_url must be 'manual_url' or 'tavily', got: {input_source}"
        )

    initial_state: JobAgentState = {
        "batch_id": batch_id,
        "role_profile_id": role_profile_id,
        "input_source": input_source,
        "source_url": source_url,
    }
    return await run_extraction_graph(initial_state, llm_client=llm_client)
