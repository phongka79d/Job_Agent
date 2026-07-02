from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.db.models import JobPost, ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion, RoleProfile
from app.services.profile_cv_job_improvement_service import (
    GenerateCvImprovementsRequest,
    ProfileCvJobImprovementService,
)


async def create_active_cv(db_session, *, with_active: bool = True):
    profile = RoleProfile(
        id=str(uuid4()),
        target_role="AI Engineer Intern",
        level="intern",
        location="Ha Noi",
        accept_remote=True,
        skills=json.dumps(["FastAPI", "LangGraph"]),
    )
    db_session.add(profile)
    await db_session.flush()
    document = ProfileDocument(
        role_profile_id=profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash=str(uuid4()),
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=120,
        chunk_count=1,
        document_kind="cv",
        status="ready",
    )
    db_session.add(document)
    await db_session.flush()
    version = ProfileDocumentVersion(
        document_id=document.id,
        role_profile_id=profile.id,
        version_number=1,
        source_type="original_upload",
        display_name="Original upload",
        filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash=document.content_hash,
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=120,
        chunk_count=1,
        extraction_status="ready",
        structure_status="reliable",
        structure_confidence=0.8,
        created_by="user",
    )
    db_session.add(version)
    await db_session.flush()
    if with_active:
        document.active_version_id = version.id
        profile.active_cv_document_id = document.id
        profile.active_cv_version_id = version.id
    await db_session.commit()
    return profile, document, version


@pytest.mark.asyncio
async def test_generate_suggestions_maps_score_gap_to_active_cv_evidence(
    db_session,
):
    profile, document, version = await create_active_cv(db_session)
    db_session.add(
        ProfileDocumentChunk(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            source_type="profile_cv",
            chunk_index=0,
            text="Built FastAPI APIs and retrieval augmented generation pipelines with LangGraph.",
            token_count=12,
            qdrant_point_id="point-1",
        )
    )
    job = JobPost(
        batch_id=str(uuid4()),
        role_profile_id=profile.id,
        title="AI Engineer Intern",
        company="Example",
        location=profile.location,
        level=profile.level,
        requirements="FastAPI\nLangGraph\nAWS deployment",
        skills=json.dumps(["FastAPI", "LangGraph", "AWS"]),
        source_platform="manual_text",
        parse_status="success",
        jd_status="full_jd",
        extraction_status="success",
        should_score_similarity=True,
        embedding_similarity=0.7,
        skill_overlap_score=0.4,
        location_match_score=1.0,
        level_match_score=1.0,
        base_score=0.65,
        jd_confidence_multiplier=1.0,
        final_score=0.65,
        final_score_percent=65.0,
        status="pending_review",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    result = await ProfileCvJobImprovementService().generate_suggestions(
        db_session,
        GenerateCvImprovementsRequest(role_profile_id=profile.id, job_id=job.id),
    )

    assert result.job_id == job.id
    assert result.document_id == document.id
    assert result.version_id == version.id
    assert len(result.suggestions) >= 2
    wording = [item for item in result.suggestions if item.edit_kind == "wording_only"]
    fact_required = [item for item in result.suggestions if item.edit_kind == "requires_user_fact"]
    assert any("FastAPI" in item.requirement or "LangGraph" in item.requirement for item in wording)
    assert any("AWS" in item.requirement for item in fact_required)
    assert all("invent" not in item.proposed_edit.casefold() for item in result.suggestions)


@pytest.mark.asyncio
async def test_generate_suggestions_requires_job_in_profile(db_session):
    profile, _, _ = await create_active_cv(db_session)
    other_profile = RoleProfile(
        id=str(uuid4()),
        target_role="Other Role",
        level="senior",
        location="Other",
        accept_remote=True,
        skills=json.dumps(["Other"]),
    )
    db_session.add(other_profile)
    await db_session.flush()
    job = JobPost(
        batch_id=str(uuid4()),
        role_profile_id=other_profile.id,
        title="Backend Engineer",
        company="Example",
        source_platform="manual_text",
        parse_status="success",
        jd_status="full_jd",
        extraction_status="success",
        should_score_similarity=True,
        status="pending_review",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with pytest.raises(LookupError, match="Job not found"):
        await ProfileCvJobImprovementService().generate_suggestions(
            db_session,
            GenerateCvImprovementsRequest(role_profile_id=profile.id, job_id=job.id),
        )


@pytest.mark.asyncio
async def test_scored_job_to_draft_keeps_active_cv_unchanged(
    db_session,
):
    import json
    from uuid import uuid4

    from app.db.models import JobPost, ProfileDocumentChunk
    from app.services.profile_cv_draft_service import CreateCvDraftRequest, ProfileCvDraftService

    profile, document, version = await create_active_cv(db_session)
    db_session.add(
        ProfileDocumentChunk(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            source_type="profile_cv",
            chunk_index=0,
            text="Built FastAPI APIs and LangGraph workflows.",
            token_count=8,
            qdrant_point_id="point-e2e-1",
        )
    )
    job = JobPost(
        batch_id=str(uuid4()),
        role_profile_id=profile.id,
        title="AI Engineer Intern",
        company="Example",
        requirements="FastAPI",
        skills=json.dumps(["FastAPI"]),
        source_platform="manual_text",
        parse_status="success",
        jd_status="full_jd",
        extraction_status="success",
        should_score_similarity=True,
        skill_overlap_score=0.5,
        final_score=0.7,
        final_score_percent=70,
        status="pending_review",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    generation = await ProfileCvJobImprovementService().generate_suggestions(
        db_session,
        GenerateCvImprovementsRequest(role_profile_id=profile.id, job_id=job.id),
    )
    wording_only_ids = [
        suggestion.id for suggestion in generation.suggestions if suggestion.edit_kind == "wording_only"
    ]
    assert wording_only_ids

    draft = await ProfileCvDraftService().create_draft(
        db_session,
        CreateCvDraftRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            base_version_id=version.id,
            title="Draft from scored job",
            suggestion_ids=wording_only_ids,
            confirmed=True,
        ),
    )

    assert draft.status == "draft"
    await db_session.refresh(profile)
    await db_session.refresh(document)
    assert profile.active_cv_version_id == version.id
    assert document.active_version_id == version.id


@pytest.mark.asyncio
async def test_generate_suggestions_requires_active_cv(db_session):
    profile, _, _ = await create_active_cv(db_session, with_active=False)
    job = JobPost(
        batch_id=str(uuid4()),
        role_profile_id=profile.id,
        title="Backend Engineer",
        company="Example",
        requirements="FastAPI",
        source_platform="manual_text",
        parse_status="success",
        jd_status="full_jd",
        extraction_status="success",
        should_score_similarity=True,
        status="pending_review",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with pytest.raises(ValueError, match="active CV"):
        await ProfileCvJobImprovementService().generate_suggestions(
            db_session,
            GenerateCvImprovementsRequest(role_profile_id=profile.id, job_id=job.id),
        )
