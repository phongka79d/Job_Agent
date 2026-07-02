# Profile CV Job-Scoring Improvement Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn scored jobs into grounded CV improvement suggestions, let users approve wording-only suggestions into drafts, and verify the full path from Review Queue job score to exported CV PDF version.

**Architecture:** Reuse the existing scored `JobPost` rows, active CV version pointers, profile document chunks, CV suggestion table, draft service, export service, chat tool-call events, and Review/Profile frontend surfaces. Add one focused orchestration service that maps score gaps and job requirements to active CV evidence; expose it through a thin job route and a visible agent tool without inventing CV facts or auto-modifying PDFs.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, SQLite, existing profile document Qdrant indexing/retrieval, React, TypeScript, Vitest, pytest, existing API contract exporter.

---

## Source Inputs

- Spec: `docs/superpowers/specs/2026-07-01-profile-cv-pdf-source-of-truth-design.md`
- Roadmap: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-roadmap.md`
- Phase 3: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-3.md`
- Phase 4: `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-4.md`

## Current Baseline

Already available:

- `JobPost` score fields:
  - `embedding_similarity`
  - `skill_overlap_score`
  - `location_match_score`
  - `level_match_score`
  - `base_score`
  - `jd_confidence_multiplier`
  - `final_score`
  - `final_score_percent`
- Active CV source-of-truth pointers:
  - `RoleProfile.active_cv_document_id`
  - `RoleProfile.active_cv_version_id`
  - `ProfileDocument.active_version_id`
- Version-aware CV chunks in `profile_document_chunks`.
- `ProfileCvImprovementSuggestion` table.
- `ProfileCvDraftService` for suggestions, drafts, and draft previews.
- `ProfileCvExportService` for exporting drafts to real PDF versions.
- Profile document frontend panel showing suggestions, drafts, versions, export, view, download, and active version controls.
- Chat tool-call event persistence and frontend visible tool-call timeline.

## Phase 5 Scope

Implement:

- deterministic score-gap to CV suggestion generation
- evidence mapping from active CV chunks to each job requirement
- storage of both wording-only and user-fact-required suggestions
- draft creation only from approved wording-only suggestions
- API route for Review Queue to generate CV suggestions for a scored job
- tool: `score_cv_against_job`
- visible chat tool call for job/CV improvement requests that include a job id
- Review Queue controls to generate suggestions and create a draft from approved wording-only suggestions
- contract regeneration for the new route/schemas
- end-to-end backend test from scored job to suggestions, draft, exported PDF version, and non-activation

Do not implement:

- OCR
- pixel-perfect editing of arbitrary uploaded PDFs
- automatic CV draft creation without confirmation
- automatic PDF export from suggestions
- automatic active CV promotion
- any new demo/mock runtime data
- any new persistent tables

## File Structure

Create:

- `backend/app/services/profile_cv_job_improvement_service.py`
  - Owns score-gap analysis and CV suggestion generation for one scored job and one active CV version.
- `backend/tests/test_profile_cv_job_improvement_service.py`
  - Unit tests for deterministic evidence mapping, fact-required suggestions, no-active-CV behavior, and no-fabrication behavior.

Modify:

- `backend/app/services/profile_cv_draft_service.py`
  - Allow storing `requires_user_fact` suggestions, while continuing to block drafting those suggestions.
- `backend/app/api/schemas.py`
  - Add job-CV improvement request/response schemas.
- `backend/app/api/routes_jobs.py`
  - Add `POST /api/jobs/{id}/cv-improvements`.
- `backend/app/services/tool_registry.py`
  - Register and implement `score_cv_against_job`.
- `backend/app/api/routes_chat.py`
  - Wire the new tool and add a narrow intent path for messages that include a job id.
- `backend/app/agents/chat_prompts.py`
  - Clarify that job-scoring CV improvement must use tools and must not invent CV facts.
- `backend/scripts/export_api_contract.py`
  - Add the new endpoint and schemas.
- `backend/tests/test_profile_cv_draft_service.py`
  - Update expectations for storing fact-required suggestions and rejecting drafts that use them.
- `backend/tests/test_routes_jobs.py`
  - Route tests for job scoping and generated suggestions.
- `backend/tests/test_tool_registry.py`
  - Tool definition, handler, and safe payload tests.
- `backend/tests/test_routes_chat.py`
  - Visible tool-call path for job/CV improvement messages.
- `backend/tests/test_api_contract_export.py`
  - Existing contract test should pass after exporter updates and regenerated contract.
- `shared/api-contract.json`
  - Regenerated by `backend/scripts/export_api_contract.py`.
- `frontend/job-agent-ui/src/types/api.ts`
  - Add job-CV improvement response types.
- `frontend/job-agent-ui/src/api/client.ts`
  - Add `generateJobCvImprovements(...)`.
- `frontend/job-agent-ui/src/components/JobCard.tsx`
  - Add Review Queue CV improvement controls and suggestion rendering.
- `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
  - Pass active profile and generation callbacks into job cards.
- `frontend/job-agent-ui/src/styles/app.css`
  - Add small job-card suggestion styles.
- `frontend/job-agent-ui/src/test/apiContract.test.ts`
  - Add endpoint/schema expectations if the test explicitly lists known client endpoints.
- `frontend/job-agent-ui/src/test/JobCard.test.tsx`
  - Button, suggestion rendering, and draft confirmation tests.
- `frontend/job-agent-ui/src/test/ReviewPage.test.tsx`
  - Review page integration test for generating suggestions.
- `frontend/job-agent-ui/src/test/apiClient.test.ts`
  - API client test for `generateJobCvImprovements(...)`.

No database migration is required in this phase.

---

### Task 1: Tighten Suggestion Safety Rules

**Files:**

- Modify: `backend/app/services/profile_cv_draft_service.py`
- Test: `backend/tests/test_profile_cv_draft_service.py`

- [ ] **Step 1: Write failing tests for fact-required suggestion storage and draft blocking**

Append these tests to `backend/tests/test_profile_cv_draft_service.py`. Reuse the existing `create_cv(...)` helper already defined in that file:

```python
import pytest
from sqlalchemy import select

from app.db.models import ProfileCvImprovementSuggestion
from app.services.profile_cv_draft_service import CreateCvDraftRequest, CreateCvSuggestionRequest, ProfileCvDraftService


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
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_draft_service.py -q
```

Expected: FAIL because `create_suggestion(...)` currently rejects `requires_user_fact` suggestions before they can be stored, or because fixture names need to be aligned before the safety rule exists.

- [ ] **Step 3: Update suggestion creation and draft loading**

Modify `ProfileCvDraftService.create_suggestion(...)` in `backend/app/services/profile_cv_draft_service.py` so it validates both supported edit kinds instead of rejecting `requires_user_fact` immediately:

```python
        if request.risk_level not in {"low", "medium", "high"}:
            raise ValueError("risk_level must be low, medium, or high")
        if request.edit_kind not in {"wording_only", "requires_user_fact"}:
            raise ValueError("edit_kind must be wording_only or requires_user_fact")
```

Modify `_load_suggestions(...)` before returning ordered suggestions:

```python
        suggestions = [by_id[suggestion_id] for suggestion_id in suggestion_ids]
        fact_required = [suggestion for suggestion in suggestions if suggestion.edit_kind == "requires_user_fact"]
        if fact_required:
            raise ValueError("Suggestion requires user-provided facts before drafting.")
        high_risk = [suggestion for suggestion in suggestions if suggestion.risk_level == "high"]
        if high_risk:
            raise ValueError("High-risk CV suggestions require manual user-provided facts before drafting.")
        return suggestions
```

Remove the old return line:

```python
        return [by_id[suggestion_id] for suggestion_id in suggestion_ids]
```

- [ ] **Step 4: Run the focused draft-service tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_draft_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```powershell
git add backend/app/services/profile_cv_draft_service.py backend/tests/test_profile_cv_draft_service.py
git commit -m "fix: preserve fact-required cv suggestions"
```

---

### Task 2: Add Job-Scoring CV Improvement Service

**Files:**

- Create: `backend/app/services/profile_cv_job_improvement_service.py`
- Test: `backend/tests/test_profile_cv_job_improvement_service.py`

- [ ] **Step 1: Write failing service tests**

Create `backend/tests/test_profile_cv_job_improvement_service.py`:

```python
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
    other_profile_id = str(uuid4())
    job = JobPost(
        batch_id=str(uuid4()),
        role_profile_id=other_profile_id,
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
```

- [ ] **Step 2: Run the tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_job_improvement_service.py -q
```

Expected: FAIL because `profile_cv_job_improvement_service.py` does not exist.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/profile_cv_job_improvement_service.py`:

```python
"""Generate grounded CV improvement suggestions from scored jobs."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobPost, ProfileCvImprovementSuggestion, ProfileDocumentChunk, RoleProfile
from app.services.profile_cv_draft_service import CreateCvSuggestionRequest, ProfileCvDraftService


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
        stopwords = {"and", "or", "the", "with", "for", "to", "of", "in", "a", "an"}
        return {
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", value.casefold())
            if token not in stopwords
        }

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
```

- [ ] **Step 4: Run service tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_job_improvement_service.py tests/test_profile_cv_draft_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```powershell
git add backend/app/services/profile_cv_job_improvement_service.py backend/tests/test_profile_cv_job_improvement_service.py
git commit -m "feat: generate cv suggestions from scored jobs"
```

---

### Task 3: Add Job API Route And Contract Schemas

**Files:**

- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/api/routes_jobs.py`
- Modify: `backend/scripts/export_api_contract.py`
- Modify: `shared/api-contract.json`
- Test: `backend/tests/test_routes_jobs.py`
- Test: `backend/tests/test_api_contract_export.py`

- [ ] **Step 1: Write failing route test**

Append to `backend/tests/test_routes_jobs.py`:

```python
async def test_generate_job_cv_improvements_returns_grounded_suggestions(client, db_session):
    import json

    from app.db.models import ProfileDocument, ProfileDocumentChunk, ProfileDocumentVersion

    profile = await create_profile(db_session)
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
    document.active_version_id = version.id
    profile.active_cv_document_id = document.id
    profile.active_cv_version_id = version.id
    db_session.add(
        ProfileDocumentChunk(
            role_profile_id=profile.id,
            document_id=document.id,
            version_id=version.id,
            source_type="profile_cv",
            chunk_index=0,
            text="Built FastAPI APIs and LangGraph workflows.",
            token_count=8,
            qdrant_point_id="point-route-1",
        )
    )
    job = await create_job(
        db_session,
        profile,
        final_score=0.7,
    )
    job.requirements = "FastAPI\nAWS"
    job.skills = json.dumps(["FastAPI", "AWS"])
    job.skill_overlap_score = 0.5
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = await client.post(
        f"/api/jobs/{job.id}/cv-improvements",
        json={"role_profile_id": profile.id, "max_suggestions": 4},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == job.id
    assert body["document_id"] == document.id
    assert body["version_id"] == version.id
    assert body["suggestion_count"] >= 1
    assert any(item["edit_kind"] == "wording_only" for item in body["suggestions"])
    assert any(item["edit_kind"] == "requires_user_fact" for item in body["suggestions"])
```

- [ ] **Step 2: Run the route test and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_routes_jobs.py::test_generate_job_cv_improvements_returns_grounded_suggestions -q
```

Expected: FAIL because the route does not exist.

- [ ] **Step 3: Add schemas**

In `backend/app/api/schemas.py`, add after `CvImprovementSuggestionListResponse`:

```python
class GenerateJobCvImprovementsRequest(ApiSchema):
    role_profile_id: UUID
    max_suggestions: int = Field(default=6, ge=1, le=12)


class GenerateJobCvImprovementsResponse(ApiSchema):
    job_id: UUID
    role_profile_id: UUID
    document_id: UUID
    version_id: UUID
    suggestion_count: int
    suggestions: list[CvImprovementSuggestionResponse] = Field(default_factory=list)
```

- [ ] **Step 4: Add route**

In `backend/app/api/routes_jobs.py`, extend schema imports:

```python
    GenerateJobCvImprovementsRequest,
    GenerateJobCvImprovementsResponse,
```

Add service imports:

```python
from app.services.profile_cv_job_improvement_service import GenerateCvImprovementsRequest, ProfileCvJobImprovementService
```

Add singleton near `router = APIRouter(...)`:

```python
profile_cv_job_improvement_service = ProfileCvJobImprovementService()
```

Add route before `@router.get("/{id}", response_model=JobResponse)`:

```python
@router.post(
    "/{id}/cv-improvements",
    response_model=GenerateJobCvImprovementsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_job_cv_improvements(
    id: UUID,
    request: GenerateJobCvImprovementsRequest,
    session: SessionDep,
) -> GenerateJobCvImprovementsResponse:
    try:
        result = await profile_cv_job_improvement_service.generate_suggestions(
            session,
            GenerateCvImprovementsRequest(
                role_profile_id=str(request.role_profile_id),
                job_id=str(id),
                max_suggestions=request.max_suggestions,
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return GenerateJobCvImprovementsResponse(
        job_id=result.job_id,
        role_profile_id=result.role_profile_id,
        document_id=result.document_id,
        version_id=result.version_id,
        suggestion_count=len(result.suggestions),
        suggestions=result.suggestions,
    )
```

- [ ] **Step 5: Update API contract exporter**

In `backend/scripts/export_api_contract.py`, import the new schemas:

```python
    GenerateJobCvImprovementsRequest,
    GenerateJobCvImprovementsResponse,
```

Add endpoint to `ENDPOINTS`:

```python
    "generateJobCvImprovements": {
        "method": "POST",
        "path": "/api/jobs/{id}/cv-improvements",
        "request_schema": "GenerateJobCvImprovementsRequest",
        "response_schema": "GenerateJobCvImprovementsResponse",
    },
```

Add schemas to `SCHEMA_MODELS`:

```python
    GenerateJobCvImprovementsRequest,
    GenerateJobCvImprovementsResponse,
```

Regenerate the contract:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe scripts\export_api_contract.py
```

Expected: `shared/api-contract.json` updates.

- [ ] **Step 6: Run route and contract tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_routes_jobs.py::test_generate_job_cv_improvements_returns_grounded_suggestions tests/test_api_contract_export.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```powershell
git add backend/app/api/schemas.py backend/app/api/routes_jobs.py backend/scripts/export_api_contract.py shared/api-contract.json backend/tests/test_routes_jobs.py
git commit -m "feat: expose job cv improvement generation"
```

---

### Task 4: Add Agent Tool And Visible Chat Path

**Files:**

- Modify: `backend/app/services/tool_registry.py`
- Modify: `backend/app/api/routes_chat.py`
- Modify: `backend/app/agents/chat_prompts.py`
- Test: `backend/tests/test_tool_registry.py`
- Test: `backend/tests/test_routes_chat.py`

- [ ] **Step 1: Write failing tool tests**

Append to `backend/tests/test_tool_registry.py`:

```python
def test_score_cv_against_job_tool_is_registered_without_confirmation():
    tools = ToolRegistry().list_tools()

    assert "score_cv_against_job" in tools
    assert tools["score_cv_against_job"].requires_confirmation is False


@pytest.mark.asyncio
async def test_score_cv_against_job_tool_returns_safe_payload():
    from app.services.tool_registry import ToolRequest, build_score_cv_against_job_handler

    class ImprovementService:
        async def generate_suggestions(self, session, request):
            class Suggestion:
                id = "suggestion-1"
                edit_kind = "wording_only"
                risk_level = "low"
                status = "suggested"

            class Result:
                job_id = request.job_id
                role_profile_id = request.role_profile_id
                document_id = "doc-1"
                version_id = "version-1"
                suggestions = [Suggestion()]

            return Result()

    result = await build_score_cv_against_job_handler(ImprovementService(), object())(
        ToolRequest(
            name="score_cv_against_job",
            arguments={"job_id": "job-1", "max_suggestions": 4},
            context={"role_profile_id": "profile-1"},
        )
    )

    assert result.result_summary == "Generated 1 CV improvement suggestion"
    assert result.safe_payload == {
        "job_id": "job-1",
        "document_id": "doc-1",
        "version_id": "version-1",
        "suggestion_count": 1,
        "wording_only_count": 1,
        "requires_user_fact_count": 0,
    }
```

- [ ] **Step 2: Run tool tests and verify failure**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py::test_score_cv_against_job_tool_is_registered_without_confirmation tests/test_tool_registry.py::test_score_cv_against_job_tool_returns_safe_payload -q
```

Expected: FAIL because the tool is not registered.

- [ ] **Step 3: Register the tool and handler**

In `backend/app/services/tool_registry.py`, import:

```python
from app.services.profile_cv_job_improvement_service import GenerateCvImprovementsRequest
```

Add to `ToolRegistry.__init__`:

```python
            "score_cv_against_job": ToolDefinition(
                name="score_cv_against_job",
                description="Generate grounded CV improvement suggestions for one scored job using the active CV.",
                requires_confirmation=False,
                handler=_not_wired,
            ),
```

Add handler near the other CV tool handlers:

```python
def build_score_cv_against_job_handler(
    improvement_service: object,
    session: object,
) -> ToolHandler:
    async def handler(request: ToolRequest) -> ToolResult:
        job_id = str(request.arguments["job_id"])
        result = await improvement_service.generate_suggestions(
            session,
            GenerateCvImprovementsRequest(
                role_profile_id=str(request.context["role_profile_id"]),
                job_id=job_id,
                max_suggestions=int(request.arguments.get("max_suggestions", 6)),
            ),
        )
        wording_only_count = sum(1 for suggestion in result.suggestions if suggestion.edit_kind == "wording_only")
        requires_user_fact_count = sum(
            1 for suggestion in result.suggestions if suggestion.edit_kind == "requires_user_fact"
        )
        suggestion_word = "suggestion" if len(result.suggestions) == 1 else "suggestions"
        return ToolResult(
            content=(
                f"Generated {len(result.suggestions)} grounded CV improvement {suggestion_word}. "
                "Wording-only suggestions may be drafted after confirmation. "
                "Fact-required suggestions need user-provided facts."
            ),
            result_summary=f"Generated {len(result.suggestions)} CV improvement {suggestion_word}",
            safe_payload={
                "job_id": result.job_id,
                "document_id": result.document_id,
                "version_id": result.version_id,
                "suggestion_count": len(result.suggestions),
                "wording_only_count": wording_only_count,
                "requires_user_fact_count": requires_user_fact_count,
            },
        )

    return handler
```

- [ ] **Step 4: Wire chat registry and add narrow UUID intent**

In `backend/app/api/routes_chat.py`, import:

```python
import re
from app.services.profile_cv_job_improvement_service import ProfileCvJobImprovementService
```

Extend tool imports:

```python
    build_score_cv_against_job_handler,
```

Add singleton:

```python
profile_cv_job_improvement_service = ProfileCvJobImprovementService()
```

Add registry override:

```python
            "score_cv_against_job": build_score_cv_against_job_handler(profile_cv_job_improvement_service, session),
```

Add helper near the intent helpers:

```python
JOB_ID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _job_cv_improvement_intent(content: str) -> str | None:
    normalized = content.casefold()
    if "cv" not in normalized and "resume" not in normalized:
        return None
    if "job" not in normalized and "role" not in normalized:
        return None
    if not any(term in normalized for term in ("improve", "score", "match", "missing", "suggest")):
        return None
    match = JOB_ID_PATTERN.search(content)
    return match.group(0) if match else None
```

Add a branch in `event_generator()` before `_is_profile_cv_read_intent(...)`:

```python
        elif job_id := _job_cv_improvement_intent(user_message.content):
            tool_call = await agent_event_service.create_tool_call(
                session,
                conversation_id=str(conversation_id),
                tool_name="score_cv_against_job",
                input_summary=f"Generate CV improvements for job {job_id}",
                safe_payload={"job_id": job_id},
            )
            tool_call = await agent_event_service.mark_running(session, tool_call.id)
            yield _sse_event(
                "tool_call_started",
                {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status,
                    "input_summary": tool_call.input_summary,
                },
            )
            try:
                tool_result = await build_tool_registry(session).execute(
                    ToolRequest(
                        name="score_cv_against_job",
                        arguments={"job_id": job_id, "max_suggestions": 6},
                        context={
                            "role_profile_id": conversation.role_profile_id,
                            "conversation_id": str(conversation_id),
                        },
                    )
                )
            except Exception:
                logger.exception("score_cv_against_job tool failed")
                tool_call = await agent_event_service.mark_failed(
                    session,
                    tool_call.id,
                    error_message="CV improvement generation failed. Check that the job belongs to this profile and an active CV is selected.",
                )
                assistant_content = (
                    "Called 1 tool: Score CV against job, but it failed. "
                    "Check that the job belongs to this profile and an active CV is selected."
                )
                agent_metadata_source = "chat_agent_tool_error"
                yield _sse_event(
                    "tool_call_failed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "error_message": tool_call.error_message,
                    },
                )
            else:
                tool_call = await agent_event_service.mark_success(
                    session,
                    tool_call.id,
                    result_summary=tool_result.result_summary,
                    safe_payload=tool_result.safe_payload,
                )
                assistant_content = (
                    "Called 1 tool: Score CV against job. "
                    f"{tool_result.result_summary}. Open the Review Queue or Profile CV panel to inspect suggestions."
                )
                agent_metadata_source = "chat_agent_tool"
                yield _sse_event(
                    "tool_call_completed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "result_summary": tool_call.result_summary,
                        "safe_payload": tool_result.safe_payload,
                    },
                )
```

- [ ] **Step 5: Update chat prompt**

In `backend/app/agents/chat_prompts.py`, replace the prompt body with:

```python
CHAT_AGENT_SYSTEM_PROMPT = """You are an AI Job Agent.
Use tools for factual job data, profile document retrieval, job status changes, job ingestion, and CV improvement generation.
Do not invent job listings, scores, CV facts, companies, schools, dates, certifications, projects, metrics, or responsibilities.
When improving a CV for a job, distinguish original PDF, extracted text, editable draft, and exported PDF version.
Ask for confirmation before profile updates, CV draft creation, CV PDF export, active CV changes, job status changes, deletions, or bulk modifications.
Keep answers concise and cite visible tool results when relevant."""
```

- [ ] **Step 6: Run focused chat/tool tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py tests/test_routes_chat.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```powershell
git add backend/app/services/tool_registry.py backend/app/api/routes_chat.py backend/app/agents/chat_prompts.py backend/tests/test_tool_registry.py backend/tests/test_routes_chat.py
git commit -m "feat: add visible job cv improvement tool"
```

---

### Task 5: Add Review Queue CV Improvement UI

**Files:**

- Modify: `frontend/job-agent-ui/src/types/api.ts`
- Modify: `frontend/job-agent-ui/src/api/client.ts`
- Modify: `frontend/job-agent-ui/src/components/JobCard.tsx`
- Modify: `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
- Modify: `frontend/job-agent-ui/src/styles/app.css`
- Test: `frontend/job-agent-ui/src/test/apiClient.test.ts`
- Test: `frontend/job-agent-ui/src/test/JobCard.test.tsx`
- Test: `frontend/job-agent-ui/src/test/ReviewPage.test.tsx`

- [ ] **Step 1: Write failing API client test**

Append to `frontend/job-agent-ui/src/test/apiClient.test.ts`:

```typescript
import { generateJobCvImprovements } from "../api/client";

it("generates CV improvements for a scored job", async () => {
  postSpy.mockResolvedValueOnce({
    data: {
      job_id: "job-1",
      role_profile_id: "profile-1",
      document_id: "doc-1",
      version_id: "version-1",
      suggestion_count: 1,
      suggestions: [
        {
          id: "suggestion-1",
          role_profile_id: "profile-1",
          document_id: "doc-1",
          version_id: "version-1",
          job_id: "job-1",
          requirement: "FastAPI",
          current_cv_evidence: "Built FastAPI APIs.",
          missing_or_weak_evidence: "Could be emphasized more clearly.",
          proposed_edit: "Rewrite the relevant bullet to emphasize FastAPI.",
          edit_kind: "wording_only",
          risk_level: "low",
          requires_confirmation: true,
          status: "suggested",
          created_at: "2026-07-02T00:00:00Z",
          updated_at: "2026-07-02T00:00:00Z",
        },
      ],
    },
  });

  const result = await generateJobCvImprovements("job-1", { role_profile_id: "profile-1", max_suggestions: 4 });

  expect(postSpy).toHaveBeenCalledWith("/api/jobs/job-1/cv-improvements", {
    role_profile_id: "profile-1",
    max_suggestions: 4,
  });
  expect(result.suggestion_count).toBe(1);
});
```

- [ ] **Step 2: Add frontend types and API client**

In `frontend/job-agent-ui/src/types/api.ts`, add:

```typescript
export type CvSuggestionEditKind = "wording_only" | "requires_user_fact";
export type CvSuggestionRiskLevel = "low" | "medium" | "high";

export interface JobCvImprovementSuggestion {
  id: string;
  role_profile_id: string;
  document_id: string;
  version_id: string;
  job_id: string | null;
  requirement: string;
  current_cv_evidence: string;
  missing_or_weak_evidence: string;
  proposed_edit: string;
  edit_kind: CvSuggestionEditKind;
  risk_level: CvSuggestionRiskLevel;
  requires_confirmation: boolean;
  status: "suggested" | "accepted" | "rejected" | "drafted";
  created_at: string;
  updated_at: string;
}

export interface GenerateJobCvImprovementsRequest {
  role_profile_id: string;
  max_suggestions?: number;
}

export interface GenerateJobCvImprovementsResponse {
  job_id: string;
  role_profile_id: string;
  document_id: string;
  version_id: string;
  suggestion_count: number;
  suggestions: JobCvImprovementSuggestion[];
}
```

In `frontend/job-agent-ui/src/api/client.ts`, import the new types and add:

```typescript
export async function generateJobCvImprovements(
  id: string,
  request: GenerateJobCvImprovementsRequest
): Promise<GenerateJobCvImprovementsResponse> {
  try {
    const response = await apiClient.post<GenerateJobCvImprovementsResponse>(
      `/api/jobs/${id}/cv-improvements`,
      request
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
```

- [ ] **Step 3: Write failing JobCard UI test**

Append to `frontend/job-agent-ui/src/test/JobCard.test.tsx`:

```tsx
it("renders CV improvement suggestions and draft action", async () => {
  const onGenerateCvImprovements = vi.fn();
  const onCreateCvDraft = vi.fn();

  render(
    <JobCard
      job={scoredJob}
      onGenerateCvImprovements={onGenerateCvImprovements}
      onCreateCvDraft={onCreateCvDraft}
      cvImprovementResult={{
        job_id: scoredJob.id,
        role_profile_id: scoredJob.role_profile_id,
        document_id: "doc-1",
        version_id: "version-1",
        suggestion_count: 2,
        suggestions: [
          {
            id: "suggestion-1",
            role_profile_id: scoredJob.role_profile_id,
            document_id: "doc-1",
            version_id: "version-1",
            job_id: scoredJob.id,
            requirement: "FastAPI",
            current_cv_evidence: "Built FastAPI APIs.",
            missing_or_weak_evidence: "Could be emphasized more clearly.",
            proposed_edit: "Rewrite the relevant bullet to emphasize FastAPI.",
            edit_kind: "wording_only",
            risk_level: "low",
            requires_confirmation: true,
            status: "suggested",
            created_at: "2026-07-02T00:00:00Z",
            updated_at: "2026-07-02T00:00:00Z",
          },
          {
            id: "suggestion-2",
            role_profile_id: scoredJob.role_profile_id,
            document_id: "doc-1",
            version_id: "version-1",
            job_id: scoredJob.id,
            requirement: "AWS",
            current_cv_evidence: "No matching evidence was found in the active CV extracted text.",
            missing_or_weak_evidence: "Requires user-provided facts.",
            proposed_edit: "Ask the user for real experience or proof before adding anything about AWS.",
            edit_kind: "requires_user_fact",
            risk_level: "high",
            requires_confirmation: true,
            status: "suggested",
            created_at: "2026-07-02T00:00:00Z",
            updated_at: "2026-07-02T00:00:00Z",
          },
        ],
      }}
    />
  );

  expect(screen.getByText("CV improvement suggestions")).toBeInTheDocument();
  expect(screen.getByText("FastAPI")).toBeInTheDocument();
  expect(screen.getByText("Requires user facts")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /create cv draft/i }));
  expect(onCreateCvDraft).toHaveBeenCalledWith(scoredJob.id);
});
```

- [ ] **Step 4: Add JobCard props and rendering**

In `frontend/job-agent-ui/src/components/JobCard.tsx`, import type:

```typescript
import type { GenerateJobCvImprovementsResponse } from "../types/api";
```

Extend `JobCardProps`:

```typescript
  cvImprovementResult?: GenerateJobCvImprovementsResponse;
  onGenerateCvImprovements?: (id: string) => void | Promise<void>;
  onCreateCvDraft?: (id: string) => void | Promise<void>;
  isCvImprovementLoading?: boolean;
```

Add props to the function destructuring:

```typescript
  cvImprovementResult,
  onGenerateCvImprovements,
  onCreateCvDraft,
  isCvImprovementLoading = false,
```

Add a button inside `.job-card-actions` after the Breakdown button:

```tsx
          {onGenerateCvImprovements ? (
            <button
              type="button"
              onClick={() => onGenerateCvImprovements(job.id)}
              disabled={isCvImprovementLoading}
              className="btn-secondary"
            >
              <span>{isCvImprovementLoading ? "Generating..." : "Improve CV"}</span>
            </button>
          ) : null}
```

Render suggestions before the closing `</div>` of `.job-card`:

```tsx
      {cvImprovementResult ? (
        <div className="job-cv-suggestions">
          <div className="job-cv-suggestions-header">
            <strong>CV improvement suggestions</strong>
            {cvImprovementResult.suggestions.some((suggestion) => suggestion.edit_kind === "wording_only") &&
            onCreateCvDraft ? (
              <button type="button" className="btn-secondary" onClick={() => onCreateCvDraft(job.id)}>
                Create CV draft
              </button>
            ) : null}
          </div>
          {cvImprovementResult.suggestions.map((suggestion) => (
            <article key={suggestion.id} className="job-cv-suggestion">
              <div>
                <strong>{suggestion.requirement}</strong>
                <span>{suggestion.proposed_edit}</span>
              </div>
              <small>
                {suggestion.edit_kind === "requires_user_fact" ? "Requires user facts" : "Wording only"} - {suggestion.risk_level}
              </small>
            </article>
          ))}
        </div>
      ) : null}
```

- [ ] **Step 5: Wire ReviewPage generation and draft creation**

In `frontend/job-agent-ui/src/pages/ReviewPage.tsx`, import:

```typescript
import { createCvDraft } from "../api/profileDocumentsClient";
import { generateJobCvImprovements, getReviewJobs, approveJob, rejectJob } from "../api/client";
import type { GenerateJobCvImprovementsResponse } from "../types/api";
```

Add state:

```typescript
  const [cvImprovementByJob, setCvImprovementByJob] = useState<Record<string, GenerateJobCvImprovementsResponse>>({});
```

Add handlers:

```typescript
  const handleGenerateCvImprovements = async (jobId: string) => {
    if (!activeProfileId) return;
    setActionLoading((prev) => ({ ...prev, [`cv-${jobId}`]: true }));
    setError(null);
    try {
      const result = await generateJobCvImprovements(jobId, {
        role_profile_id: activeProfileId,
        max_suggestions: 6,
      });
      setCvImprovementByJob((prev) => ({ ...prev, [jobId]: result }));
    } catch (err: any) {
      setError(err.message || "Failed to generate CV improvements.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`cv-${jobId}`]: false }));
    }
  };

  const handleCreateCvDraft = async (jobId: string) => {
    const improvement = cvImprovementByJob[jobId];
    if (!improvement) return;
    const wordingOnlySuggestionIds = improvement.suggestions
      .filter((suggestion) => suggestion.edit_kind === "wording_only")
      .map((suggestion) => suggestion.id);
    if (wordingOnlySuggestionIds.length === 0) {
      setError("No wording-only CV suggestions are available for drafting.");
      return;
    }
    const confirmed = window.confirm("Create a CV draft from wording-only suggestions? The original PDF will not change.");
    if (!confirmed) return;
    setActionLoading((prev) => ({ ...prev, [`draft-${jobId}`]: true }));
    setError(null);
    try {
      await createCvDraft(improvement.role_profile_id, improvement.document_id, improvement.version_id, {
        title: `CV draft for ${jobs.find((job) => job.id === jobId)?.title || "job"}`,
        suggestion_ids: wordingOnlySuggestionIds,
        confirmed: true,
      });
    } catch (err: any) {
      setError(err.message || "Failed to create CV draft.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`draft-${jobId}`]: false }));
    }
  };
```

Pass props into `JobCard`:

```tsx
              cvImprovementResult={cvImprovementByJob[job.id]}
              onGenerateCvImprovements={handleGenerateCvImprovements}
              onCreateCvDraft={handleCreateCvDraft}
              isCvImprovementLoading={Boolean(actionLoading[`cv-${job.id}`])}
```

- [ ] **Step 6: Add minimal CSS**

Append to `frontend/job-agent-ui/src/styles/app.css`:

```css
.job-cv-suggestions {
  border-top: 1px solid var(--border-subtle);
  margin-top: 12px;
  padding-top: 12px;
  display: grid;
  gap: 8px;
}

.job-cv-suggestions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.job-cv-suggestion {
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 8px;
  display: grid;
  gap: 4px;
}

.job-cv-suggestion strong,
.job-cv-suggestion span,
.job-cv-suggestion small {
  display: block;
}

.job-cv-suggestion small {
  color: var(--text-muted);
  font-size: 12px;
}
```

- [ ] **Step 7: Run frontend focused tests**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm test -- --run src/test/apiClient.test.ts src/test/JobCard.test.tsx src/test/ReviewPage.test.tsx src/test/apiContract.test.ts
npm run typecheck
```

Expected: PASS.

- [ ] **Step 8: Commit Task 5**

```powershell
git add frontend/job-agent-ui/src/types/api.ts frontend/job-agent-ui/src/api/client.ts frontend/job-agent-ui/src/components/JobCard.tsx frontend/job-agent-ui/src/pages/ReviewPage.tsx frontend/job-agent-ui/src/styles/app.css frontend/job-agent-ui/src/test/apiClient.test.ts frontend/job-agent-ui/src/test/JobCard.test.tsx frontend/job-agent-ui/src/test/ReviewPage.test.tsx frontend/job-agent-ui/src/test/apiContract.test.ts
git commit -m "feat: show scored job cv improvement workflow"
```

---

### Task 6: Add End-To-End Backend Workflow Test

**Files:**

- Test: `backend/tests/test_profile_cv_job_improvement_service.py`

- [ ] **Step 1: Add workflow test from scored job to exported PDF**

Append to `backend/tests/test_profile_cv_job_improvement_service.py`:

```python
@pytest.mark.asyncio
async def test_scored_job_to_draft_to_exported_pdf_keeps_active_cv_unchanged(
    db_session,
):
    import json
    from uuid import uuid4

    from app.db.models import JobPost, ProfileDocumentChunk
    from app.services.profile_cv_draft_service import CreateCvDraftRequest, ProfileCvDraftService
    from app.services.profile_cv_export_service import ExportCvDraftRequest, ProfileCvExportService

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

    export = await ProfileCvExportService().export_draft_to_pdf(
        db_session,
        ExportCvDraftRequest(
            role_profile_id=profile.id,
            document_id=document.id,
            draft_id=draft.id,
            confirmed=True,
            created_by="ai",
        ),
    )

    assert export.source_type == "exported_draft"
    assert export.draft_id == draft.id
    assert export.id != version.id
    await db_session.refresh(profile)
    await db_session.refresh(document)
    assert profile.active_cv_version_id == version.id
    assert document.active_version_id == version.id
```

- [ ] **Step 2: Run the workflow test**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m pytest tests/test_profile_cv_job_improvement_service.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit Task 6**

```powershell
git add backend/tests/test_profile_cv_job_improvement_service.py
git commit -m "test: verify scored job cv export workflow"
```

---

### Task 7: Full Verification And Plan Checkoff

**Files:**

- Modify: `docs/superpowers/plans/2026-07-02-profile-cv-pdf-source-of-truth-phase-5.md`

- [ ] **Step 1: Run backend verification**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Expected:

- compileall exits 0
- pytest exits 0
- pip check reports no broken requirements

- [ ] **Step 2: Run frontend verification**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Expected:

- lint exits 0
- typecheck exits 0
- tests exit 0
- build exits 0
- existing lint warnings are acceptable only if unchanged from earlier phases

- [ ] **Step 3: Run safety and stale-reference scans**

Run:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent
rg -n "score_cv_against_job|cv-improvements|GenerateJobCvImprovements|ProfileCvJobImprovementService" backend frontend shared docs
rg -n "invent|fabricate|api_key|OPENAI_API_KEY|TAVILY_API_KEY|stored_path|content_hash" backend\app frontend\job-agent-ui\src
git diff --check
git status --short
```

Expected:

- new route and tool names appear only in service, route, tests, API client, frontend UI, contract, and plan/docs
- safe payloads contain IDs, counts, statuses, and route metadata only
- no frontend code exposes stored paths, content hashes, API keys, or provider payloads
- anti-fabrication prompt text is present
- `git diff --check` exits 0
- `git status --short` shows only the plan checkoff before the final commit

- [ ] **Step 4: Manually verify the Phase 5 flow**

Start backend and frontend:

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host localhost --port 8000
```

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run dev -- --host localhost --port 5173
```

Manual flow:

1. Open `http://localhost:5173`.
2. Select a role profile with an active text-based CV.
3. Ensure the Review Queue contains a scored job.
4. Click `Improve CV` on the job card.
5. Confirm suggestions render under the job card.
6. Confirm suggestions with missing evidence are labeled as requiring user facts.
7. Click `Create CV draft`.
8. Confirm the original PDF remains unchanged.
9. Open the Profile CV panel and confirm the draft appears.
10. Export the draft to PDF.
11. View and download the exported PDF version.
12. Confirm the exported version is not active until `Set active` is clicked and confirmed.
13. In chat, send a message containing the job id, for example `Improve my CV for job <job-id>`.
14. Confirm the visible tool-call timeline shows `score_cv_against_job`.

- [ ] **Step 5: Check off completed tasks and commit the plan update**

After every task above is complete and verified, update this plan file by changing each completed checkbox from `- [ ]` to `- [x]`.

Commit:

```powershell
git add docs/superpowers/plans/2026-07-02-profile-cv-pdf-source-of-truth-phase-5.md
git commit -m "docs: complete profile cv job improvement phase"
```

## Acceptance Criteria

- `requires_user_fact` suggestions can be stored and displayed.
- `requires_user_fact` and `high` risk suggestions cannot be drafted.
- Job/CV improvement generation requires:
  - job belongs to the selected role profile
  - active CV document exists
  - active CV version exists
  - active CV chunks exist
  - job contains extractable requirements or skills
- Each generated suggestion includes:
  - job requirement
  - current CV evidence
  - missing or weak evidence
  - proposed edit
  - edit kind
  - risk level
  - confirmation requirement
- The AI/tool flow never fabricates CV facts.
- The `score_cv_against_job` safe payload does not include raw full CV text.
- Review Queue can generate and display CV suggestions for a scored job.
- Review Queue can create a draft from wording-only suggestions after confirmation.
- Draft export still creates a real PDF version and does not activate it.
- Full backend and frontend verification passes.

## Risks And Guardrails

- Deterministic keyword evidence matching is intentionally conservative. It should prefer asking for user facts over inventing missing evidence.
- This phase should not add a new LLM call for CV rewriting. The first production-safe version stores grounded proposed edits and uses the existing draft/export path.
- Existing profile document chunk retrieval remains the source of active CV evidence. Do not use legacy `resume_text` as the CV source of truth when an active CV exists.
- No new database table is required. The existing suggestion table already stores all required fields.
- Do not expose full CV chunks in frontend safe payloads or tool-call safe payloads.
- Do not auto-export drafts and do not auto-promote exported versions.

## Final Verification Commands

```powershell
cd C:\Users\ACER\OtherProjects\Job_Agent\backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check

cd C:\Users\ACER\OtherProjects\Job_Agent\frontend\job-agent-ui
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

## Self-Review Notes

- Spec coverage: Phase 5 covers job-score-driven suggestions, evidence mapping, risk classification, fact-request flow, user confirmation before drafting, visible agent tool calls, Review Queue UI, and end-to-end suggestion-to-export verification.
- Intentional deferrals: rich LLM-authored CV rewriting, OCR, pixel-perfect PDF editing, and automatic active CV promotion remain outside Phase 5.
- Type consistency: backend response schema names match frontend type names and API client method name `generateJobCvImprovements`.
- Safety boundary: missing evidence becomes `requires_user_fact` with high risk; only wording-only suggestions can be drafted.
