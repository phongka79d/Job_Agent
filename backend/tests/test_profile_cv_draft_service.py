import json

import pytest
from sqlalchemy import select

from app.db.models import (
    ProfileCvDraft,
    ProfileCvImprovementSuggestion,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
    RoleProfile,
)
from app.services.cv_structure_extraction_service import POOR_STRUCTURE_RECOMMENDATION
from app.services.profile_cv_draft_service import (
    CreateCvDraftRequest,
    CreateCvSuggestionRequest,
    ProfileCvDraftService,
)


async def create_cv(db_session, *, structure_status: str = "reliable"):
    profile = RoleProfile(target_role="AI Engineer", location="Hanoi", skills='["Python"]')
    db_session.add(profile)
    await db_session.flush()
    document = ProfileDocument(
        role_profile_id=profile.id,
        original_filename="cv.pdf",
        stored_path="cv.pdf",
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=80,
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
        content_hash="hash",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_chars=80,
        chunk_count=1,
        extraction_status="ready",
        structure_status=structure_status,
        structure_confidence=0.8 if structure_status == "reliable" else 0.1,
        created_by="user",
    )
    db_session.add(version)
    await db_session.flush()
    document.active_version_id = version.id
    profile.active_cv_document_id = document.id
    profile.active_cv_version_id = version.id
    db_session.add(
        ProfileDocumentChunk(
            document_id=document.id,
            role_profile_id=profile.id,
            version_id=version.id,
            source_type="profile_cv",
            chunk_index=0,
            text="Active CV evidence: Python FastAPI project",
            token_count=8,
            qdrant_point_id="99999999-9999-9999-9999-999999999999",
        )
    )
    await db_session.commit()
    return profile, document, version


@pytest.mark.asyncio
async def test_create_suggestion_stores_fact_required_safely(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()

    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            requirement="AWS production experience",
            current_cv_evidence="No AWS evidence in active CV.",
            missing_or_weak_evidence="AWS is missing.",
            proposed_edit="Add AWS production deployment experience.",
            edit_kind="requires_user_fact",
            risk_level="high",
            requires_confirmation=True,
        ),
    )

    assert suggestion.edit_kind == "requires_user_fact"
    assert suggestion.status == "suggested"


@pytest.mark.asyncio
async def test_create_wording_suggestion_persists_grounded_item(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()

    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            requirement="FastAPI",
            current_cv_evidence="Active CV evidence: Python FastAPI project",
            missing_or_weak_evidence="FastAPI evidence is present but not emphasized.",
            proposed_edit="Emphasize FastAPI API ownership in the project bullet.",
            edit_kind="wording_only",
            risk_level="low",
            requires_confirmation=True,
        ),
    )

    assert suggestion.status == "suggested"
    assert suggestion.edit_kind == "wording_only"


@pytest.mark.asyncio
async def test_create_draft_preserves_original_and_marks_suggestions_drafted(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()
    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            requirement="FastAPI",
            current_cv_evidence="Active CV evidence: Python FastAPI project",
            missing_or_weak_evidence="FastAPI evidence is weakly worded.",
            proposed_edit="Rewrite bullet to lead with FastAPI service delivery.",
            edit_kind="wording_only",
            risk_level="low",
            requires_confirmation=True,
        ),
    )

    draft = await service.create_draft(
        db_session,
        CreateCvDraftRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            base_version_id=version.id,
            title="FastAPI emphasis draft",
            suggestion_ids=[suggestion.id],
            confirmed=True,
            created_by="ai",
        ),
    )

    stored = await db_session.get(ProfileCvDraft, draft.id)
    updated_suggestion = await db_session.get(ProfileCvImprovementSuggestion, suggestion.id)
    document_after = await db_session.get(ProfileDocument, document.id)
    assert stored.status == "draft"
    assert json.loads(stored.edit_plan_json)["suggestion_ids"] == [suggestion.id]
    assert updated_suggestion.status == "drafted"
    assert document_after.active_version_id == version.id


@pytest.mark.asyncio
async def test_create_draft_for_unreliable_structure_returns_template_recommendation(db_session):
    profile, document, version = await create_cv(db_session, structure_status="unreliable")
    service = ProfileCvDraftService()

    draft = await service.create_draft(
        db_session,
        CreateCvDraftRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            base_version_id=version.id,
            title="Template draft",
            suggestion_ids=[],
            confirmed=True,
            created_by="ai",
        ),
    )

    preview = await service.preview_draft(db_session, role_profile_id=profile.id, draft_id=draft.id)
    assert preview["recommendation"] == POOR_STRUCTURE_RECOMMENDATION
    assert preview["structure_status"] == "unreliable"


@pytest.mark.asyncio
async def test_create_suggestion_stores_requires_user_fact_without_drafting(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()

    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            job_id=None,
            requirement="AWS production deployment",
            current_cv_evidence="No AWS deployment evidence found in the active CV.",
            missing_or_weak_evidence="The job asks for AWS, but the CV does not contain that fact.",
            proposed_edit="Ask the user for real AWS deployment evidence before adding this.",
            edit_kind="requires_user_fact",
            risk_level="high",
            requires_confirmation=True,
        ),
    )

    assert suggestion.edit_kind == "requires_user_fact"
    assert suggestion.risk_level == "high"
    assert suggestion.status == "suggested"


@pytest.mark.asyncio
async def test_create_draft_rejects_fact_required_suggestions(db_session):
    profile, document, version = await create_cv(db_session)
    service = ProfileCvDraftService()
    suggestion = await service.create_suggestion(
        db_session,
        CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            job_id=None,
            requirement="AWS production deployment",
            current_cv_evidence="No AWS deployment evidence found in the active CV.",
            missing_or_weak_evidence="Requires new user-provided facts.",
            proposed_edit="Ask the user for real AWS deployment evidence before adding this.",
            edit_kind="requires_user_fact",
            risk_level="high",
            requires_confirmation=True,
        ),
    )

    with pytest.raises(ValueError, match="requires user-provided facts"):
        await service.create_draft(
            db_session,
            CreateCvDraftRequest(
                role_profile_id=profile.id,
                document_id=document.id,
                base_version_id=version.id,
                title="Fact required draft",
                suggestion_ids=[suggestion.id],
                confirmed=True,
            ),
        )

    result = await db_session.execute(select(ProfileCvImprovementSuggestion).where(ProfileCvImprovementSuggestion.id == suggestion.id))
    stored = result.scalar_one()
    assert stored.status == "suggested"
