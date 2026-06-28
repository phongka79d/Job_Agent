"""
Shared Status and Source Constants.

These constants serve as the central source of truth for status and source values
across backend services, routes, models, schemas, and tests.
"""

# Job Statuses allowed in the job_posts table
JOB_STATUSES = (
    "pending_review",
    "saved",
    "applied",
    "interview",
    "rejected",
    "offer",
    "ignored",
)

# Subset of JOB_STATUSES that represent active tracking states
TRACKED_JOB_STATUSES = (
    "saved",
    "applied",
    "interview",
    "rejected",
    "offer",
)

# Statuses allowed in the applications table
APPLICATION_STATUSES = (
    "applied",
    "interview",
    "rejected",
    "offer",
)

# Job Description completeness statuses
JD_STATUSES = (
    "full_jd",
    "partial_jd",
    "contact_for_jd",
    "no_jd",
    "unclear",
)

# HTML/Markdown parsing statuses
PARSE_STATUSES = (
    "success",
    "needs_manual_input",
    "failed",
)

# Extraction service statuses for job post data
EXTRACTION_STATUSES = (
    "success",
    "retried",
    "failed",
)

# Source platforms for job posts
SOURCE_PLATFORMS = (
    "tavily",
    "manual_url",
    "manual_text",
    "mock",
    "job_board",
)

# Allowed input sources for inserting new job posts
INPUT_SOURCES = (
    "tavily",
    "manual_url",
    "manual_text",
    "mock",
)
