"""Profile CV suggestion and draft services."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ProfileCvDraft,
    ProfileCvImprovementSuggestion,
    ProfileDocument,
    ProfileDocumentChunk,
    ProfileDocumentVersion,
)
from app.services.cv_structure_extraction_service import POOR_STRUCTURE_RECOMMENDATION


EditKind = Literal["wording_only", "requires_user_fact"]
RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CreateCvSuggestionRequest:
    role_profile_id: str
    document_id: str
    version_id: str
    requirement: str
    current_cv_evidence: str
    missing_or_weak_evidence: str
    proposed_edit: str
    edit_kind: EditKind
    risk_level: RiskLevel
    requires_confirmation: bool = True
    job_id: str | None = None


@dataclass(frozen=True)
class CreateCvDraftRequest:
    role_profile_id: str
    document_id: str
    base_version_id: str
    title: str
    suggestion_ids: list[str]
    confirmed: bool
    created_by: str = "ai"


class ProfileCvDraftService:
    async def create_suggestion(
        self,
        session: AsyncSession,
        request: CreateCvSuggestionRequest,
    ) -> ProfileCvImprovementSuggestion:
        await self._require_version(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.version_id,
        )
        if request.risk_level not in {"low", "medium", "high"}:
            raise ValueError("risk_level must be low, medium, or high")
        if request.edit_kind not in {"wording_only", "requires_user_fact"}:
            raise ValueError("edit_kind must be wording_only or requires_user_fact")

        suggestion = ProfileCvImprovementSuggestion(
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.version_id,
            job_id=request.job_id,
            requirement=request.requirement.strip(),
            current_cv_evidence=request.current_cv_evidence.strip(),
            missing_or_weak_evidence=request.missing_or_weak_evidence.strip(),
            proposed_edit=request.proposed_edit.strip(),
            edit_kind=request.edit_kind,
            risk_level=request.risk_level,
            requires_confirmation=request.requires_confirmation,
            status="suggested",
        )
        session.add(suggestion)
        await session.commit()
        await session.refresh(suggestion)
        return suggestion

    async def list_suggestions(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str | None = None,
    ) -> list[ProfileCvImprovementSuggestion]:
        statement = select(ProfileCvImprovementSuggestion).where(
            ProfileCvImprovementSuggestion.role_profile_id == role_profile_id
        )
        if document_id:
            statement = statement.where(ProfileCvImprovementSuggestion.document_id == document_id)
        result = await session.execute(statement.order_by(ProfileCvImprovementSuggestion.created_at.desc()))
        return list(result.scalars())

    async def create_draft(
        self,
        session: AsyncSession,
        request: CreateCvDraftRequest,
    ) -> ProfileCvDraft:
        if not request.confirmed:
            raise ValueError("Creating a CV draft requires confirmation.")
        document, version = await self._require_version(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.base_version_id,
        )
        suggestions = await self._load_suggestions(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.base_version_id,
            suggestion_ids=request.suggestion_ids,
        )
        chunks = await self._load_chunks(
            session,
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            version_id=request.base_version_id,
        )
        structure = {
            "source": "extracted_text",
            "document_id": document.id,
            "version_id": version.id,
            "structure_status": version.structure_status,
            "sections": [{"heading": "Extracted CV", "content": "\n\n".join(chunk.text for chunk in chunks)}],
            "recommendation": (
                POOR_STRUCTURE_RECOMMENDATION
                if version.structure_status == "unreliable"
                else None
            ),
        }
        edit_plan = {
            "suggestion_ids": [suggestion.id for suggestion in suggestions],
            "edits": [
                {
                    "requirement": suggestion.requirement,
                    "current_cv_evidence": suggestion.current_cv_evidence,
                    "proposed_edit": suggestion.proposed_edit,
                    "edit_kind": suggestion.edit_kind,
                    "risk_level": suggestion.risk_level,
                }
                for suggestion in suggestions
            ],
        }
        draft = ProfileCvDraft(
            role_profile_id=request.role_profile_id,
            document_id=request.document_id,
            base_version_id=request.base_version_id,
            status="draft",
            title=request.title.strip() or "CV edit draft",
            structure_json=json.dumps(structure, separators=(",", ":")),
            edit_plan_json=json.dumps(edit_plan, separators=(",", ":")),
            structure_status_at_creation=version.structure_status,
            created_by=request.created_by,
        )
        session.add(draft)
        for suggestion in suggestions:
            suggestion.status = "drafted"
        await session.commit()
        await session.refresh(draft)
        return draft

    async def list_drafts(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str | None = None,
    ) -> list[ProfileCvDraft]:
        statement = select(ProfileCvDraft).where(ProfileCvDraft.role_profile_id == role_profile_id)
        if document_id:
            statement = statement.where(ProfileCvDraft.document_id == document_id)
        result = await session.execute(statement.order_by(ProfileCvDraft.updated_at.desc()))
        return list(result.scalars())

    async def preview_draft(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        draft_id: str,
        document_id: str | None = None,
    ) -> dict[str, object]:
        draft = await session.get(ProfileCvDraft, draft_id)
        if draft is None or draft.role_profile_id != role_profile_id:
            raise LookupError("CV draft not found")
        if document_id is not None and draft.document_id != document_id:
            raise LookupError("CV draft not found")
        structure = json.loads(draft.structure_json)
        edit_plan = json.loads(draft.edit_plan_json)
        return {
            "draft_id": draft.id,
            "title": draft.title,
            "status": draft.status,
            "structure_status": draft.structure_status_at_creation,
            "recommendation": structure.get("recommendation"),
            "sections": structure.get("sections", []),
            "edits": edit_plan.get("edits", []),
        }

    async def _require_version(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
    ) -> tuple[ProfileDocument, ProfileDocumentVersion]:
        document = await session.get(ProfileDocument, document_id)
        version = await session.get(ProfileDocumentVersion, version_id)
        if document is None or version is None:
            raise LookupError("Profile CV version not found")
        if document.role_profile_id != role_profile_id or version.role_profile_id != role_profile_id:
            raise LookupError("Profile CV version not found")
        if version.document_id != document_id:
            raise LookupError("Profile CV version not found")
        return document, version

    async def _load_suggestions(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
        suggestion_ids: list[str],
    ) -> list[ProfileCvImprovementSuggestion]:
        if not suggestion_ids:
            return []
        result = await session.execute(
            select(ProfileCvImprovementSuggestion)
            .where(ProfileCvImprovementSuggestion.id.in_(suggestion_ids))
            .where(ProfileCvImprovementSuggestion.role_profile_id == role_profile_id)
            .where(ProfileCvImprovementSuggestion.document_id == document_id)
            .where(ProfileCvImprovementSuggestion.version_id == version_id)
        )
        by_id = {suggestion.id: suggestion for suggestion in result.scalars()}
        missing = [suggestion_id for suggestion_id in suggestion_ids if suggestion_id not in by_id]
        if missing:
            raise LookupError("CV suggestion not found")
        suggestions = [by_id[suggestion_id] for suggestion_id in suggestion_ids]
        fact_required = [suggestion for suggestion in suggestions if suggestion.edit_kind == "requires_user_fact"]
        if fact_required:
            raise ValueError("Suggestion requires user-provided facts before drafting.")
        high_risk = [suggestion for suggestion in suggestions if suggestion.risk_level == "high"]
        if high_risk:
            raise ValueError("High-risk CV suggestions require manual user-provided facts before drafting.")
        return suggestions

    async def _load_chunks(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        document_id: str,
        version_id: str,
    ) -> list[ProfileDocumentChunk]:
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.role_profile_id == role_profile_id)
            .where(ProfileDocumentChunk.document_id == document_id)
            .where(ProfileDocumentChunk.version_id == version_id)
            .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
        )
        return list(result.scalars())
