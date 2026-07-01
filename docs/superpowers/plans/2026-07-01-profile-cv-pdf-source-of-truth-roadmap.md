# Profile CV PDF Source Of Truth Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the approved Profile CV PDF source-of-truth redesign into bounded implementation plans that can be shipped and verified independently.

**Architecture:** Build on the existing profile PDF upload, text extraction, chunking, Qdrant indexing, chat tool-call, and React profile document panel. Phase 1 establishes real PDF source-of-truth behavior; later phases add active-CV retrieval tools, structure extraction, editable drafts, PDF export, and job-score-driven CV improvement.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, SQLite, Qdrant, pypdf, React, TypeScript, Vitest, oxlint.

---

## Source Spec

- `docs/superpowers/specs/2026-07-01-profile-cv-pdf-source-of-truth-design.md`

## Phase Boundaries

### Phase 1: PDF Source-Of-Truth Foundation

Plan file:

- `docs/superpowers/plans/2026-07-01-profile-cv-pdf-source-of-truth-phase-1.md`

Ships:

- original uploaded PDFs remain real stored files
- original version records
- active CV pointers
- inline PDF view endpoints
- attachment PDF download endpoints
- document delete endpoint with active-CV guard
- frontend View, Download, Delete, Set active controls
- tests for upload, view, download, active selection, delete guard, path safety

Does not ship:

- AI CV editing
- PDF export
- new CV improvement tools
- OCR
- cloud storage

### Phase 2: Active CV Retrieval And Agent Tools

Plan to write after Phase 1 is merged because it depends on landed version table and active CV field names.

Ships:

- active CV retrieval service
- version-aware profile chunk retrieval
- Qdrant payload includes `version_id`
- tools: `list_profile_cvs`, `get_active_profile_cv`, `view_profile_cv_metadata`, `retrieve_profile_cv_chunks`, `analyze_cv_structure`
- chat-visible tool events for CV reads
- chat memory and scoring use active CV as primary profile evidence

Exit criteria:

- AI can retrieve active CV chunks through visible tools
- tool safe payloads contain IDs, counts, and statuses only
- existing structured profile fields remain as supplemental data

### Phase 3: CV Structure And Drafts

Plan to write after Phase 2 lands because it depends on active CV retrieval and tool conventions.

Ships:

- CV structure extraction service
- reliability status: `reliable`, `partial`, `unreliable`
- draft table and draft service
- suggestion table
- tools: `suggest_cv_improvements`, `create_cv_edit_draft`, `preview_cv_edit_draft`
- frontend suggestion and draft preview panels

Exit criteria:

- unreliable PDF structure triggers the required template recommendation
- AI drafts do not overwrite original or exported PDFs
- suggestions distinguish wording-only edits from edits needing user facts

### Phase 4: PDF Export And Version Promotion

Plan to write after Phase 3 lands because it depends on the draft schema and structure reliability fields.

Ships:

- PDF export dependency and service
- draft-to-PDF export as a new version
- view/download exported versions
- tools: `export_cv_draft_to_pdf`, `set_active_cv_version`
- explicit confirmation before active version promotion
- frontend version history and exported version controls

Exit criteria:

- exported PDFs are real stored files
- exported PDFs can be viewed and downloaded through the same file-serving path
- export does not automatically set active CV

### Phase 5: Job-Scoring-Based CV Improvement Workflow

Plan to write after Phase 4 lands because it depends on scoring evidence, suggestions, drafts, and export.

Ships:

- score-gap to CV evidence mapping
- targeted improvement suggestions after job scoring
- risk classification
- user fact-request flow
- draft creation from approved suggestions
- end-to-end tests from scored job to exported CV version

Exit criteria:

- AI never fabricates CV content
- each suggestion includes job requirement, CV evidence, gap, proposed edit, edit kind, risk, and confirmation requirement
- approved suggestions can produce a draft and exported PDF version

## Dependency Order

1. Phase 1 must land before every later phase.
2. Phase 2 must land before Phase 3 because draft/edit tools need active CV retrieval semantics.
3. Phase 3 must land before Phase 4 because export consumes drafts.
4. Phase 4 must land before Phase 5 because job-driven improvements need the full suggestion-to-export loop.

## Verification Policy

Each phase must run:

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

Existing lint warnings are acceptable only when unchanged and not introduced by the phase.

