"""Generate grounded CV improvement suggestions from scored jobs."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobPost, ProfileCvImprovementSuggestion, ProfileDocumentChunk, RoleProfile
from app.services.profile_cv_draft_service import CreateCvSuggestionRequest, ProfileCvDraftService
from app.services.scoring_service import extract_text_match_tokens


@dataclass(frozen=True)
class GenerateCvImprovementsRequest:
    role_profile_id: str
    job_id: str
    max_suggestions: int = 6


@dataclass(frozen=True)
class CvImprovementGenerationResult:
    job_id: str
    role_profile_id: str
    document_id: str
    version_id: str
    suggestions: list[ProfileCvImprovementSuggestion]


class ProfileCvJobImprovementService:
    def __init__(self, *, draft_service: ProfileCvDraftService | None = None) -> None:
        self.draft_service = draft_service or ProfileCvDraftService()

    async def generate_suggestions(
        self,
        session: AsyncSession,
        request: GenerateCvImprovementsRequest,
    ) -> CvImprovementGenerationResult:
        profile = await self._load_profile(session, request.role_profile_id)
        job = await self._load_job(session, role_profile_id=request.role_profile_id, job_id=request.job_id)
        if not profile.active_cv_document_id or not profile.active_cv_version_id:
            raise ValueError("Generating CV improvements requires an active CV.")

        chunks = await self._load_active_cv_chunks(session, profile)
        if not chunks:
            raise ValueError("Generating CV improvements requires indexed active CV chunks.")

        requirements = self._job_requirements(job)[: request.max_suggestions]
        if not requirements:
            raise ValueError("Job does not contain enough requirements for CV improvement suggestions.")

        suggestions: list[ProfileCvImprovementSuggestion] = []
        existing_requirements = await self._existing_requirements(
            session,
            role_profile_id=request.role_profile_id,
            job_id=request.job_id,
        )
        for requirement in requirements:
            if requirement.casefold() in existing_requirements:
                continue
            evidence = self._best_evidence(requirement, chunks)
            suggestion_request = self._build_suggestion_request(
                profile=profile,
                job=job,
                requirement=requirement,
                evidence=evidence,
            )
            suggestions.append(await self.draft_service.create_suggestion(session, suggestion_request))

        return CvImprovementGenerationResult(
            job_id=job.id,
            role_profile_id=profile.id,
            document_id=profile.active_cv_document_id,
            version_id=profile.active_cv_version_id,
            suggestions=suggestions,
        )

    async def _load_profile(self, session: AsyncSession, role_profile_id: str) -> RoleProfile:
        profile = await session.get(RoleProfile, role_profile_id)
        if profile is None:
            raise LookupError("Role profile not found")
        return profile

    async def _load_job(self, session: AsyncSession, *, role_profile_id: str, job_id: str) -> JobPost:
        result = await session.execute(
            select(JobPost)
            .where(JobPost.id == job_id)
            .where(JobPost.role_profile_id == role_profile_id)
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise LookupError("Job not found")
        return job

    async def _load_active_cv_chunks(self, session: AsyncSession, profile: RoleProfile) -> list[ProfileDocumentChunk]:
        result = await session.execute(
            select(ProfileDocumentChunk)
            .where(ProfileDocumentChunk.role_profile_id == profile.id)
            .where(ProfileDocumentChunk.document_id == profile.active_cv_document_id)
            .where(ProfileDocumentChunk.version_id == profile.active_cv_version_id)
            .order_by(ProfileDocumentChunk.chunk_index.asc(), ProfileDocumentChunk.id.asc())
        )
        return list(result.scalars())

    async def _existing_requirements(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        job_id: str,
    ) -> set[str]:
        result = await session.execute(
            select(ProfileCvImprovementSuggestion.requirement)
            .where(ProfileCvImprovementSuggestion.role_profile_id == role_profile_id)
            .where(ProfileCvImprovementSuggestion.job_id == job_id)
        )
        return {str(value).casefold() for value in result.scalars()}

    def _job_requirements(self, job: JobPost) -> list[str]:
        raw_items: list[str] = []
        raw_items.extend(self._parse_json_or_lines(job.skills))
        raw_items.extend(self._parse_json_or_lines(job.requirements))
        raw_items.extend(self._parse_json_or_lines(job.responsibilities))

        seen: set[str] = set()
        requirements: list[str] = []
        for item in raw_items:
            cleaned = re.sub(r"\s+", " ", item).strip(" -:\t")
            if len(cleaned) < 3:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            requirements.append(cleaned)
        return requirements

    def _parse_json_or_lines(self, value: str | None) -> list[str]:
        if not value:
            return []
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except ValueError:
            return [part.strip() for part in re.split(r"[\n;,]", raw) if part.strip()]
        if isinstance(parsed, list):
            return [str(part).strip() for part in parsed if str(part).strip()]
        return [str(parsed).strip()] if str(parsed).strip() else []

    def _best_evidence(self, requirement: str, chunks: list[ProfileDocumentChunk]) -> str | None:
        tokens = self._tokens(requirement)
        if not tokens:
            return None
        best_chunk: ProfileDocumentChunk | None = None
        best_score = 0
        for chunk in chunks:
            chunk_tokens = self._tokens(chunk.text)
            score = len(tokens & chunk_tokens)
            if score > best_score:
                best_score = score
                best_chunk = chunk
        if best_chunk is None or best_score == 0:
            return None
        return best_chunk.text[:600].strip()

    def _tokens(self, value: str) -> set[str]:
        return extract_text_match_tokens(value)

    def _build_suggestion_request(
        self,
        *,
        profile: RoleProfile,
        job: JobPost,
        requirement: str,
        evidence: str | None,
    ) -> CreateCvSuggestionRequest:
        if evidence:
            return CreateCvSuggestionRequest(
                role_profile_id=profile.id,
                document_id=profile.active_cv_document_id,
                version_id=profile.active_cv_version_id,
                job_id=job.id,
                requirement=requirement,
                current_cv_evidence=evidence,
                missing_or_weak_evidence="The active CV contains related evidence, but it may not emphasize this requirement strongly enough.",
                proposed_edit=f"Rewrite the relevant CV bullet to emphasize existing evidence for: {requirement}.",
                edit_kind="wording_only",
                risk_level="low",
                requires_confirmation=True,
            )
        return CreateCvSuggestionRequest(
            role_profile_id=profile.id,
            document_id=profile.active_cv_document_id,
            version_id=profile.active_cv_version_id,
            job_id=job.id,
            requirement=requirement,
            current_cv_evidence="No matching evidence was found in the active CV extracted text.",
            missing_or_weak_evidence="This requirement appears in the job, but the active CV does not provide supporting evidence.",
            proposed_edit=f"Ask the user for real experience or proof before adding anything about: {requirement}.",
            edit_kind="requires_user_fact",
            risk_level="high",
            requires_confirmation=True,
        )
