from app.services.dedup_service import (
    build_dedup_key,
    decide_duplicate_action,
    normalize_text,
)


def test_normalize_text_collapses_case_and_whitespace():
    assert normalize_text("  Senior   Backend Engineer  ") == "senior backend engineer"
    assert normalize_text(None) == ""


def test_build_dedup_key_is_stable_after_normalization():
    assert build_dedup_key(" Acme  Inc ", "Backend Engineer") == build_dedup_key(
        "acme inc",
        " backend   engineer ",
    )


def test_build_dedup_key_requires_company_and_title():
    assert build_dedup_key(None, "Backend Engineer") is None
    assert build_dedup_key("Acme", None) is None
    assert build_dedup_key("   ", "Backend Engineer") is None
    assert build_dedup_key("Acme", "   ") is None


def test_duplicate_action_policy_for_pending_tracked_and_ignored_statuses():
    assert decide_duplicate_action("pending_review") == "skip_duplicate"
    assert decide_duplicate_action("ignored") == "skip_duplicate"

    for tracked_status in ("saved", "applied", "interview", "rejected", "offer"):
        assert (
            decide_duplicate_action(tracked_status)
            == "mark_new_as_duplicate_ignored"
        )
