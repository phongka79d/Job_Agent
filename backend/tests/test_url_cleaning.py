"""Focused URL preparation tests using mocked HTTP responses."""

import hashlib

import httpx
import pytest
import respx

from app.core.config import settings
from app.services.extraction_service import (
    is_unreliable_extraction,
    prepare_url_content,
    should_run_llm_extraction,
)


UNRELIABLE_EXTRACTION_NOTE = "URL content was too short or unreliable for extraction"
EXPECTED_MANUAL_INPUT_WARNING = (
    "We could not extract enough job content from this URL.\n"
    "The page may require JavaScript rendering, login, or cookie acceptance.\n"
    "Please paste the job description text manually."
)


@pytest.mark.asyncio
@respx.mock
async def test_mocked_url_fetch_extracts_bounded_clean_text() -> None:
    source_url = "https://example.test/jobs/senior-engineer"
    html = """
    <html>
      <head><title>Senior Backend Engineer</title></head>
      <body>
        <main>
          <h1>Senior Backend Engineer</h1>
          <p>Acme builds reliable workflow software for operations teams.</p>
          <h2>Responsibilities</h2>
          <p>Build Python APIs, maintain async services, and improve observability.</p>
          <h2>Requirements</h2>
          <p>Python, FastAPI, SQL, testing discipline, and production ownership.</p>
        </main>
      </body>
    </html>
    """
    respx.get(source_url).mock(return_value=httpx.Response(200, text=html))

    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url=source_url,
    )

    assert state["input_source"] == "manual_url"
    assert state["source_url"] == source_url
    assert state["parse_status"] == "success"
    assert state["raw_text"]
    assert state["clean_text"]
    assert "Senior Backend Engineer" in state["clean_text"]
    assert "Python APIs" in state["clean_text"]
    assert len(state["clean_text"]) <= settings.MAX_CLEAN_TEXT_CHARS
    assert state["raw_content_hash"] == hashlib.sha256(
        state["clean_text"].encode("utf-8")
    ).hexdigest()


@pytest.mark.asyncio
@respx.mock
async def test_invalid_url_scheme_is_rejected_before_network_access() -> None:
    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url="file:///etc/passwd",
    )

    assert state["parse_status"] == "failed"
    assert state["error_reason"] == "unsupported_url_scheme"
    assert state["clean_text"] is None
    assert state["raw_content_hash"] is None
    assert len(respx.calls) == 0


@pytest.mark.asyncio
@respx.mock
async def test_timeout_returns_parser_failure_without_crashing() -> None:
    source_url = "https://example.test/timeout"
    respx.get(source_url).mock(side_effect=httpx.ReadTimeout("timed out"))

    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url=source_url,
    )

    assert state["parse_status"] == "failed"
    assert state["error_reason"] == "request_timeout"
    assert state["clean_text"] is None


@pytest.mark.asyncio
@respx.mock
async def test_oversized_response_returns_parser_failure_without_extracting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_url = "https://example.test/too-large"
    monkeypatch.setattr(settings, "MAX_RESPONSE_SIZE_MB", 0)
    monkeypatch.setattr(
        "app.services.extraction_service.trafilatura.extract",
        lambda html: pytest.fail("oversized responses must not be extracted"),
    )
    respx.get(source_url).mock(return_value=httpx.Response(200, content=b"x"))

    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url=source_url,
    )

    assert state["parse_status"] == "failed"
    assert state["error_reason"] == "response_size_limit_exceeded"
    assert state["raw_text"] is None
    assert state["clean_text"] is None


@pytest.mark.asyncio
@respx.mock
async def test_http_failure_returns_parser_failure_without_crashing() -> None:
    source_url = "https://example.test/not-found"
    respx.get(source_url).mock(return_value=httpx.Response(404))

    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url=source_url,
    )

    assert state["parse_status"] == "failed"
    assert state["error_reason"] == "http_error"
    assert state["clean_text"] is None
    assert state["raw_content_hash"] is None


@pytest.mark.asyncio
@respx.mock
async def test_low_content_url_returns_complete_manual_input_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_url = "https://example.test/js-shell"
    monkeypatch.setattr(
        "app.services.extraction_service.trafilatura.extract",
        lambda html: "Apply now",
    )
    respx.get(source_url).mock(return_value=httpx.Response(200, text="<html></html>"))

    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url=source_url,
    )

    assert state["batch_id"] == "batch-1"
    assert state["role_profile_id"] == "role-1"
    assert state["input_source"] == "manual_url"
    assert state["source_url"] == source_url
    assert state["raw_text"] is None
    assert state["clean_text"] == "Apply now"
    assert state["raw_content_hash"] == hashlib.sha256(b"Apply now").hexdigest()
    assert state["parse_status"] == "needs_manual_input"
    assert state["jd_status"] == "unclear"
    assert state["should_score_similarity"] is False
    assert state["extraction_status"] is None
    assert state["error_reason"] == UNRELIABLE_EXTRACTION_NOTE
    assert state["user_warning"] == EXPECTED_MANUAL_INPUT_WARNING
    assert state["input_tokens"] is None
    assert state["output_tokens"] is None
    assert state["estimated_cost_usd"] is None
    assert state["extraction_time_ms"] is None

    assert state["extracted_job"] == {
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
        "source_url": source_url,
        "source_platform": "manual_url",
        "jd_status": "unclear",
        "should_score_similarity": False,
        "extraction_notes": UNRELIABLE_EXTRACTION_NOTE,
    }
    for score_field in (
        "embedding_text",
        "embedding_similarity",
        "skill_overlap_score",
        "location_match_score",
        "level_match_score",
        "base_score",
        "jd_confidence_multiplier",
        "final_score",
        "final_score_percent",
    ):
        assert state[score_field] is None


def test_unreliable_extraction_detects_low_content_and_blocked_signals() -> None:
    assert is_unreliable_extraction("x" * 149)
    assert not is_unreliable_extraction("x" * 150)
    assert is_unreliable_extraction("Please enable JavaScript to view this page." * 6)
    assert is_unreliable_extraction("Sign in to view this job posting." * 7)
    assert is_unreliable_extraction("Accept cookies to continue to this site." * 7)


@pytest.mark.asyncio
@respx.mock
async def test_manual_input_parser_state_is_terminal_before_fake_llm_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        async def extract_job(self) -> None:
            self.calls += 1

    source_url = "https://example.test/login-gated"
    monkeypatch.setattr(
        "app.services.extraction_service.trafilatura.extract",
        lambda html: "Sign in to continue to this job page." * 8,
    )
    respx.get(source_url).mock(return_value=httpx.Response(200, text="<html></html>"))

    state = await prepare_url_content(
        batch_id="batch-1",
        role_profile_id="role-1",
        source_url=source_url,
    )
    fake_client = FakeClient()

    if should_run_llm_extraction(state):
        await fake_client.extract_job()

    assert state["parse_status"] == "needs_manual_input"
    assert fake_client.calls == 0
