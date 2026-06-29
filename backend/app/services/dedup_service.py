"""
Deduplication Service.

Provides utility functions for normalizing job post fields, building deterministic
deduplication keys, and deciding appropriate actions for duplicate jobs based on
their existing status.
"""

import hashlib
from app.core.constants import TRACKED_JOB_STATUSES


def normalize_text(text: str | None) -> str:
    """
    Normalize text by trimming whitespace, lowercasing, and replacing multiple
    consecutive spaces with a single space. Returns empty string if text is None
    or blank.
    """
    if text is None:
        return ""
    return " ".join(text.strip().lower().split())


def build_dedup_key(company: str | None, title: str | None) -> str | None:
    """
    Generate a deterministic deduplication key for a job post.

    Returns None if either the normalized company or normalized title is missing
    or blank. Uses SHA-256 to hash the concatenated normalized fields.
    """
    norm_company = normalize_text(company)
    norm_title = normalize_text(title)

    if not norm_company or not norm_title:
        return None

    # Concatenate using a distinct separator to avoid collisions
    # e.g. "Google" and "Software Engineer" -> "google|software engineer"
    combined = f"{norm_company}|{norm_title}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def decide_duplicate_action(existing_job_status: str) -> str:
    """
    Decide the duplicate action policy based on the status of an existing duplicate job.

    Returns:
        - "skip_duplicate": If the existing job is in "pending_review" or "ignored"
          (skip inserting a new duplicate row).
        - "mark_new_as_duplicate_ignored": If the existing job is active/tracked
          (saved, applied, interview, rejected, offer), meaning we insert a new row
          with duplicate metadata and status = "ignored".
        - "skip_duplicate" (default/fallback): For any other status.
    """
    if existing_job_status == "pending_review":
        return "skip_duplicate"
    if existing_job_status in TRACKED_JOB_STATUSES:
        return "mark_new_as_duplicate_ignored"
    if existing_job_status == "ignored":
        return "skip_duplicate"
    return "skip_duplicate"
