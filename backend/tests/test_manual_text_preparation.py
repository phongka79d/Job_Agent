"""Focused contract tests for manual-text preparation."""

import hashlib

from app.core.config import settings
from app.services.extraction_service import (
    clean_text_content,
    compute_content_hash,
    prepare_manual_text,
)


def test_empty_manual_text_is_not_parse_success() -> None:
    state = prepare_manual_text(
        batch_id="batch-1",
        role_profile_id="role-1",
        raw_text=" \r\n\t\n ",
    )

    assert state["input_source"] == "manual_text"
    assert state["clean_text"] is None
    assert state["raw_content_hash"] is None
    assert state["parse_status"] == "failed"


def test_normal_manual_text_preserves_sections_and_hashes_clean_content() -> None:
    raw_text = (
        "  Senior Engineer  \r\n\r\n"
        "Responsibilities:\t Build APIs  \n\n\n"
        " Requirements:\n Python  "
    )

    state = prepare_manual_text(
        batch_id="batch-1",
        role_profile_id="role-1",
        raw_text=raw_text,
        source_url="https://example.test/job",
    )

    expected_clean_text = (
        "Senior Engineer\n\n"
        "Responsibilities: Build APIs\n\n"
        "Requirements:\n"
        "Python"
    )
    assert state == {
        "batch_id": "batch-1",
        "role_profile_id": "role-1",
        "input_source": "manual_text",
        "source_url": "https://example.test/job",
        "raw_text": raw_text[: settings.MAX_RAW_TEXT_CHARS],
        "clean_text": expected_clean_text,
        "raw_content_hash": hashlib.sha256(
            expected_clean_text.encode("utf-8")
        ).hexdigest(),
        "parse_status": "success",
    }


def test_oversized_manual_text_obeys_raw_and_clean_limits() -> None:
    raw_text = ("Responsibilities: build APIs with Python.\n" * 1000) + (
        "x" * settings.MAX_RAW_TEXT_CHARS
    )

    state = prepare_manual_text(
        batch_id="batch-1",
        role_profile_id="role-1",
        raw_text=raw_text,
    )

    assert len(state["raw_text"]) == settings.MAX_RAW_TEXT_CHARS
    assert state["clean_text"] is not None
    assert len(state["clean_text"]) <= settings.MAX_CLEAN_TEXT_CHARS
    assert not state["clean_text"].endswith((" ", "\t", "\n"))
    assert state["parse_status"] == "success"


def test_oversized_cleaning_drops_known_low_signal_footer_lines() -> None:
    job_content = "\n".join(
        f"- Build reliable Python service component {index}" for index in range(260)
    )
    low_signal_footer = "\n".join("Accept all cookies" for _ in range(250))

    clean_text = clean_text_content(f"Responsibilities:\n{job_content}\n{low_signal_footer}")

    assert clean_text is not None
    assert "Responsibilities:" in clean_text
    assert "Accept all cookies" not in clean_text
    assert len(clean_text) <= settings.MAX_CLEAN_TEXT_CHARS


def test_content_hash_is_stable_for_repeat_clean_content() -> None:
    clean_text = clean_text_content("Title\n\nRequirements:\nPython")

    assert clean_text is not None
    assert compute_content_hash(clean_text) == compute_content_hash(clean_text)
    assert compute_content_hash(clean_text) == hashlib.sha256(
        clean_text.encode("utf-8")
    ).hexdigest()
    assert compute_content_hash("") is None
