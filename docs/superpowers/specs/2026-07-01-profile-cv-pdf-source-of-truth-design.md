# Profile CV PDF Source Of Truth Design

## Summary

Redesign profile documents so an uploaded CV PDF is treated as the primary profile artifact, not as disposable text that is copied into structured fields. The original PDF file must be stored, viewable, downloadable, retrievable by AI tools, and preserved as immutable source material. AI edits must create drafts and exported PDF versions; they must never overwrite the original uploaded PDF.

This design extends the current production foundation:

- existing profile PDF upload endpoint
- existing text-only PDF extraction using `pypdf`
- existing SQLite metadata tables for profile documents and chunks
- existing Qdrant `profile_documents` collection
- existing chat memory and tool-call visibility
- existing React profile document panel

The design is intentionally incremental. Phase 1 makes uploaded PDFs real source-of-truth files with view/download/delete and active CV selection. Later phases add versioning, AI tools, draft editing, PDF export, and job-scoring-based CV improvement.

## Product Principles

1. **PDF file is authoritative.** SQLite metadata, extracted text, chunks, embeddings, summaries, and structured CV JSON are auxiliary data. They never replace the stored PDF.
2. **Original uploads are immutable.** The system may delete an original after explicit user action, but it must never modify or overwrite it.
3. **AI edits create new artifacts.** AI suggestions become drafts. Drafts can export new PDF versions. A user must explicitly approve before an exported version becomes active.
4. **The active CV is explicit.** A role profile can have many CV documents and versions, but only one active CV version is used as the main profile evidence for AI reasoning and job scoring.
5. **No fabrication.** AI may improve wording, ordering, emphasis, and relevance. It must not invent skills, companies, schools, dates, certifications, projects, metrics, or experience.
6. **Real PDF viewing.** The UI must render the stored PDF file via browser PDF viewer, iframe, object/embed, or a PDF rendering library. It must not reconstruct the PDF from extracted text.
7. **Thin routes, service-owned logic.** API routes validate request shape and profile scoping. File storage, metadata, extraction, retrieval, versioning, draft logic, and export live in services.

## Current Baseline

Backend already has:

- `backend/app/api/routes_profile_documents.py`
  - `POST /api/role-profiles/{role_profile_id}/documents`
  - `GET /api/role-profiles/{role_profile_id}/documents`
- `backend/app/services/profile_document_service.py`
  - validates PDF uploads
  - copies PDFs under the SQLite directory
  - extracts text
  - chunks text
  - embeds chunks
  - persists `ProfileDocument` and `ProfileDocumentChunk`
  - upserts chunk vectors to Qdrant
- `backend/app/services/profile_document_retrieval_service.py`
  - keyword-based retrieval over SQLite chunks
- `backend/app/services/qdrant_service.py`
  - `profile_documents` collection
  - profile document chunk upsert payloads
- `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
  - upload and list profile PDFs

Missing capabilities:

- serving the actual stored PDF file
- download endpoints with correct PDF headers
- delete endpoints
- active CV selection
- version history
- draft editing
- PDF export
- CV-specific agent tools
- frontend PDF viewer
- frontend version/draft controls
- confirmation gates for destructive/write actions

## Recommended Architecture

Use five layers.

1. **File storage layer**
   - Owns safe storage paths.
   - Writes uploaded and exported PDFs.
   - Opens files for inline view and attachment download.
   - Ensures resolved file paths stay under the configured storage root.

2. **Document metadata layer**
   - Owns `ProfileDocument`, `ProfileDocumentVersion`, chunks, active CV pointers, and deletion behavior.
   - Stores metadata, not PDF bytes.
   - Keeps originals immutable.

3. **Extraction and retrieval layer**
   - Extracts text from PDFs.
   - Extracts a best-effort editable structure with reliability status.
   - Chunks text and stores embeddings.
   - Retrieves active CV chunks for AI tools and scoring.

4. **Draft and versioning layer**
   - Creates editable CV drafts from original or exported versions.
   - Stores proposed changes and structured draft JSON.
   - Exports a draft to a new PDF version.
   - Promotes an exported version to active only after explicit user approval.

5. **Agent/UI layer**
   - Exposes CV actions as tools with visible tool-call states.
   - Shows PDF metadata, versions, drafts, suggestions, and active CV status.
   - Opens actual PDF file URLs for View and Download.

## Storage Design

Add a profile document storage root setting:

```text
PROFILE_DOCUMENT_STORAGE_DIR
```

Default:

```text
<sqlite_db_parent>/uploads/profile_documents
```

Recommended path layout:

```text
uploads/profile_documents/
  {role_profile_id}/
    {document_id}/
      original/
        {version_id}.pdf
      versions/
        {version_id}.pdf
```

Rules:

- Store uploaded PDFs as real files.
- Store exported CV versions as real PDF files.
- Never store raw PDF bytes in SQLite.
- Never serve a path directly from request input.
- Always resolve stored paths and verify they are inside `PROFILE_DOCUMENT_STORAGE_DIR`.
- Use safe generated filenames for stored files.
- Use safe user-friendly filenames for downloads.

Download filename format:

```text
{profile-target-role-or-profile}_{cv-title-or-original-name}_{version-label}.pdf
```

Sanitize filenames to ASCII-safe characters, trim length, and ensure `.pdf`.

## Database Design

### Existing Table: `profile_documents`

Keep this table as the logical CV document container. Extend it instead of replacing it.

Current useful fields:

- `id`
- `role_profile_id`
- `original_filename`
- `stored_path`
- `content_hash`
- `mime_type`
- `file_size_bytes`
- `extracted_text_chars`
- `chunk_count`
- `status`
- `error_reason`
- `created_at`
- `updated_at`

Recommended additions:

- `document_kind`: text, default `cv`
- `active_version_id`: nullable FK to `profile_document_versions.id`
- `deleted_at`: nullable datetime, used only if soft deletion is needed for safety during file cleanup

For MVP simplicity, deletion should remove the document from normal lists. If a hard delete is used, it must delete chunks, Qdrant points, versions, drafts, and files. If a soft delete is used first, UI must hide deleted rows and a cleanup service must remove files.

### New Table: `profile_document_versions`

Represents every real PDF file associated with a CV document.

Fields:

- `id`
- `document_id`
- `role_profile_id`
- `version_number`
- `source_type`: `original_upload` or `exported_draft`
- `parent_version_id`: nullable FK to `profile_document_versions.id`
- `draft_id`: nullable FK to `profile_cv_drafts.id`
- `display_name`
- `filename`
- `stored_path`
- `content_hash`
- `mime_type`
- `file_size_bytes`
- `extracted_text_chars`
- `chunk_count`
- `extraction_status`: `processing`, `ready`, `failed`
- `structure_status`: `not_extracted`, `reliable`, `partial`, `unreliable`
- `structure_confidence`: nullable float
- `error_reason`
- `created_by`: `user`, `ai`, or `system`
- `created_at`
- `updated_at`

The original uploaded PDF becomes version 1 with `source_type = original_upload`.

### New Active CV Pointers

Add to `role_profiles`:

- `active_cv_document_id`: nullable FK to `profile_documents.id`
- `active_cv_version_id`: nullable FK to `profile_document_versions.id`

Rules:

- If no active CV exists and the user uploads the first ready CV, set it active automatically.
- If a later CV is uploaded, do not replace the active CV unless the user chooses it.
- Migration for existing ready documents should create original versions and set the most recent ready document active only when the profile has no active CV.

### Existing Table: `profile_document_chunks`

Extend chunks to support version-aware retrieval.

Recommended additions:

- `version_id`: nullable FK to `profile_document_versions.id`
- `source_type`: text, default `extracted_text`

For migrated data, backfill `version_id` to the generated original version.

Qdrant payload should include:

- `role_profile_id`
- `document_id`
- `version_id`
- `chunk_id`
- `chunk_index`
- `source_type`: `profile_cv`

### New Table: `profile_cv_drafts`

Stores AI/user editable drafts before export.

Fields:

- `id`
- `role_profile_id`
- `document_id`
- `base_version_id`
- `status`: `draft`, `exported`, `discarded`
- `title`
- `structure_json`
- `edit_plan_json`
- `structure_status_at_creation`
- `created_by`: `user` or `ai`
- `created_at`
- `updated_at`

Drafts are not active CVs and are not PDFs until exported.

### New Table: `profile_cv_improvement_suggestions`

Stores job-scoring-based improvement suggestions.

Fields:

- `id`
- `role_profile_id`
- `document_id`
- `version_id`
- `job_id`: nullable
- `requirement`
- `current_cv_evidence`
- `missing_or_weak_evidence`
- `proposed_edit`
- `edit_kind`: `wording_only` or `requires_user_fact`
- `risk_level`: `low`, `medium`, `high`
- `requires_confirmation`: boolean
- `status`: `suggested`, `accepted`, `rejected`, `drafted`
- `created_at`
- `updated_at`

High-risk and fact-adding suggestions must not be applied without explicit user-provided facts.

## Backend Services

### `ProfileDocumentStorageService`

Responsibilities:

- compute storage root
- create per-profile/document/version directories
- copy uploaded PDFs
- write exported PDFs
- validate paths before serving
- build inline and attachment filenames
- delete stored files safely

### `ProfileDocumentService`

Responsibilities:

- create document container
- create original version
- validate upload type and size
- list documents and versions
- delete documents after confirmation
- keep routes thin

This service should delegate file work to `ProfileDocumentStorageService`.

### `ProfileCvVersionService`

Responsibilities:

- create original and exported version records
- set active CV version
- enforce immutable original rule
- reject active-version promotion without explicit confirmation
- return file metadata for serving/download

### `PdfTextExtractionService`

Keep existing text-only extraction. OCR is not part of this redesign.

Rules:

- Reject PDFs with no extractable text for retrieval.
- Store failed extraction status.
- Still allow viewing/downloading the original PDF if storage succeeded.

### `CvStructureExtractionService`

Best-effort structure extraction from extracted text.

Outputs:

- section order
- headings
- bullet groups
- date-like ranges
- project/work/education ordering when detectable
- `structure_status`
- `structure_confidence`
- warnings

Reliability rules:

- `reliable`: sections and bullets are consistently detected.
- `partial`: content is extractable, but some structure is ambiguous.
- `unreliable`: scanned/image-only, table-heavy, broken ordering, inconsistent headings, or very low confidence.

When unreliable, AI editing tools must recommend a clean template instead of forcing structure-preserving edits.

### `ProfileCvRetrievalService`

Responsibilities:

- retrieve chunks from active CV version by default
- optionally retrieve chunks from a specified document/version
- use Qdrant vector search when available
- fall back to SQLite keyword retrieval if Qdrant search is unavailable
- return chunk text only to backend agent context, not raw full CV text to frontend safe payloads

### `CvDraftService`

Responsibilities:

- create draft from base version
- apply approved wording-only edits
- store draft structure JSON and edit plan JSON
- mark suggestions as drafted
- never modify original or exported PDF files

### `CvPdfExportService`

Responsibilities:

- export draft to a new real PDF file
- create `profile_document_versions` row with `source_type = exported_draft`
- extract/chunk/embed exported PDF version
- return exported version metadata

Current dependencies do not include a production PDF generation library. Add `reportlab>=4` in the export phase only, not in Phase 1. The first export implementation should use a clean supported CV template. Structure-preserving export can be added only when `structure_status` is reliable.

## API Design

### Upload And List

```text
POST /api/role-profiles/{profile_id}/documents
GET  /api/role-profiles/{profile_id}/documents
GET  /api/role-profiles/{profile_id}/documents/{document_id}
```

Upload returns document metadata and original version metadata.

### View Real PDF

```text
GET /api/role-profiles/{profile_id}/documents/{document_id}/file
GET /api/role-profiles/{profile_id}/documents/{document_id}/versions/{version_id}/file
GET /api/role-profiles/{profile_id}/active-cv/file
```

Response:

```text
Content-Type: application/pdf
Content-Disposition: inline; filename="safe-name.pdf"
```

### Download Real PDF

```text
GET /api/role-profiles/{profile_id}/documents/{document_id}/download
GET /api/role-profiles/{profile_id}/documents/{document_id}/versions/{version_id}/download
GET /api/role-profiles/{profile_id}/active-cv/download
```

Response:

```text
Content-Type: application/pdf
Content-Disposition: attachment; filename="safe-name.pdf"
```

### Delete

```text
DELETE /api/role-profiles/{profile_id}/documents/{document_id}
```

Rules:

- Requires explicit user action.
- If the document contains the active CV version, reject with `409 Conflict` unless the request explicitly clears active CV selection.
- Delete document versions, chunks, Qdrant points, drafts, suggestions, and stored files.

### Active CV

```text
GET  /api/role-profiles/{profile_id}/active-cv
POST /api/role-profiles/{profile_id}/documents/{document_id}/versions/{version_id}/activate
```

Activation body:

```json
{
  "confirmed": true
}
```

If `confirmed` is not true, return `409 Conflict` with a message explaining that setting active CV changes AI/profile source of truth.

### Versions

```text
GET /api/role-profiles/{profile_id}/documents/{document_id}/versions
GET /api/role-profiles/{profile_id}/documents/{document_id}/versions/{version_id}
```

### Drafts And Export

```text
POST /api/role-profiles/{profile_id}/documents/{document_id}/versions/{version_id}/drafts
GET  /api/role-profiles/{profile_id}/documents/{document_id}/drafts
GET  /api/role-profiles/{profile_id}/documents/{document_id}/drafts/{draft_id}
POST /api/role-profiles/{profile_id}/documents/{document_id}/drafts/{draft_id}/preview
POST /api/role-profiles/{profile_id}/documents/{document_id}/drafts/{draft_id}/export-pdf
```

Export creates a new PDF version. Export does not activate it automatically.

## Agent Tool Design

Add these tools incrementally to `ToolRegistry`.

Read-only tools:

- `list_profile_cvs`
- `get_active_profile_cv`
- `view_profile_cv_metadata`
- `retrieve_profile_cv_chunks`
- `analyze_cv_structure`
- `score_cv_against_job`

Draft/export/write tools:

- `suggest_cv_improvements`
- `create_cv_edit_draft`
- `preview_cv_edit_draft`
- `export_cv_draft_to_pdf`
- `set_active_cv_version`
- `delete_profile_cv`

Confirmation policy:

- `list_profile_cvs`: no confirmation
- `get_active_profile_cv`: no confirmation
- `view_profile_cv_metadata`: no confirmation
- `retrieve_profile_cv_chunks`: no confirmation
- `analyze_cv_structure`: no confirmation
- `score_cv_against_job`: no confirmation if it only reads and reports
- `suggest_cv_improvements`: no confirmation if it only suggests
- `create_cv_edit_draft`: confirmation required unless the user directly asks for a draft in the same message
- `preview_cv_edit_draft`: no confirmation
- `export_cv_draft_to_pdf`: confirmation required
- `set_active_cv_version`: confirmation required
- `delete_profile_cv`: confirmation required

Safe payloads must include only IDs, statuses, counts, display names, and frontend routes. They must not expose API keys, prompts, provider payloads, or full CV text.

When the AI discusses CV content, it must distinguish between:

- original PDF file
- extracted text
- structured editable draft
- exported PDF version

## Job-Scoring-Based CV Improvement

After a job is scored against the active CV, the AI may suggest targeted improvements.

Each suggestion must include:

- job requirement
- current CV evidence
- missing or weak evidence
- proposed edit
- edit kind: wording-only or requires user-provided facts
- risk level
- confirmation requirement

Rules:

- Wording-only suggestions may be drafted after user approval or direct request.
- Suggestions requiring new facts must ask the user for those facts.
- High-risk suggestions must never be applied automatically.
- The AI must not invent facts to improve a match score.

## Frontend Design

Rename the conceptual UI from "Profile documents" to "Profile CVs" while keeping file/module names stable unless a rename clearly reduces confusion.

Required UI areas:

1. **Active CV card**
   - filename
   - version label
   - status
   - last updated
   - View
   - Download

2. **Uploaded CV list**
   - original filename
   - active badge
   - status
   - file size
   - chunk count
   - extraction/structure status
   - View
   - Download
   - Versions
   - Set active
   - Delete

3. **PDF viewer**
   - modal or route
   - source URL points to `/file`
   - renders actual PDF using iframe/object/embed or a PDF rendering library
   - download button points to `/download`

4. **Version history**
   - original upload version
   - exported draft versions
   - active marker
   - View
   - Download
   - Set active

5. **Draft and improvement area**
   - suggestions grouped by job
   - risk level
   - edit kind
   - confirmation controls
   - preview draft
   - export draft PDF
   - set exported version active

6. **Tool-call timeline**
   - reuse existing chat tool call cards
   - show CV tools while the AI reads, retrieves, drafts, exports, or activates CVs

## Scoring And Profile Memory Behavior

When a role profile has an active CV:

- use active CV extracted text/chunks as the primary resume/profile evidence
- use structured role profile fields as target preferences and supplemental data
- treat `role_profiles.resume_text` as legacy supplemental notes, not the source of truth

When no active CV exists:

- continue supporting existing structured fields and `resume_text`
- prompt the user to upload or select an active CV when asking for CV-aware analysis

## Qdrant Design

Keep a separate `profile_documents` collection.

Reasoning:

- CV/profile chunks have different lifecycle and access rules than job chunks.
- Profile retrieval must filter by `role_profile_id`, `document_id`, and `version_id`.
- Active CV retrieval should not mix old versions unless explicitly requested.

Payload filters:

- `role_profile_id`
- `document_id`
- `version_id`
- `chunk_id`
- `chunk_index`
- `source_type = profile_cv`

Deletion must remove Qdrant points for deleted documents/versions when possible. If Qdrant deletion fails, the service should report a recoverable indexing cleanup error instead of silently leaving active stale vectors.

## Safety Rules

- Never overwrite original uploaded PDFs.
- Never fabricate CV facts.
- Never set a CV version active without explicit confirmation.
- Never delete a CV without explicit confirmation.
- Never expose full raw CV text in frontend tool safe payloads.
- Never expose API keys or provider payloads.
- Do not use uploaded PDFs outside the profile/chat/job-scoring context.
- Do not call external APIs unless the user action requires extraction, embedding, scoring, retrieval, or export.
- Poor structure must trigger a template recommendation instead of forced structure-preserving edits.

Required poor-structure message:

```text
The current PDF structure is not reliable enough for structure-preserving edits. I recommend converting it into a cleaner CV template before editing.
```

## Phased Implementation Plan

### Phase 1: PDF Source-Of-Truth Foundation

Deliver:

- real PDF file view endpoints
- real PDF download endpoints
- delete endpoint
- active CV pointers
- original version records
- frontend View/Download/Delete/Set active controls
- tests for upload, view, download, delete, active selection, path safety

Do not implement AI editing yet.

### Phase 2: Active CV Retrieval And Agent Tools

Deliver:

- active-CV retrieval service
- Qdrant payload includes `version_id`
- tools: `list_profile_cvs`, `get_active_profile_cv`, `view_profile_cv_metadata`, `retrieve_profile_cv_chunks`, `analyze_cv_structure`
- chat-visible tool events for CV retrieval
- scoring/memory use active CV as primary profile evidence

### Phase 3: CV Structure And Drafts

Deliver:

- structure extraction service
- reliability status
- draft table and draft service
- suggestions table
- tools: `suggest_cv_improvements`, `create_cv_edit_draft`, `preview_cv_edit_draft`
- frontend draft preview and suggestions panel

### Phase 4: PDF Export And Version Promotion

Deliver:

- add PDF export dependency
- export draft as new real PDF version
- view/download exported versions
- tools: `export_cv_draft_to_pdf`, `set_active_cv_version`
- explicit confirmation flow
- frontend version history and active version promotion

### Phase 5: Job-Scoring-Based CV Improvement Workflow

Deliver:

- connect job score breakdown to CV suggestions
- evidence mapping from score gaps to active CV chunks
- risk classification
- user fact-request flow
- draft generation from approved suggestions
- end-to-end tests from job score to exported CV version

## Testing Strategy

Backend tests:

- upload stores a real PDF file and creates metadata
- file endpoint returns `application/pdf` and inline disposition
- download endpoint returns `application/pdf` and attachment disposition
- file serving rejects path traversal and wrong-profile access
- deleting inactive CV removes metadata, chunks, vectors, and files
- deleting active CV requires explicit clear/confirmation behavior
- setting active CV requires `confirmed: true`
- active CV retrieval returns active version chunks
- original upload cannot be overwritten
- exported version creates a new PDF file and version row
- unreliable structure triggers template recommendation
- tool safe payloads do not include raw CV text or secrets

Frontend tests:

- uploaded CV list shows active marker and metadata
- View opens actual `/file` URL
- Download uses `/download` URL
- Delete confirmation path calls delete endpoint
- Set active confirmation calls activate endpoint
- version list renders original and exported versions
- draft preview renders structured draft, not original PDF
- tool-call timeline shows CV retrieval/edit/export tools

End-to-end manual verification:

- upload a text-based PDF
- view exact stored PDF
- download original PDF
- ask AI to read CV
- score a job against active CV
- create a draft from approved suggestions
- preview draft
- export draft to PDF
- view and download exported PDF
- set exported version active

## Non-Goals

- OCR for scanned PDFs
- pixel-perfect editing of arbitrary uploaded PDFs
- collaborative editing
- cloud object storage
- authentication or multi-tenant permissions beyond existing profile scoping
- replacing the existing job ingestion/scoring workflow

## Open Implementation Constraints

- The current dependency set supports PDF text extraction but not rich PDF generation. PDF export should add a generation dependency only in the export phase.
- The current app does not have authentication. All access control in this design is scoped by `role_profile_id` and document ownership checks.
- Existing `resume_text` remains as supplemental legacy data until a later cleanup removes or de-emphasizes the field in the profile form.

