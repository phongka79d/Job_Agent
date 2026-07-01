from uuid import UUID

import pytest

from app.agents.schemas import JobAgentState


@pytest.mark.asyncio
async def test_ingest_raw_job_text_delegates_to_extraction_and_processing(monkeypatch):
    from app.services import job_text_ingestion_workflow as workflow

    calls = []

    async def extract_double(*, batch_id, role_profile_id, raw_text, source_url=None):
        calls.append(
            {
                "batch_id": batch_id,
                "role_profile_id": role_profile_id,
                "raw_text": raw_text,
                "source_url": source_url,
            }
        )
        return JobAgentState(
            batch_id=batch_id,
            role_profile_id=role_profile_id,
            input_source="manual_text",
            source_url=source_url,
            raw_text=raw_text,
            cleaned_text=raw_text,
        )

    class ProcessingResult:
        inserted_jobs = 1
        skipped_exact_duplicates = 2
        skipped_dedup_key_duplicates = 3
        inserted_duplicate_metadata = 0
        qdrant_upserted = 1
        qdrant_synced = True
        job_ids = ["job-1"]
        warnings = ["minor warning"]

    async def process_double(session, state):
        assert session == "session"
        assert state["raw_text"] == "Senior AI Engineer\nRequirements: Python"
        return ProcessingResult()

    monkeypatch.setattr(workflow, "extract_from_raw_text", extract_double)
    monkeypatch.setattr(workflow, "process_job_state", process_double)

    result = await workflow.ingest_raw_job_text(
        "session",
        role_profile_id="profile-1",
        raw_text="Senior AI Engineer\nRequirements: Python",
        source_url="https://example.com/job",
    )

    assert isinstance(result.batch_id, UUID)
    assert calls == [
        {
            "batch_id": str(result.batch_id),
            "role_profile_id": "profile-1",
            "raw_text": "Senior AI Engineer\nRequirements: Python",
            "source_url": "https://example.com/job",
        }
    ]
    assert result.inserted_jobs == 1
    assert result.skipped_exact_duplicates == 2
    assert result.skipped_dedup_key_duplicates == 3
    assert result.qdrant_upserted == 1
    assert result.qdrant_synced is True
    assert result.job_ids == ["job-1"]
    assert result.warnings == ["minor warning"]


@pytest.mark.asyncio
async def test_ingest_raw_job_text_emits_progress(monkeypatch):
    from app.services import job_text_ingestion_workflow as workflow

    progress = []

    async def extract_double(**kwargs):
        return JobAgentState(
            batch_id=kwargs["batch_id"],
            role_profile_id=kwargs["role_profile_id"],
            input_source="manual_text",
            raw_text=kwargs["raw_text"],
            cleaned_text=kwargs["raw_text"],
        )

    class ProcessingResult:
        inserted_jobs = 0
        skipped_exact_duplicates = 0
        skipped_dedup_key_duplicates = 0
        inserted_duplicate_metadata = 0
        qdrant_upserted = 0
        qdrant_synced = True
        job_ids = []
        warnings = []

    async def process_double(session, state):
        return ProcessingResult()

    monkeypatch.setattr(workflow, "extract_from_raw_text", extract_double)
    monkeypatch.setattr(workflow, "process_job_state", process_double)

    await workflow.ingest_raw_job_text(
        object(),
        role_profile_id="profile-1",
        raw_text="Responsibilities: build ML systems. Requirements: Python.",
        on_progress=progress.append,
    )

    assert progress == [
        "Preparing pasted job text...",
        "Extracting structured job data...",
        "Scoring against the active profile...",
        "Saving job to Review Queue...",
    ]
