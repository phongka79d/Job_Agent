"""
Constants contract test.

Verifies that the shared status and source constants match the exact
requirements defined in Plan 1 and are correctly imported.
"""

from app.core import constants


def test_constants_exist():
    """Assert every required constant group exists in the constants module."""
    assert hasattr(constants, "JOB_STATUSES")
    assert hasattr(constants, "TRACKED_JOB_STATUSES")
    assert hasattr(constants, "APPLICATION_STATUSES")
    assert hasattr(constants, "JD_STATUSES")
    assert hasattr(constants, "PARSE_STATUSES")
    assert hasattr(constants, "EXTRACTION_STATUSES")
    assert hasattr(constants, "SOURCE_PLATFORMS")
    assert hasattr(constants, "INPUT_SOURCES")


def test_constants_values():
    """Assert each constant group contains exactly the Plan 1 values."""
    assert constants.JOB_STATUSES == (
        "pending_review",
        "saved",
        "applied",
        "interview",
        "rejected",
        "offer",
        "ignored",
    )
    
    assert constants.TRACKED_JOB_STATUSES == (
        "saved",
        "applied",
        "interview",
        "rejected",
        "offer",
    )
    
    assert constants.APPLICATION_STATUSES == (
        "applied",
        "interview",
        "rejected",
        "offer",
    )
    
    assert constants.JD_STATUSES == (
        "full_jd",
        "partial_jd",
        "contact_for_jd",
        "no_jd",
        "unclear",
    )
    
    assert constants.PARSE_STATUSES == (
        "success",
        "needs_manual_input",
        "failed",
    )
    
    assert constants.EXTRACTION_STATUSES == (
        "success",
        "retried",
        "failed",
    )
    
    assert constants.SOURCE_PLATFORMS == (
        "tavily",
        "manual_url",
        "manual_text",
        "mock",
        "job_board",
    )
    
    assert constants.INPUT_SOURCES == (
        "tavily",
        "manual_url",
        "manual_text",
        "mock",
    )


def test_tracked_statuses_are_subset_of_job_statuses():
    """Assert tracked statuses are a subset of job statuses."""
    job_statuses_set = set(constants.JOB_STATUSES)
    tracked_statuses_set = set(constants.TRACKED_JOB_STATUSES)
    assert tracked_statuses_set.issubset(job_statuses_set)


def test_application_statuses_are_subset_of_tracked_job_statuses():
    """Assert application statuses are a subset of tracked job statuses."""
    tracked_job_statuses_set = set(constants.TRACKED_JOB_STATUSES)
    application_statuses_set = set(constants.APPLICATION_STATUSES)
    assert application_statuses_set.issubset(tracked_job_statuses_set)
