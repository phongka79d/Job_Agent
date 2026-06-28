# Plan 5 - React Dashboard, Review Workflow, and Demo UI

## 1. Objective

Build the React + TypeScript frontend for the MVP: role profile creation, job search and manual ingestion, review queue, tracked-job dashboard, score breakdown, basic cost/performance metrics, approve/reject actions, and manual application status updates.

After this phase, the project meets the final MVP definition from `Master_Plan.md`.

## 2. Source of Truth

- `Master_Plan.md` section 1, "System Objective"
- `Master_Plan.md` section 3, "MVP Scope"
- `Master_Plan.md` section 4, "Architecture"
- `Master_Plan.md` section 7, "Handling JavaScript Pages and Cookie Banners"
- `Master_Plan.md` section 14, "Visual Score Breakdown in UI"
- `Master_Plan.md` section 15, "Cost & Performance Metrics Panel"
- `Master_Plan.md` section 19, "Human-in-the-Loop Rules"
- `Master_Plan.md` section 26, "API Endpoints"
- `Master_Plan.md` section 31, "Environment Setup"
- `Master_Plan.md` section 35, "Implementation Checklist: Demo Readiness, UI"
- `Master_Plan.md` section 36, "Final MVP Definition"

## 3. Prerequisites from Prior Phases

- [ ] Plan 1 backend foundation and database exist.
- [ ] Plan 2 extraction graph works.
- [ ] Plan 3 scoring, deduplication, persistence, and Qdrant sync work.
- [ ] Plan 4 FastAPI routes and demo seeding work.
- [ ] Plan 4 exposes stable API response schemas from `backend/app/api/schemas.py`.
- [ ] Plan 4 exports `shared/api-contract.json` by running `backend/scripts/export_api_contract.py`.
- [ ] Plan 4 API schemas are validated against Plan 1 backend constants for statuses and source values.
- [ ] Plan 4 ingestion endpoints return the standard ingestion response with `batch_id`, counts, full jobs, and ingestion-level warnings.
- [ ] Plan 4 supports `GET /api/jobs?status=tracked` for saved/applied/interview/rejected/offer jobs.
- [ ] Plan 4 CORS allows `http://localhost:5173`.
- [ ] `python scripts/seed_demo.py --reset` can preload demo jobs from the `backend/` directory.
- [ ] Backend can run locally on port `8000`.

## 4. Scope

- Create Vite React TypeScript app under `frontend/job-agent-ui`.
- Install frontend dependencies:
  - `react-router-dom`
  - `axios`
  - `lucide-react`
- Add API client for backend endpoints.
- Add TypeScript types for role profiles, jobs, score fields, statuses, warnings, and batch metrics.
- Keep frontend status/source TypeScript unions synchronized with the Plan 4 exported `shared/api-contract.json`, which is generated from backend constants, Plan 3 status transitions, endpoint metadata, and API schemas.
- Build role profile creation and selection UI.
- Build job ingestion controls:
  - Tavily/public search
  - manual public URL
  - manual raw text
  - mock load/demo mode
- Build review queue showing `pending_review` jobs.
- Build approve and reject controls.
- Build tracked-job dashboard sorted by backend score order.
- Build manual status update controls for saved/tracked jobs.
- Track the active `batch_id` returned from search, parse-url, parse-text, and mock-load responses.
- Refresh metrics from the active `batch_id`.
- Fetch dashboard jobs with `status=tracked`, not only `saved`.
- Preserve jobs in the dashboard after status changes to `applied`, `interview`, `rejected`, or `offer`.
- Display all backend warnings returned from ingestion responses.
- Build score breakdown accordion, popover, or modal.
- Build cost/performance metrics panel.
- Show manual-input warning for URL parsing failures.
- Add loading, error, and empty states.
- Add responsive layout for laptop and mobile demo.
- Ensure the dashboard can work from already seeded local demo data without Tavily, public internet search, URL fetching, or LLM extraction access.

## 5. Out of Scope

- Do not implement authentication, organizations, or multi-user switching.
- Do not call OpenAI, Tavily, Qdrant, or SQLite directly from the frontend.
- Do not duplicate backend scoring formulas in the frontend.
- Do not add cover letter generation.
- Do not add auto-apply behavior.
- Do not add authenticated LinkedIn/Facebook scraping.
- Do not add heavy analytics or background jobs.
- Do not redesign backend API contracts from Plan 4.

## 6. Target Directory Structure

```text
frontend/
`-- job-agent-ui/
    |-- package.json
    |-- index.html
    |-- vite.config.ts
    |-- tsconfig.json
    `-- src/
        |-- App.tsx
        |-- main.tsx
        |-- api/
        |   `-- client.ts
        |-- components/
        |   |-- AppShell.tsx
        |   |-- BatchMetrics.tsx
        |   |-- IngestionPanel.tsx
        |   |-- JobCard.tsx
        |   |-- ReviewQueue.tsx
        |   |-- RoleProfilePanel.tsx
        |   |-- ScoreBreakdown.tsx
        |   `-- StatusSelect.tsx
        |-- pages/
        |   |-- DashboardPage.tsx
        |   `-- ReviewPage.tsx
        |-- styles/
        |   `-- app.css
        |-- test/
        |   |-- activeBatch.test.tsx
        |   |-- apiContract.test.ts
        |   |-- setup.ts
        |   `-- StatusSelect.test.tsx
        `-- types/
            `-- api.ts
```

If the app already uses a different component organization, keep the existing convention while preserving these feature boundaries.

## 7. Technical Specifications

### Frontend Runtime

Create the app with:

```powershell
npm create vite@latest frontend/job-agent-ui -- --template react-ts
cd frontend/job-agent-ui
npm install
npm install react-router-dom axios lucide-react
```

Run with:

```powershell
npm run dev
```

Default frontend port:

```text
5173
```

Backend base URL:

```text
http://localhost:8000
```

Do not create any `.env` or `.env.example` files under the frontend directory. This enforces the single-root `.env` architecture.
The frontend API client base URL must default in code to `http://localhost:8000`. If custom configuration is required for production, it must be loaded via a centralized root configuration mechanism, not via a frontend-specific environment file. Only expose frontend-safe configurations if necessary, and never expose backend API keys.

`package.json` must include these scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "test": "vitest",
    "preview": "vite preview"
  }
}
```

### Pages and Navigation

Use a compact application layout, not a marketing landing page.

Required views:

```text
Review Queue
Tracked Jobs Dashboard
```

The first screen should be the usable dashboard/review experience with role profile controls and ingestion actions visible.

### API Client

Implement client functions for:

```text
createRoleProfile
listRoleProfiles
searchJobs
parseJobUrl
parseJobText
loadMockJobs
getReviewJobs
approveJob
rejectJob
updateJobStatus
getJobs
getJobDetail
getBatchSummary
```

`getJobs` must support:

```ts
getJobs(roleProfileId: string, status?: "saved" | "tracked" | JobStatus)
```

Dashboard should call:

```ts
getJobs(activeRoleProfileId, "tracked")
```

Review queue should call:

```ts
getReviewJobs(activeRoleProfileId)
```

All client functions must return typed data and surface backend validation errors without swallowing them.

All state-changing UI actions must call the backend and then refresh affected data from the backend.

### Required TypeScript API Types

`src/types/api.ts` must include:

```ts
export type JobStatus =
  | "pending_review"
  | "saved"
  | "applied"
  | "interview"
  | "rejected"
  | "offer"
  | "ignored";

export type JdStatus =
  | "full_jd"
  | "partial_jd"
  | "contact_for_jd"
  | "no_jd"
  | "unclear";

export type ParseStatus = "success" | "needs_manual_input" | "failed";
export type ExtractionStatus = "success" | "retried" | "failed";

export interface Job {
  id: string;
  batch_id: string;
  role_profile_id: string;
  title: string | null;
  company: string | null;
  location: string | null;
  work_mode: string | null;
  level: string | null;
  employment_type: string | null;
  salary: string | null;
  responsibilities: string | null;
  requirements: string | null;
  skills: string[];
  source_url: string | null;
  source_platform: string | null;
  parse_status: ParseStatus | null;
  jd_status: JdStatus | null;
  extraction_status: ExtractionStatus | null;
  error_reason: string | null;
  should_score_similarity: boolean;
  embedding_similarity: number | null;
  skill_overlap_score: number | null;
  location_match_score: number | null;
  level_match_score: number | null;
  base_score: number | null;
  jd_confidence_multiplier: number | null;
  final_score: number | null;
  final_score_percent: number | null;
  status: JobStatus;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  extraction_time_ms: number | null;
  discovered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestionResponse {
  batch_id: string;
  inserted_jobs: number;
  skipped_exact_duplicates: number;
  skipped_dedup_key_duplicates: number;
  inserted_duplicate_metadata: number;
  qdrant_upserted: number;
  qdrant_synced: boolean;
  jobs: Job[];
  warnings: string[];
}

export interface BatchSummary {
  batch_id: string;
  total_parsed_jobs: number;
  scorable_jobs: number;
  failed_extractions: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  average_extraction_time_ms: number | null;
}
```

These TypeScript unions mirror backend API response values; they are not an independent source of truth. Add a frontend contract test or schema snapshot check that loads `shared/api-contract.json` from the repository root. When running tests from `frontend/job-agent-ui`, resolve it as `path.resolve(process.cwd(), "../../shared/api-contract.json")`. Compare `JobStatus`, `JdStatus`, `ParseStatus`, `ExtractionStatus`, source platform values, endpoint metadata, and key response schema names against the exported backend contract. If the backend adds or removes a Master-approved value, the frontend test must fail until `src/types/api.ts` is updated deliberately or regenerated from the contract.

If API types are generated instead of handwritten, generate them from `shared/api-contract.json` or from the backend OpenAPI/schema export referenced by that contract. Local hardcoded literals are acceptable only when covered by a contract test that fails on drift.

### Active Batch Handling

When any ingestion action succeeds:

```text
searchJobs
parseJobUrl
parseJobText
loadMockJobs
```

the UI must:

```text
1. Store `response.batch_id` as `activeBatchId` in component state AND save it to localStorage (keyed by active role profile ID).
2. Show response warnings.
3. Refresh review queue.
4. Refresh tracked dashboard.
5. Fetch `GET /api/batches/{activeBatchId}/summary`.
```

If there is no active batch, the metrics panel should show an empty state instead of calling the summary endpoint.
When the user switches role profiles, the UI must reload the corresponding `activeBatchId` from localStorage for that profile, or reset the batch metrics view if no batch history exists. This ensures metrics do not disappear or leak across profiles on refresh.

There is no backend "latest batch for profile" endpoint in the MVP API contract. Do not invent one in the frontend phase. If no active batch ID exists for the selected profile in localStorage, show the metrics empty state until the user runs an ingestion action.

Use this stable localStorage key format:

```text
job-agent.activeBatchId.{role_profile_id}
```

Rules:

- Write the key only after a successful ingestion response that includes a `batch_id`.
- Read the key after selecting or creating a role profile.
- Remove the key if `GET /api/batches/{batch_id}/summary` returns 404 for that profile's saved batch.
- Never reuse an active batch ID across different role profiles.

### Role Profile UI

Fields:

```text
target role
level
location
accept remote
skills
resume/profile text
```

Use the backend response ID as the active `role_profile_id`.

### Ingestion UI

Provide controls for:

- Public job search query.
- Manual public URL paste.
- Manual raw job text paste.
- Demo/mock load button.

Use configured backend limits; show backend validation errors when limits are exceeded.

When URL parsing returns a manual input warning, show:

```text
We could not extract enough job content from this URL.
The page may require JavaScript rendering, login, or cookie acceptance.
Please paste the job description text manually.
```

Display warnings and stored extraction errors from:

```text
IngestionResponse.warnings
Job.error_reason
```

Show `IngestionResponse.warnings` in a short ingestion result area after parse/search/mock-load.
Show persisted per-job extraction or processing issues on job cards from `Job.error_reason`.
Do not assume the `warnings` array can identify a specific job card unless Plan 4 later adds job-keyed warning metadata.

### Review Queue UI

Each pending job card must show:

```text
title
company
location
final score percent when available
JD status
status
source platform
warning/error when available
approve action
reject action
score breakdown action when scorable
```

Approve behavior:

```text
POST /api/jobs/{id}/approve
refresh review queue
refresh tracked dashboard
refresh batch metrics if a current batch is selected
```

Reject behavior:

```text
POST /api/jobs/{id}/reject
refresh review queue
refresh metrics if a current batch is selected
```

### Tracked Jobs Dashboard

Show tracked jobs using:

```text
GET /api/jobs?role_profile_id={id}&status=tracked
```

The backend owns sorting by `final_score`. The dashboard must include jobs with:

```text
saved
applied
interview
rejected
offer
```

Do not filter to only `saved`, or jobs will disappear after manual status updates.

Each tracked job must show:

```text
title
company
location
final score percent
JD status
current status
score breakdown
manual application status control
```

Manual statuses:

```text
applied
interview
rejected
offer
```

`StatusSelect` must be current-status aware and filter dropdown options to only display valid manual transition paths allowed by the backend contract:
- If current status is `saved`: show options `applied` and `rejected`.
- If current status is `applied`: show options `interview` and `rejected`.
- If current status is `interview`: show options `rejected` and `offer`.
- If current status is `rejected` or `offer` (terminal states): disable the dropdown or hide status controls.

The dropdown must never offer `pending_review`, `saved`, or `ignored` options.
These examples must be tested against `allowed_status_transitions` from `shared/api-contract.json`, not accepted as an unverified independent frontend transition map.

Approve uses the approve endpoint, reject from review uses the reject endpoint, and manual tracking uses `PATCH /api/jobs/{id}/status`.

Use:

```text
PATCH /api/jobs/{id}/status
```

### Score Breakdown

The UI must show the final score and component scores.

Required fields:

```text
Semantic Similarity
Skill Overlap
Location Match
Level Match
JD Confidence
Final Score
```

For null scores, display a clear non-scorable state such as:

```text
Not scored
```

Format nullable score fields safely:

```text
null -> Not scored
0.85 -> 85%
```

Never compute missing component scores in the frontend. Only format values returned by the backend.

If `should_score_similarity = false`, show `Not scored` for the whole breakdown.

Do not recalculate scores in the frontend.

### Metrics Panel

Use:

```text
GET /api/batches/{batch_id}/summary
```

Display:

```text
Jobs parsed
Scorable jobs
Failed extractions
Total tokens
Estimated cost
Average extraction time when available
```

Use stored per-job fields and backend aggregation only. Do not add frontend-only analytics.

### UI States

Required states:

- Loading state for route fetches and state-changing actions.
- Empty state when no profile exists.
- Empty state when review queue is empty.
- Empty state when no tracked jobs exist.
- Error state for backend validation or service failure.
- Disabled state while approve/reject/status actions are in flight.

### Visual Design Rules

- Build the actual app as the first screen, not a landing page.
- Keep the interface work-focused and dashboard-like.
- Use compact panels and predictable navigation.
- Use `lucide-react` icons in buttons where useful.
- Use buttons only for commands, selects for status choices, textareas for raw text, and forms for input.
- Avoid decorative cards inside cards.
- Ensure text fits on mobile and desktop.
- Ensure score and status labels do not overlap.
- Use a compact, work-focused dashboard visual system with CSS variables for background, surface, border, accent, and muted text colors.
- Use restrained hover/focus states that do not resize fixed-format UI elements or cause layout shift.
- Use local/system font fallbacks by default; do not require external font loading for the demo to work offline.

## 8. Implementation Steps

- [ ] Scaffold `frontend/job-agent-ui` with Vite React TypeScript.
- [ ] Install `react-router-dom`, `axios`, and `lucide-react`.
- [ ] Add required `package.json` scripts for `dev`, `build`, `typecheck`, `test`, and `preview`.
- [ ] Add `src/types/api.ts` matching Plan 4 response contracts.
- [ ] Add a contract test or generated-schema snapshot check that loads `shared/api-contract.json` and keeps frontend status/source unions synchronized with the exported backend contract.
- [ ] Ensure frontend endpoint constants/client paths are covered by `shared/api-contract.json` endpoint metadata or tested against it.
- [ ] Add complete nullable TypeScript API types.
- [ ] Add `src/api/client.ts` with all backend client functions.
- [ ] Store active `role_profile_id` and active `batch_id`.
- [ ] Build app shell with review/dashboard navigation.
- [ ] Build role profile creation and selection UI.
- [ ] Build ingestion panel for search, URL, raw text, and mock load.
- [ ] Use standard ingestion response for search, URL parse, text parse, and mock load.
- [ ] Show ingestion warnings and per-job extraction errors.
- [ ] Display `IngestionResponse.warnings` only in the ingestion result area unless the backend returns job-keyed warning metadata.
- [ ] Display per-job persisted issues from `Job.error_reason` on job cards.
- [ ] Build review queue and job cards.
- [ ] Add approve and reject actions.
- [ ] Build tracked jobs dashboard.
- [ ] Fetch dashboard jobs with `status=tracked`.
- [ ] Add a test or mocked client assertion that the dashboard calls `GET /api/jobs` with `status=tracked`, not only `saved`.
- [ ] Add manual status update control.
- [ ] Ensure manual status select does not offer `ignored`.
- [ ] Add score breakdown UI.
- [ ] Add batch metrics panel.
- [ ] Refresh review queue, tracked dashboard, and active batch metrics after every state-changing action.
- [ ] Add loading, empty, disabled, and error states.
- [ ] Add responsive CSS.
- [ ] Add frontend tests for API client/type-safe rendering where practical.
- [ ] Add `src/test/setup.ts` and configure Vitest to use `jsdom`.
- [ ] Add tests for localStorage active batch keys being isolated per role profile.
- [ ] Add tests that profile switching uses the profile-specific localStorage active batch key or shows empty metrics when no key exists.
- [ ] Add tests for `StatusSelect` only showing valid backend transition options from `shared/api-contract.json`.
- [ ] Add tests proving frontend status/source unions match `shared/api-contract.json` values and do not contain non-Master statuses such as `archived` or unsupported source platforms.
- [ ] Add rendering tests for null score fields and ingestion warnings.
- [ ] Verify already seeded local demo data can populate the UI without Tavily, public internet search, URL fetching, or LLM extraction access.
- [ ] Confirm frontend never exposes API keys or calls external AI/search/vector services directly.
- [ ] Confirm no frontend `.env`, `frontend/.env.example`, or `frontend/job-agent-ui/.env.example` exists.

## 9. Verification & Testing Plan

Backend prerequisite:

```powershell
docker compose up -d qdrant
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/seed_demo.py --reset
uvicorn app.main:app --reload --port 8000
```

Frontend checks:

```powershell
cd frontend/job-agent-ui
npm install
```

Backend contract prerequisite:

```powershell
cd ../..
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/export_api_contract.py
cd ..\frontend\job-agent-ui
```

Install test dependencies and configure the Vite test runner:

```powershell
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Configure `vite.config.ts` to support testing settings. Add a `test` block to `defineConfig`:

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
```

Ensure a mock API adapter/server (e.g., MSW or custom axios mocks) is set up in `src/test/setup.ts` to test client API functions against network errors gracefully.

```powershell
npm run build
npm run typecheck
npm test -- --run
npm run dev
```

Contract verification:

```powershell
npm test -- --run
```

Expected contract coverage:

```text
Frontend JobStatus, JdStatus, ParseStatus, ExtractionStatus, source platform unions, endpoint metadata, and StatusSelect transition options match shared/api-contract.json generated from backend constants, Plan 3 transitions, and Plan 4 API schemas.
```

If no separate `typecheck` script exists, add one:

```json
"typecheck": "tsc --noEmit"
```

If no separate `test` script exists, add one:

```json
"test": "vitest"
```

Frontend environment file verification:

```powershell
Test-Path frontend/.env
Test-Path frontend/.env.example
Test-Path frontend/job-agent-ui/.env
Test-Path frontend/job-agent-ui/.env.example
```

Expected:

```text
False
False
False
False
```

Manual verification:

- Create or select a role profile.
- Load mock/demo jobs.
- Confirm review queue shows pending jobs sorted with scorable jobs first.
- Open score breakdown for a scorable job.
- Confirm non-scorable social/contact jobs show `Not scored`.
- Approve a job and confirm it moves from review queue to tracked dashboard.
- After approving a job, it appears in tracked dashboard.
- Reject a job and confirm it leaves the review queue.
- Update a tracked job to `applied`, `interview`, `rejected`, or `offer`.
- After changing a job to applied/interview/rejected/offer, it remains in tracked dashboard.
- Confirm metrics panel shows parsed jobs, scorable jobs, failed extractions, tokens, and estimated cost.
- Metrics panel updates after mock-load, parse-text, parse-url, and search.
- Metrics panel reloads the active batch from `job-agent.activeBatchId.{role_profile_id}` after page refresh.
- Switching role profiles uses that profile's own active batch key and does not show metrics from another profile.
- Switching to a profile without a stored active batch key shows metrics empty state and does not call a non-existent latest-batch endpoint.
- Parse a manual raw text job and confirm it appears in review queue.
- Parse a low-content URL and confirm manual input warning appears.
- Null score fields render as `Not scored`.
- Ingestion warnings appear after low-content URL parsing.
- Job cards show persisted `Job.error_reason` without requiring transient `warnings` to be job-keyed.
- No request is made to OpenAI, Tavily, Qdrant, or SQLite from browser devtools.
- Confirm browser console has no critical errors.
- Confirm the app works at a mobile viewport without overlapping text.
- Confirm no frontend `.env` or `.env.example` files exist.
- Confirm frontend status/source labels and dropdown options match the backend API schema and do not introduce frontend-only states.
- Confirm contract tests fail if `shared/api-contract.json` removes or changes a status, source platform, endpoint path, or allowed status transition.

Expected MVP behavior:

- Demo can start from preloaded data.
- Dashboard works from preloaded local demo data without internet search or extraction API access.
- User can create a profile.
- User can search or manually ingest jobs.
- Extracted jobs are shown as `pending_review`.
- User can approve, reject, and update status manually.
- Score breakdown and metrics are visible.

## 10. Handoff Notes for Phase 6

There is no required Phase 6 in the MVP split.

This phase completes the final MVP definition:

```text
1. Seed demo data into SQLite and local Qdrant.
2. Create a role profile.
3. Search public jobs or accept manual URL/text input.
4. Extract job data into validated JSON.
5. Classify JD completeness.
6. Save jobs as pending_review.
7. Score full/partial JD jobs only.
8. Show a ranked dashboard.
9. Show score breakdown per job.
10. Show basic cost/performance metrics.
11. Let user approve/reject jobs.
12. Let user update application status manually.
```

Hard rules after MVP completion:

- Future enhancements must preserve SQLite as the source of truth unless a migration plan replaces it.
- Future features must not silently change scoring semantics used in this MVP.
- Any authentication, cover-letter generation, browser scraping, or auto-apply work must be planned as separate post-MVP scope.
