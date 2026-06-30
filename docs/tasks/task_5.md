# Plan 5 - React Dashboard, Review Workflow, and Demo UI Execution Tasks

## Purpose

Build the React + TypeScript frontend MVP for role profile creation, job ingestion, review approval/rejection, tracked-job status updates, score breakdowns, and batch cost/performance metrics.

This task file is planning-only. It does not implement runtime code, product tests, migrations, backend logic, frontend files, or configuration changes.

## Authoritative Source

Source precedence for execution:

1. `docs/plans/Master_Plan.md` is the architecture and MVP source of truth.
2. `docs/plans/Plan_5.md` defines the approved Phase 5 frontend boundary and detailed React/API behavior where it does not conflict with the master plan.
3. `README.md` records the current project state after Phase 4 and must be treated as the implementation baseline.
4. `shared/api-contract.json` is the generated backend contract artifact that the frontend must test against; it is an implementation input, not an independent architecture source.

Comparison result:

- No blocking architecture conflict was found between `Master_Plan.md` and `Plan_5.md`.
- `README.md` confirms Phase 4 is complete: FastAPI routes, ingestion endpoints, demo loader, seed script, mock data, local CORS for `http://localhost:5173`, and `shared/api-contract.json` already exist.
- The repository has no implemented `frontend/job-agent-ui` app yet, so Phase 5 must create the frontend app rather than revise existing React conventions.
- Plan 5's dashboard requirement to fetch `status=tracked` narrows the older master dashboard SQL example that showed only `status = 'saved'`. This is aligned with the master status flow and final MVP because tracked jobs include `saved`, `applied`, `interview`, `rejected`, and `offer`.
- Plan 5's frontend contract tests are required because the backend owns status/source constants, allowed transitions, endpoint metadata, and response schemas through `shared/api-contract.json`.
- Plan 5 explicitly forbids frontend `.env` files, direct frontend calls to OpenAI, Tavily, Qdrant, or SQLite, backend API redesign, authentication, cover letters, browser scraping, and auto-apply behavior.
- There is no required Phase 6. This task file limits mandatory work to the final MVP frontend and verification only.

## Source Section Index

- `docs/plans/Master_Plan.md` > `## 1. System Objective` -> end-to-end job matching, structured extraction, scoring, review, and tracking goal.
- `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack` -> React + TypeScript + Vite frontend with FastAPI backend.
- `docs/plans/Master_Plan.md` > `## 3. MVP Scope` -> role profiles, search, URL/text ingestion, demo mode, review, score breakdown, metrics, and manual status updates.
- `docs/plans/Master_Plan.md` > `## 4. Architecture` -> frontend consumes FastAPI and the backend owns SQLite/Qdrant/agent behavior.
- `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners` -> required manual-input warning for low-content URL parsing.
- `docs/plans/Master_Plan.md` > `## 14. Visual Score Breakdown in UI` -> score component display requirements.
- `docs/plans/Master_Plan.md` > `## 15. Cost & Performance Metrics Panel` -> batch metrics shown from stored job fields/backend aggregation.
- `docs/plans/Master_Plan.md` > `## 19. Human-in-the-Loop Rules` -> approve/reject/manual status actions remain user-controlled.
- `docs/plans/Master_Plan.md` > `## 26. API Endpoints` -> API route surface consumed by the frontend.
- `docs/plans/Master_Plan.md` > `## 31. Environment Setup` -> frontend creation and run commands.
- `docs/plans/Master_Plan.md` > `## 32. Single Root .env` -> no frontend exposure of backend secrets.
- `docs/plans/Master_Plan.md` > `## 35. Implementation Checklist` > `### Demo Readiness` and `### UI` -> demo readiness and required UI controls.
- `docs/plans/Master_Plan.md` > `## 36. Final MVP Definition` -> final MVP completion behavior.
- `docs/plans/Plan_5.md` > `## 1. Objective` -> Phase 5 final MVP outcome.
- `docs/plans/Plan_5.md` > `## 3. Prerequisites from Prior Phases` -> required backend/API/demo/contract baseline.
- `docs/plans/Plan_5.md` > `## 4. Scope` and `## 5. Out of Scope` -> exact frontend boundary.
- `docs/plans/Plan_5.md` > `## 6. Target Directory Structure` -> required frontend file/module layout.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Frontend Runtime` -> Vite setup, dependencies, scripts, port, base URL, and no frontend env files.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Pages and Navigation` -> compact app layout and required views.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### API Client` -> typed client functions and refresh behavior.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Required TypeScript API Types` -> frontend API type shape and contract drift testing.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Active Batch Handling` -> per-profile localStorage batch key and summary refresh behavior.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Role Profile UI` -> profile creation fields and active profile ID behavior.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Ingestion UI` -> search, URL, text, mock load, warning, and error display behavior.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Review Queue UI` -> pending review job cards and approve/reject refresh rules.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Tracked Jobs Dashboard` -> `status=tracked` dashboard, manual transitions, and status control behavior.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Score Breakdown` -> nullable score formatting and no frontend scoring.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Metrics Panel` -> batch summary endpoint and displayed metrics.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### UI States` -> loading, empty, error, and disabled states.
- `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Visual Design Rules` -> work-focused dashboard design and responsive behavior.
- `docs/plans/Plan_5.md` > `## 8. Implementation Steps` -> required implementation inventory.
- `docs/plans/Plan_5.md` > `## 9. Verification & Testing Plan` -> automated and manual verification commands.
- `docs/plans/Plan_5.md` > `## 10. Handoff Notes for Phase 6` -> no required Phase 6 and post-MVP hard rules.
- `README.md` > `## Directory Structure` -> current backend, mock data, shared contract, and empty frontend target location baseline.
- `README.md` > `## Setup and Running Instructions` -> established local backend setup and app route checks.
- `README.md` > `## API Schema and Contract Foundation (Phase 4 - Batch 01)` -> generated backend-owned frontend contract.
- `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)` -> route surface, `status=tracked`, batch summary, CORS, and startup wiring.
- `README.md` > `## Manual and Search Ingestion Routes (Phase 4 - Batch 03)` -> parse text, parse URL, search ingestion, and standard ingestion responses.
- `README.md` > `## Demo Loader, Fixtures, Seed Script, and Mock Load (Phase 4 - Batch 04)` -> seed script, demo fixtures, and mock-load endpoint.
- `README.md` > `## Phase 4 Verification and Boundary Checks (Batch 05)` -> verified Phase 4 backend route, contract, and demo readiness baseline.
- `shared/api-contract.json` > `endpoints`, `job_statuses`, `tracked_job_statuses`, `allowed_status_transitions`, `source_platforms`, and `schemas` -> generated contract values for frontend tests.

## Approved Architecture Summary

- The frontend is a Vite React TypeScript app under `frontend/job-agent-ui`.
- The frontend talks only to the FastAPI API at `http://localhost:8000` by default.
- Backend services remain the owners of extraction, search, scoring, deduplication, persistence, Qdrant sync, status transitions, and batch metrics.
- `shared/api-contract.json` is generated from backend constants, allowed status transitions, endpoint metadata, and Pydantic schemas. Frontend status/source unions and endpoint assumptions must be tested against it.
- The first screen is the usable dashboard/review experience, not a marketing page.
- The UI supports role profile creation/selection, public search, manual URL parsing, manual raw text parsing, mock load, pending review, approve/reject, tracked dashboard, manual status updates, score breakdowns, warnings, and batch metrics.
- Dashboard jobs are fetched with `status=tracked` and must preserve jobs after status changes to `applied`, `interview`, `rejected`, or `offer`.
- Active batch IDs are stored per role profile in localStorage using `job-agent.activeBatchId.{role_profile_id}`. There is no backend latest-batch endpoint in the MVP.
- The metrics panel uses `GET /api/batches/{batch_id}/summary` only when an active batch ID exists.
- The frontend must work from already seeded local demo data without Tavily, public internet search, URL fetching, or LLM extraction access.
- No frontend `.env` or `.env.example` files are allowed. Backend API keys and backend-only config must never be exposed to frontend code.

## Global Implementation Rules

- Before adding any helper, utility, hook, API adapter, formatter, or component abstraction, search the codebase with `grep` for equivalent logic and reuse or safely extend the existing owner.
- Do not duplicate backend business logic, score formulas, status transitions, source/status constants, endpoint metadata, or schema definitions without contract tests that fail on drift.
- Keep files focused. Split components, API client code, types, styles, and tests by responsibility instead of growing one large `App.tsx`.
- Prefer simple React state and explicit refresh functions over broad state-management libraries. Do not add Redux, Zustand, React Query, MSW, or other frameworks unless a focused test or existing convention requires it.
- Do not call OpenAI, Tavily, Qdrant, SQLite, LangChain, or LangGraph directly from browser code.
- Do not redesign backend routes, response schemas, scoring semantics, dedup policy, database schema, or generated contract structure in this phase. If the frontend contract is missing a required value, stop and report the mismatch.
- Do not implement authentication, organizations, multi-user switching, cover letter generation, auto-apply behavior, browser scraping, Playwright rendering, heavy analytics, background jobs, or latest-batch backend discovery.
- Use `.env.example` only at the repository root when needed by backend setup. Do not create `frontend/.env`, `frontend/.env.example`, `frontend/job-agent-ui/.env`, or `frontend/job-agent-ui/.env.example`.
- All state-changing UI actions must call the backend and then refresh affected data from the backend.
- Frontend tests must use mocked HTTP/client behavior and the generated contract artifact; they must not require live OpenAI, Tavily, Qdrant, public internet, or LLM extraction access.
- Keep implementation code readable and boring. Add comments only for non-obvious decisions such as contract drift protection or active-batch isolation.

## Execution Agent Coding Style Requirements

- Write clean, idiomatic, readable TypeScript and React.
- Use descriptive names for modules, functions, variables, components, props, types, tests, and CSS classes.
- Keep functions, hooks, components, and modules focused on one clear responsibility.
- Prefer simple, explicit control flow over clever abstractions.
- Follow established Vite, React, TypeScript, React Router, Axios, Vitest, and Testing Library conventions.
- Use clear typing and avoid `any`, broad catch-all data shapes, hidden global mutable state, and hardcoded backend contract values unless covered by contract tests.
- Surface backend validation errors safely without swallowing them or leaking backend-only secrets.
- Keep frontend code free of backend-only secret names and backend-only configuration values beyond the safe default API base URL.
- Add comments only for non-obvious behavior, especially contract synchronization and localStorage batch isolation.
- Avoid adding formatters, linters, frameworks, or architecture changes outside the source plan unless already present or explicitly requested.

## Batch Map

| Batch | Outcome | Depends On |
|---|---|---|
| Batch01 | Frontend scaffold, dependencies, scripts, typed API contract foundation, and API client | Phase 4 backend/API contract baseline |
| Batch02 | Application shell, role profile workflow, ingestion controls, and active batch state | Batch01 |
| Batch03 | Review queue, tracked dashboard, score breakdown, approve/reject, and manual status updates | Batch01, Batch02 |
| Batch04 | Metrics panel, UI states, responsive visual system, warnings/errors, and seeded demo readiness | Batch02, Batch03 |
| Batch05 | Contract, component, workflow, environment, and final MVP verification | Batch01, Batch02, Batch03, Batch04 |

## Mandatory Batch01 - Frontend Scaffold and API Contract Foundation

### Goal

Create the Vite React TypeScript app foundation and typed backend API boundary without building the full UI workflow yet.

### Why this batch exists

The React app must consume a backend-owned contract. Building the scaffold, scripts, types, contract tests, and API client first prevents later UI work from inventing duplicate endpoint paths, statuses, transitions, or response shapes.

### Inputs / Dependencies

- Completed Phase 4 backend routes and generated `shared/api-contract.json`.
- Existing root project with an empty or missing `frontend/job-agent-ui` app.
- Node/npm available locally for Vite setup.

### Tasks

- [x] (01A): Verify Phase 5 prerequisites and frontend baseline
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 3. Prerequisites from Prior Phases`
    - `docs/plans/Plan_5.md` > `## 5. Out of Scope`
    - `README.md` > `## API Schema and Contract Foundation (Phase 4 - Batch 01)`
    - `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)`
  - Source Requirements:
    - Plan 4 FastAPI routes, demo seeding, CORS, stable schemas, and generated contract must exist.
    - `shared/api-contract.json` must be available before frontend contract tests are written.
    - Phase 5 must not redesign backend API contracts.
  - Details: Confirm the execution baseline before creating frontend code.
  - Dependencies: None.
  - User Action: None.
  - Agent Work: Inspect backend route exports, `shared/api-contract.json`, existing frontend directory contents, and root env files.
  - Specific Steps:
    1. Search for any existing `frontend/job-agent-ui` files before scaffolding.
    2. Verify `shared/api-contract.json` exists and contains endpoint metadata, statuses, source platforms, schemas, and allowed status transitions.
    3. Verify README documents Phase 4 routes, mock-load, seed script, local CORS, and `status=tracked` support.
    4. Confirm no frontend `.env` or `.env.example` files already exist.
    5. Stop and report a prerequisite mismatch if the contract or required backend route surface is missing.
  - Output: Confirmed prerequisite checklist or explicit blocker report.
  - Acceptance: Execution can proceed without backend contract redesign or earlier-phase repair.
  - Validation: File existence and import/route smoke checks from the README where needed.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only if the user must approve a separate earlier-phase repair.
  - Files: Existing files only; no source edits expected for this task.

- [x] (01B): Scaffold the Vite React TypeScript app and install required dependencies
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 6. Target Directory Structure`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Frontend Runtime`
    - `docs/plans/Master_Plan.md` > `## 2. Final MVP Stack`
    - `docs/plans/Master_Plan.md` > `## 31. Environment Setup`
  - Source Requirements:
    - Create `frontend/job-agent-ui` with the React TypeScript Vite template.
    - Install `react-router-dom`, `axios`, and `lucide-react`.
    - Add `dev`, `build`, `typecheck`, `test`, and `preview` scripts.
    - Do not create frontend `.env` or `.env.example` files.
  - Details: Establish the frontend package and local development/test scripts required by the phase.
  - Dependencies: (01A).
  - User Action: None.
  - Agent Work: Scaffold the app, install runtime and test dependencies, add required scripts, and keep generated files within `frontend/job-agent-ui`.
  - Specific Steps:
    1. Use the Vite React TypeScript template for `frontend/job-agent-ui` unless the directory already contains an app.
    2. Install runtime dependencies `react-router-dom`, `axios`, and `lucide-react`.
    3. Install test dependencies `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, and `jsdom`.
    4. Ensure `package.json` includes `dev`, `build`, `typecheck`, `test`, and `preview`.
    5. Configure Vite/Vitest for `jsdom` and `src/test/setup.ts`.
    6. Remove or avoid any frontend env files generated by tools.
  - Output: Frontend package scaffold with required dependencies and scripts.
  - Acceptance: `npm install` completes and package scripts are present.
  - Validation: `cd frontend/job-agent-ui; npm run typecheck` after initial code compiles, plus env-file path checks.
  - Blocked Condition: None.
  - Files: `frontend/job-agent-ui/package.json`, `frontend/job-agent-ui/index.html`, `frontend/job-agent-ui/vite.config.ts`, `frontend/job-agent-ui/tsconfig*.json`, `frontend/job-agent-ui/src/*`.

- [x] (01C): Add TypeScript API types and contract drift tests
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Required TypeScript API Types`
    - `docs/plans/Plan_5.md` > `## 8. Implementation Steps`
    - `shared/api-contract.json` > `job_statuses`, `jd_statuses`, `parse_statuses`, `extraction_statuses`, `source_platforms`, `tracked_job_statuses`, `allowed_status_transitions`, and `schemas`
  - Source Requirements:
    - `src/types/api.ts` must include complete nullable types for role profiles, jobs, ingestion responses, statuses, warnings, and batch metrics.
    - Frontend status/source unions mirror backend API response values and are not independent sources of truth.
    - Contract tests must load `../../shared/api-contract.json` from `frontend/job-agent-ui`.
    - Tests must fail if backend-approved values, source platforms, endpoint metadata, allowed transitions, or key schema names drift.
  - Details: Create the frontend type layer and direct tests against the generated backend contract.
  - Dependencies: (01B).
  - User Action: None.
  - Agent Work: Add API types, stable exported arrays/maps where needed for runtime UI, and tests that compare them to `shared/api-contract.json`.
  - Specific Steps:
    1. Search for existing frontend API type definitions before creating `src/types/api.ts`.
    2. Define `JobStatus`, `JdStatus`, `ParseStatus`, `ExtractionStatus`, source platform values, `RoleProfile`, `Job`, `IngestionResponse`, `BatchSummary`, and request/response types used by the client.
    3. Preserve nullable backend fields such as score components, status fields, error reasons, token/cost fields, and timestamps.
    4. Add a contract test that reads `path.resolve(process.cwd(), "../../shared/api-contract.json")`.
    5. Compare frontend job/JD/parse/extraction/source unions to the generated contract.
    6. Compare endpoint metadata names/paths/methods used by the client to the generated contract.
    7. Compare allowed status transitions and ensure unsupported values such as `archived` are not present.
  - Output: `src/types/api.ts`, `src/test/setup.ts`, and `src/test/apiContract.test.ts`.
  - Acceptance: Type unions, endpoint assumptions, and transition data cannot drift silently from the generated backend contract.
  - Validation: `cd frontend/job-agent-ui; npm test -- --run src/test/apiContract.test.ts`.
  - Blocked Condition: None.
  - Files: `frontend/job-agent-ui/src/types/api.ts`, `frontend/job-agent-ui/src/test/setup.ts`, `frontend/job-agent-ui/src/test/apiContract.test.ts`, `frontend/job-agent-ui/vite.config.ts`.

- [x] (01D): Add a typed FastAPI client with safe error surfacing
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### API Client`
    - `docs/plans/Master_Plan.md` > `## 26. API Endpoints`
    - `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)`
    - `README.md` > `## Manual and Search Ingestion Routes (Phase 4 - Batch 03)`
  - Source Requirements:
    - Implement `createRoleProfile`, `listRoleProfiles`, `searchJobs`, `parseJobUrl`, `parseJobText`, `loadMockJobs`, `getReviewJobs`, `approveJob`, `rejectJob`, `updateJobStatus`, `getJobs`, `getJobDetail`, and `getBatchSummary`.
    - Backend base URL defaults in code to `http://localhost:8000`.
    - `getJobs` must support `status?: "saved" | "tracked" | JobStatus`.
    - Client functions return typed data and surface backend validation errors without swallowing them.
  - Details: Centralize all HTTP calls and error normalization in one client module.
  - Dependencies: (01C).
  - User Action: None.
  - Agent Work: Implement the Axios client, typed request/response functions, and focused tests or mocked assertions for paths and error handling.
  - Specific Steps:
    1. Search for existing API clients before creating `src/api/client.ts`.
    2. Create one Axios instance with the safe default base URL.
    3. Implement every required endpoint function using paths from the generated contract test expectations.
    4. Normalize backend validation/service errors into a small frontend-safe error shape or message helper.
    5. Ensure no backend secrets or backend-only env names are referenced in client code.
    6. Add focused tests for typed function paths, query params, and validation error surfacing where practical.
  - Output: `src/api/client.ts` and API client tests if needed.
  - Acceptance: UI components can call all required backend endpoints through typed functions only.
  - Validation: `cd frontend/job-agent-ui; npm run typecheck; npm test -- --run`.
  - Blocked Condition: None.
  - Files: `frontend/job-agent-ui/src/api/client.ts`, optional `frontend/job-agent-ui/src/test/apiClient.test.ts`.

### Files or Modules Likely Created or Updated

- `frontend/job-agent-ui/package.json`
- `frontend/job-agent-ui/index.html`
- `frontend/job-agent-ui/vite.config.ts`
- `frontend/job-agent-ui/tsconfig.json`
- `frontend/job-agent-ui/src/main.tsx`
- `frontend/job-agent-ui/src/App.tsx`
- `frontend/job-agent-ui/src/api/client.ts`
- `frontend/job-agent-ui/src/types/api.ts`
- `frontend/job-agent-ui/src/test/setup.ts`
- `frontend/job-agent-ui/src/test/apiContract.test.ts`
- Optional focused API client tests under `frontend/job-agent-ui/src/test/`

### Required Outputs / Artifacts

- A Vite React TypeScript package under `frontend/job-agent-ui`.
- Required frontend runtime and test dependencies installed.
- Required npm scripts present.
- Typed frontend API models.
- Generated-contract drift tests.
- Typed FastAPI client.

### Acceptance Criteria

- The app scaffold exists under `frontend/job-agent-ui`.
- Frontend scripts include `dev`, `build`, `typecheck`, `test`, and `preview`.
- Frontend API types cover Plan 5 job, role profile, ingestion, status, warning, and batch summary shapes.
- Contract tests read `shared/api-contract.json` from the repository root and fail on drift.
- The API client has all required functions and defaults to `http://localhost:8000`.
- No frontend `.env` or `.env.example` files exist.

### Required Tests or Validations

- `cd frontend/job-agent-ui; npm install`
- `cd frontend/job-agent-ui; npm run typecheck`
- `cd frontend/job-agent-ui; npm test -- --run`
- `Test-Path frontend/.env`
- `Test-Path frontend/.env.example`
- `Test-Path frontend/job-agent-ui/.env`
- `Test-Path frontend/job-agent-ui/.env.example`

### Explicit Non-Goals

- Do not implement backend route changes.
- Do not add authentication, cover letters, browser scraping, auto-apply, or latest-batch discovery.
- Do not add frontend environment files or expose backend secrets.
- Do not build the full UI workflow in Batch01 beyond minimal app scaffolding needed for compilation.

## Mandatory Batch02 - App Shell, Role Profiles, Ingestion, and Active Batch State

### Goal

Build the initial application workflow for selecting/creating role profiles, running ingestion actions, capturing warnings, and maintaining active role/batch state.

### Why this batch exists

Review, dashboard, and metrics behavior depends on the active role profile and active batch ID. This batch establishes those shared frontend state rules before job workflow controls are added.

### Inputs / Dependencies

- Batch01 scaffold, types, contract tests, and API client.
- Backend role profile and ingestion endpoints from Phase 4.
- Generated contract values for endpoint paths and response shapes.

### Tasks

- [x] (02A): Build compact app shell and navigation
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Pages and Navigation`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Visual Design Rules`
    - `docs/plans/Master_Plan.md` > `## 36. Final MVP Definition`
  - Source Requirements:
    - Required views are Review Queue and Tracked Jobs Dashboard.
    - The first screen must be the usable dashboard/review experience with role profile controls and ingestion actions visible.
    - Use a compact app layout, not a marketing landing page.
  - Details: Create the top-level page layout, route/navigation structure, and shared state container needed by later components.
  - Dependencies: (01D).
  - User Action: None.
  - Agent Work: Implement `App`, route/page components, app shell, navigation, and base CSS hooks without overbuilding unrelated screens.
  - Specific Steps:
    1. Search existing frontend components before creating new ones.
    2. Create `AppShell` with compact navigation for Review Queue and Tracked Jobs Dashboard.
    3. Wire React Router or simple route state using `react-router-dom`.
    4. Keep role profile controls and ingestion actions visible from the primary workflow surface.
    5. Add CSS variables for background, surface, border, accent, and muted text colors.
    6. Avoid marketing copy, hero layout, nested cards, and decorative-only visuals.
  - Output: App shell, pages, route/navigation wiring, and initial stylesheet.
  - Acceptance: The app opens directly into a usable dashboard/review layout.
  - Validation: `cd frontend/job-agent-ui; npm run typecheck; npm run build`.
  - Blocked Condition: None.
  - Files: `src/App.tsx`, `src/components/AppShell.tsx`, `src/pages/DashboardPage.tsx`, `src/pages/ReviewPage.tsx`, `src/styles/app.css`, `src/main.tsx`.

- [x] (02B): Build role profile creation and selection UI
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Role Profile UI`
    - `docs/plans/Master_Plan.md` > `## 3. MVP Scope`
    - `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)`
  - Source Requirements:
    - Role profile fields are target role, level, location, accept remote, skills, and resume/profile text.
    - Use the backend response ID as the active `role_profile_id`.
    - Role profiles are created and listed through FastAPI only.
  - Details: Add a focused profile panel and active profile state that other workflows can consume.
  - Dependencies: (02A).
  - User Action: None.
  - Agent Work: Implement role profile list/create form, active selection behavior, validation/error display, and refresh from backend after creation.
  - Specific Steps:
    1. Fetch existing role profiles with `listRoleProfiles` on startup.
    2. Render an empty state when no profile exists.
    3. Add a creation form with the required fields and simple input validation aligned with backend errors.
    4. Split skills input into the typed payload shape expected by the API.
    5. After successful creation, set the returned backend ID as active and refresh the list.
    6. Notify active-batch state logic when the active role profile changes.
  - Output: `RoleProfilePanel` and active role profile state.
  - Acceptance: User can create or select a role profile and downstream components receive the active backend ID.
  - Validation: Component test where practical; manual create/select smoke test against local backend.
  - Blocked Condition: None.
  - Files: `src/components/RoleProfilePanel.tsx`, `src/App.tsx`, `src/types/api.ts`, `src/api/client.ts`.

- [x] (02C): Build ingestion controls and warning display
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Ingestion UI`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Active Batch Handling`
    - `docs/plans/Master_Plan.md` > `## 7. Handling JavaScript Pages and Cookie Banners`
    - `README.md` > `## Manual and Search Ingestion Routes (Phase 4 - Batch 03)`
    - `README.md` > `## Demo Loader, Fixtures, Seed Script, and Mock Load (Phase 4 - Batch 04)`
  - Source Requirements:
    - Provide controls for public job search query, manual public URL paste, manual raw job text paste, and demo/mock load.
    - Use configured backend limits and show backend validation errors when limits are exceeded.
    - Show `IngestionResponse.warnings` in a short ingestion result area.
    - Show the manual-input warning for URL parsing failures.
  - Details: Add ingestion commands without placing provider logic or backend limits in browser code.
  - Dependencies: (02B).
  - User Action: None.
  - Agent Work: Implement `IngestionPanel`, submit handlers, in-flight disabled states, ingestion result area, and callback hooks for refresh/active-batch updates.
  - Specific Steps:
    1. Require an active role profile before enabling ingestion actions.
    2. Add search, URL, raw text, and mock-load form controls.
    3. Call `searchJobs`, `parseJobUrl`, `parseJobText`, and `loadMockJobs` through the API client only.
    4. Surface backend validation/service errors in a safe error state.
    5. Render all response warnings in the ingestion result area.
    6. For URL parsing low-content/manual-input responses, display the exact user-facing warning from Plan 5.
    7. Do not attach transient ingestion warnings to job cards unless the backend later returns job-keyed metadata.
  - Output: Ingestion panel and warning/error result area.
  - Acceptance: All four ingestion actions call the backend and expose warnings/errors without direct provider calls.
  - Validation: Component or mocked-client tests for successful ingestion, validation errors, and manual-input warning rendering.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only when live external credentials are needed for a manual live search/URL validation; mock-load and seeded-data UI must remain testable without them.
  - Files: `src/components/IngestionPanel.tsx`, `src/App.tsx`, `src/api/client.ts`, `src/types/api.ts`.

- [x] (02D): Implement active role and active batch state isolation
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Active Batch Handling`
    - `docs/plans/Plan_5.md` > `## 8. Implementation Steps`
  - Source Requirements:
    - Store `response.batch_id` as `activeBatchId` in component state and localStorage after successful search, parse-url, parse-text, or mock-load.
    - Use localStorage key `job-agent.activeBatchId.{role_profile_id}`.
    - Reload the profile-specific active batch ID when switching role profiles.
    - Never reuse an active batch ID across different role profiles.
    - Do not invent a backend latest-batch endpoint.
  - Details: Centralize active batch behavior so metrics, ingestion, review, and dashboard refresh logic use the same state.
  - Dependencies: (02B), (02C).
  - User Action: None.
  - Agent Work: Implement active batch state helpers, successful-ingestion handler, role-switch reload behavior, and tests for key isolation.
  - Specific Steps:
    1. Search for existing localStorage helpers before adding new code.
    2. Build a small local helper for deriving `job-agent.activeBatchId.{role_profile_id}`.
    3. Write the key only after a successful ingestion response with a `batch_id`.
    4. Read the key after selecting or creating a role profile.
    5. Reset the metrics view when no stored key exists for a profile.
    6. Avoid any call to a non-existent latest-batch endpoint.
    7. Add tests proving role profile keys are isolated and switching profiles uses or clears the correct active batch ID.
  - Output: Active profile/batch state integration and localStorage tests.
  - Acceptance: Active batch state persists per profile and cannot leak across profiles.
  - Validation: `cd frontend/job-agent-ui; npm test -- --run src/test/activeBatch.test.tsx`.
  - Blocked Condition: None.
  - Files: `src/App.tsx`, optional focused state helper file, `src/test/activeBatch.test.tsx`.

### Files or Modules Likely Created or Updated

- `frontend/job-agent-ui/src/App.tsx`
- `frontend/job-agent-ui/src/main.tsx`
- `frontend/job-agent-ui/src/components/AppShell.tsx`
- `frontend/job-agent-ui/src/components/RoleProfilePanel.tsx`
- `frontend/job-agent-ui/src/components/IngestionPanel.tsx`
- `frontend/job-agent-ui/src/pages/DashboardPage.tsx`
- `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
- `frontend/job-agent-ui/src/styles/app.css`
- `frontend/job-agent-ui/src/test/activeBatch.test.tsx`

### Required Outputs / Artifacts

- Compact app shell with Review Queue and Tracked Jobs Dashboard navigation.
- Role profile create/select UI.
- Search, URL, raw text, and mock-load ingestion controls.
- Ingestion warnings and safe error display.
- Active role profile and per-profile active batch state.
- LocalStorage isolation tests for active batch IDs.

### Acceptance Criteria

- First screen is a usable app workflow with profile and ingestion controls visible.
- User can create/select a role profile using backend IDs.
- Ingestion actions call backend API client functions only.
- Successful ingestion stores active batch ID in state and in the profile-specific localStorage key.
- Switching profiles reloads only that profile's active batch key or clears metrics state.
- No latest-batch endpoint is invented.

### Required Tests or Validations

- `cd frontend/job-agent-ui; npm run typecheck`
- `cd frontend/job-agent-ui; npm test -- --run`
- Manual smoke test with local backend for profile creation and mock-load.
- Browser devtools check that ingestion actions call only FastAPI endpoints.

### Explicit Non-Goals

- Do not implement score formulas or provider calls in the frontend.
- Do not persist active batch state globally across profiles.
- Do not build review approval/status update workflow in Batch02 beyond refresh callback placeholders.
- Do not add frontend environment files.

## Mandatory Batch03 - Review Queue, Tracked Dashboard, Score Breakdown, and Status Workflows

### Goal

Build the core human-in-the-loop job review and tracking workflows using backend-owned status transitions and score data.

### Why this batch exists

The final MVP depends on users reviewing pending jobs, approving or rejecting them, viewing ranked tracked jobs, inspecting score breakdowns, and updating application status manually.

### Inputs / Dependencies

- Batch01 API client and contract tests.
- Batch02 active role/profile and ingestion refresh state.
- Backend review, dashboard, approve, reject, status, detail, and batch summary endpoints.

### Tasks

- [x] (03A): Build shared job card and score breakdown components
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Review Queue UI`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Tracked Jobs Dashboard`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Score Breakdown`
    - `docs/plans/Master_Plan.md` > `## 14. Visual Score Breakdown in UI`
  - Source Requirements:
    - Job cards show title, company, location, final score percent, JD status, current status, source platform, and warning/error when available.
    - Score breakdown shows Semantic Similarity, Skill Overlap, Location Match, Level Match, JD Confidence, and Final Score.
    - Null scores render as `Not scored`.
    - If `should_score_similarity = false`, show `Not scored` for the whole breakdown.
    - Never compute missing component scores in the frontend.
  - Details: Build reusable display components that format backend values but do not recompute backend-owned scoring.
  - Dependencies: (02D).
  - User Action: None.
  - Agent Work: Implement `JobCard`, `ScoreBreakdown`, nullable formatting helpers, and rendering tests.
  - Specific Steps:
    1. Search for existing formatting helpers before adding score/status formatters.
    2. Format backend score fields only: `null` to `Not scored`, `0.85` to `85%`.
    3. Render persisted per-job issues from `Job.error_reason`.
    4. Render score breakdown as an accordion, popover, or modal without layout shift.
    5. Ensure non-scorable jobs clearly show `Not scored` without recalculating values.
    6. Add tests for null score fields, non-scorable jobs, and per-job `error_reason` rendering.
  - Output: Job display and score breakdown components.
  - Acceptance: Review and dashboard pages can reuse one backend-value-only job display surface.
  - Validation: `cd frontend/job-agent-ui; npm test -- --run` and visual smoke check.
  - Blocked Condition: None.
  - Files: `src/components/JobCard.tsx`, `src/components/ScoreBreakdown.tsx`, optional formatter helper, rendering tests.

- [x] (03B): Build review queue and approve/reject actions
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Review Queue UI`
    - `docs/plans/Master_Plan.md` > `## 19. Human-in-the-Loop Rules`
    - `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)`
  - Source Requirements:
    - Review queue calls `getReviewJobs(activeRoleProfileId)`.
    - Pending job cards show approve and reject actions.
    - Approve calls `POST /api/jobs/{id}/approve`, then refreshes review queue, tracked dashboard, and active batch metrics if selected.
    - Reject calls `POST /api/jobs/{id}/reject`, then refreshes review queue and active batch metrics if selected.
    - Actions are disabled while in flight.
  - Details: Implement the pending review workflow using backend status endpoints only.
  - Dependencies: (03A).
  - User Action: None.
  - Agent Work: Implement `ReviewQueue`, fetch lifecycle, approve/reject handlers, empty/loading/error states, and refresh callbacks.
  - Specific Steps:
    1. Fetch review jobs only when an active role profile exists.
    2. Render a clear empty state when no pending review jobs exist.
    3. Disable approve/reject buttons while a mutation is running.
    4. Call `approveJob` or `rejectJob` through the API client.
    5. After approve, refresh review queue, tracked dashboard, and metrics when an active batch exists.
    6. After reject, refresh review queue and metrics when an active batch exists.
    7. Surface backend mutation errors safely without changing local state optimistically.
  - Output: Review queue page/component and approve/reject mutation flow.
  - Acceptance: Pending jobs move correctly after backend confirmation and affected data is refreshed from the backend.
  - Validation: Mocked component tests for approve/reject refresh calls; manual smoke test with mock-loaded jobs.
  - Blocked Condition: None.
  - Files: `src/components/ReviewQueue.tsx`, `src/pages/ReviewPage.tsx`, `src/components/JobCard.tsx`, tests.

- [x] (03C): Build tracked jobs dashboard using backend tracked status
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Tracked Jobs Dashboard`
    - `docs/plans/Plan_5.md` > `## 8. Implementation Steps`
    - `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)`
  - Source Requirements:
    - Dashboard calls `getJobs(activeRoleProfileId, "tracked")`.
    - Backend owns sorting by `final_score`.
    - Dashboard includes jobs with `saved`, `applied`, `interview`, `rejected`, and `offer`.
    - Dashboard must not filter to only `saved`.
    - Jobs remain visible after manual status changes.
  - Details: Add the ranked tracked jobs view as the main dashboard surface.
  - Dependencies: (03A), (03B).
  - User Action: None.
  - Agent Work: Implement dashboard fetch/render behavior, empty/loading/error states, and a test proving `status=tracked` is used.
  - Specific Steps:
    1. Fetch dashboard jobs only when an active role profile exists.
    2. Call `getJobs(activeRoleProfileId, "tracked")`.
    3. Render tracked job cards with score breakdown and current status.
    4. Preserve backend order and do not sort or filter out tracked statuses in the frontend.
    5. Add a mocked client assertion that dashboard fetches with `status=tracked`, not `saved`.
    6. Add a test or scenario proving applied/interview/rejected/offer jobs remain in the dashboard list when returned by the backend.
  - Output: Tracked dashboard page/component.
  - Acceptance: The dashboard shows all backend-tracked statuses in backend score order.
  - Validation: Dashboard mocked-client test and manual status-change smoke test.
  - Blocked Condition: None.
  - Files: `src/pages/DashboardPage.tsx`, `src/components/JobCard.tsx`, dashboard tests.

- [x] (03D): Build status select and manual status update workflow
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Tracked Jobs Dashboard`
    - `shared/api-contract.json` > `allowed_status_transitions` and `tracked_job_statuses`
    - `docs/plans/Master_Plan.md` > `## 19. Human-in-the-Loop Rules`
  - Source Requirements:
    - Manual statuses are `applied`, `interview`, `rejected`, and `offer`.
    - If current status is `saved`, show `applied` and `rejected`.
    - If current status is `applied`, show `interview` and `rejected`.
    - If current status is `interview`, show `rejected` and `offer`.
    - If current status is `rejected` or `offer`, disable or hide status controls.
    - Dropdown must never offer `pending_review`, `saved`, or `ignored`.
    - Options must be tested against `allowed_status_transitions` from the contract.
  - Details: Add status controls that reflect backend-approved transition paths instead of frontend-only maps.
  - Dependencies: (03C).
  - User Action: None.
  - Agent Work: Implement `StatusSelect`, wire `updateJobStatus`, refresh dashboard/metrics after status changes, and contract-backed tests.
  - Specific Steps:
    1. Derive or validate valid options from contract-backed transition constants.
    2. Render only valid manual target statuses for the current status.
    3. Disable or hide controls for terminal states `rejected` and `offer`.
    4. Never offer `pending_review`, `saved`, or `ignored` as manual update targets.
    5. Call `updateJobStatus` through the API client only after user selection.
    6. Disable the control while the mutation is in flight.
    7. Refresh tracked dashboard and active batch metrics after backend success.
    8. Add `StatusSelect` tests that compare options to `shared/api-contract.json`.
  - Output: Status select component and manual status update flow.
  - Acceptance: Manual status transitions match the backend contract and refresh from backend after mutation.
  - Validation: `cd frontend/job-agent-ui; npm test -- --run src/test/StatusSelect.test.tsx`.
  - Blocked Condition: None.
  - Files: `src/components/StatusSelect.tsx`, `src/pages/DashboardPage.tsx`, `src/test/StatusSelect.test.tsx`.

### Files or Modules Likely Created or Updated

- `frontend/job-agent-ui/src/components/JobCard.tsx`
- `frontend/job-agent-ui/src/components/ScoreBreakdown.tsx`
- `frontend/job-agent-ui/src/components/ReviewQueue.tsx`
- `frontend/job-agent-ui/src/components/StatusSelect.tsx`
- `frontend/job-agent-ui/src/pages/DashboardPage.tsx`
- `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
- `frontend/job-agent-ui/src/test/StatusSelect.test.tsx`
- Optional rendering/dashboard tests under `frontend/job-agent-ui/src/test/`

### Required Outputs / Artifacts

- Review queue with approve/reject actions.
- Tracked jobs dashboard using `status=tracked`.
- Shared job card with persisted error display.
- Score breakdown component with nullable score formatting.
- Manual status control backed by contract transitions.

### Acceptance Criteria

- Pending review jobs display required fields and actions.
- Approve/reject calls backend endpoints and refreshes affected data.
- Dashboard fetches `status=tracked` and preserves tracked statuses.
- Status select offers only backend-approved manual transitions.
- Score breakdown formats backend values and never computes missing scores.
- `Job.error_reason` is shown on job cards.

### Required Tests or Validations

- `cd frontend/job-agent-ui; npm run typecheck`
- `cd frontend/job-agent-ui; npm test -- --run`
- Manual smoke test: mock-load, approve one job, reject one job, update a tracked job status, confirm dashboard persistence.

### Explicit Non-Goals

- Do not implement frontend scoring formulas.
- Do not filter dashboard jobs to `saved` only.
- Do not add frontend-only status values or transition maps that can drift from the contract.
- Do not add cover-letter, auto-apply, or application-note workflows.

## Mandatory Batch04 - Metrics, UI States, Responsive Design, and Demo Readiness

### Goal

Complete the visible MVP experience with batch metrics, robust UI states, responsive styling, warning/error handling, and seeded local demo behavior.

### Why this batch exists

The MVP must be reliable during a portfolio demo. This batch fills in the operational details that make the app clear, resilient, and usable with local seeded data even when external providers are unavailable.

### Inputs / Dependencies

- Batch02 active batch state.
- Batch03 review/dashboard/status workflows.
- Backend batch summary endpoint and seeded demo fixtures from Phase 4.

### Tasks

- [ ] (04A): Build batch metrics panel with active batch lifecycle
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Metrics Panel`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Active Batch Handling`
    - `docs/plans/Master_Plan.md` > `## 15. Cost & Performance Metrics Panel`
    - `README.md` > `## Core FastAPI Routes and App Wiring (Phase 4 - Batch 02)`
  - Source Requirements:
    - Use `GET /api/batches/{batch_id}/summary`.
    - Display jobs parsed, scorable jobs, failed extractions, total tokens, estimated cost, and average extraction time when available.
    - If there is no active batch, show an empty state instead of calling the summary endpoint.
    - Remove the localStorage key if summary returns 404 for the profile's saved batch.
    - Use stored per-job fields and backend aggregation only.
  - Details: Implement metrics display tied to the profile-specific active batch ID.
  - Dependencies: (02D), (03B), (03D).
  - User Action: None.
  - Agent Work: Implement `BatchMetrics`, fetch lifecycle, empty/error/404 behavior, formatting, and refresh hooks.
  - Specific Steps:
    1. Render an empty metrics state when no active role profile or active batch ID exists.
    2. Fetch summary only when a valid active batch ID exists.
    3. Display all required metrics with safe number/currency/time formatting.
    4. Refresh metrics after ingestion, approve, reject, and manual status update when an active batch is selected.
    5. If the summary endpoint returns 404 for a stored batch, remove only that profile's localStorage key and show the empty state.
    6. Do not compute additional analytics in the frontend.
  - Output: Batch metrics panel and active-batch summary lifecycle.
  - Acceptance: Metrics are shown only for the active profile's active batch and never leak across profiles.
  - Validation: Component tests for no-batch empty state, successful summary render, and 404 key removal.
  - Blocked Condition: None.
  - Files: `src/components/BatchMetrics.tsx`, `src/App.tsx`, metrics tests.

- [ ] (04B): Complete loading, empty, disabled, warning, and error states
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### UI States`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Ingestion UI`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Review Queue UI`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Tracked Jobs Dashboard`
  - Source Requirements:
    - Required states include loading for route fetches and actions, empty state when no profile exists, empty review queue, empty tracked jobs, backend validation/service error state, and disabled state while actions are in flight.
    - Show `IngestionResponse.warnings` after parse/search/mock-load.
    - Show `Job.error_reason` on job cards.
  - Details: Make every primary workflow state explicit and safe.
  - Dependencies: (03B), (03C), (04A).
  - User Action: None.
  - Agent Work: Audit all components and add missing state branches, error display, disabled behavior, and tests.
  - Specific Steps:
    1. Add loading states for role profile list, review queue, dashboard, metrics, and state-changing actions.
    2. Add empty states for no profile, empty review queue, empty dashboard, and no active batch metrics.
    3. Ensure all mutation buttons/selects disable while their own request is in flight.
    4. Surface backend validation/service failures in concise user-visible error messages.
    5. Render ingestion warnings only in the ingestion result area.
    6. Render persisted `Job.error_reason` on job cards.
    7. Add focused rendering tests for null scores, ingestion warnings, persisted job errors, and empty states.
  - Output: Completed UI state coverage across the app.
  - Acceptance: The UI does not silently fail, hide warnings, or allow duplicate in-flight actions.
  - Validation: `cd frontend/job-agent-ui; npm test -- --run` and manual error-state smoke checks with mocked failures where practical.
  - Blocked Condition: None.
  - Files: Existing components and UI state/rendering tests.

- [x] (04C): Implement responsive work-focused dashboard styling
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Visual Design Rules`
    - `docs/plans/Plan_5.md` > `## 4. Scope`
  - Source Requirements:
    - Build the actual app as the first screen, not a landing page.
    - Keep interface work-focused and dashboard-like.
    - Use compact panels, predictable navigation, CSS variables, restrained hover/focus states, local/system fonts, and responsive laptop/mobile layout.
    - Use `lucide-react` icons in buttons where useful.
    - Avoid decorative cards inside cards and layout shifts.
    - Ensure text, score labels, and status labels do not overlap on mobile or desktop.
  - Details: Add visual polish and responsive behavior without changing the approved product scope.
  - Dependencies: (04B).
  - User Action: None.
  - Agent Work: Implement responsive CSS, accessible focus/hover states, compact control styling, and viewport checks.
  - Specific Steps:
    1. Keep page sections full-width or unframed, using cards only for repeated job items or framed tool panels.
    2. Use CSS variables for key colors and avoid one-note palettes or decorative backgrounds.
    3. Use stable dimensions for controls that could shift during loading or hover.
    4. Use icons from `lucide-react` inside command buttons where useful.
    5. Ensure forms use appropriate controls: buttons for commands, selects for status, textareas for raw text.
    6. Check desktop and mobile viewports for overlapping text, score/status labels, and overflowing buttons.
    7. Keep local/system font fallbacks; do not require external font loading.
  - Output: Responsive app stylesheet and polished component layout.
  - Acceptance: The app is usable on laptop and mobile demo viewports without text overlap or layout shift.
  - Validation: `cd frontend/job-agent-ui; npm run build`; manual viewport checks in browser.
  - Blocked Condition: None.
  - Files: `src/styles/app.css`, component markup updates where needed.

- [x] (04D): Verify seeded local demo behavior and frontend boundary rules
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 4. Scope`
    - `docs/plans/Plan_5.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Master_Plan.md` > `## 35. Implementation Checklist` > `### Demo Readiness`
    - `README.md` > `## Demo Loader, Fixtures, Seed Script, and Mock Load (Phase 4 - Batch 04)`
  - Source Requirements:
    - Dashboard must work from already seeded local demo data without Tavily, public internet search, URL fetching, or LLM extraction access.
    - User can create a profile, run mock load, review pending jobs, approve/reject, update status, view score breakdown, and view metrics.
    - Browser code must not request OpenAI, Tavily, Qdrant, SQLite, or other backend-only services directly.
    - Confirm no frontend `.env` or `.env.example` files exist.
  - Details: Validate that the completed UI can run the demo path through FastAPI only.
  - Dependencies: (04A), (04B), (04C).
  - User Action: User must provide real backend secrets only for live Tavily/OpenAI-backed ingestion checks; mock-load and seeded-data checks must not require them after demo data is available.
  - Agent Work: Run or document the local demo smoke flow, inspect browser/network boundaries, and report any provider credential blockers separately.
  - Specific Steps:
    1. Start local Qdrant and backend according to README if running live manual verification.
    2. Run `python scripts/seed_demo.py --reset` from `backend/` only when local Qdrant and required backend credentials are configured.
    3. Start the frontend dev server.
    4. Confirm seeded or mock-loaded jobs populate review/dashboard workflows through FastAPI.
    5. Confirm score breakdown and metrics render from backend data.
    6. Confirm browser devtools show no direct calls to OpenAI, Tavily, Qdrant, SQLite, or LangGraph.
    7. Confirm no frontend env files exist.
  - Output: Demo-readiness validation result and any safe blocker summary.
  - Acceptance: The frontend supports the local demo flow without direct external provider calls from browser code.
  - Validation: Manual verification checklist from Plan 5 plus env-file path checks.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only for live provider credentials or local service startup outside the agent's control.
  - Files: No new source files expected unless defects are found in prior Batch04 components.

### Files or Modules Likely Created or Updated

- `frontend/job-agent-ui/src/components/BatchMetrics.tsx`
- `frontend/job-agent-ui/src/components/IngestionPanel.tsx`
- `frontend/job-agent-ui/src/components/JobCard.tsx`
- `frontend/job-agent-ui/src/components/ReviewQueue.tsx`
- `frontend/job-agent-ui/src/components/StatusSelect.tsx`
- `frontend/job-agent-ui/src/pages/DashboardPage.tsx`
- `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
- `frontend/job-agent-ui/src/styles/app.css`
- Additional focused rendering/metrics tests under `frontend/job-agent-ui/src/test/`

### Required Outputs / Artifacts

- Batch metrics panel.
- Complete loading, empty, disabled, warning, and error states.
- Responsive dashboard visual system.
- Seeded/demo data smoke-check result.
- Frontend boundary verification result.

### Acceptance Criteria

- Metrics display required backend summary fields and respect active batch state.
- Missing active batch shows an empty state and does not call summary.
- 404 summary responses clear only the current profile's stored batch key.
- All required UI states exist and are testable.
- Laptop and mobile layouts do not overlap important text or controls.
- Demo workflow works through FastAPI and no browser code directly calls backend-only services.
- No frontend `.env` or `.env.example` files exist.

### Required Tests or Validations

- `cd frontend/job-agent-ui; npm run typecheck`
- `cd frontend/job-agent-ui; npm run build`
- `cd frontend/job-agent-ui; npm test -- --run`
- Manual viewport check at desktop and mobile widths.
- Browser devtools/network check during demo flow.
- `Test-Path frontend/.env`
- `Test-Path frontend/.env.example`
- `Test-Path frontend/job-agent-ui/.env`
- `Test-Path frontend/job-agent-ui/.env.example`

### Explicit Non-Goals

- Do not add frontend-only analytics beyond the backend batch summary.
- Do not add external font dependencies.
- Do not add background jobs, provider dashboards, or live external-provider setup UI.
- Do not require Tavily/public URL/LLM access for the seeded-data dashboard path after data exists.

## Mandatory Batch05 - Final Frontend Verification and MVP Completion Checks

### Goal

Prove the frontend implementation satisfies Plan 5, remains synchronized with the backend contract, and completes the final MVP definition without out-of-scope features.

### Why this batch exists

The final phase closes the MVP. Verification must catch contract drift, status-flow regressions, stale active-batch behavior, frontend env leakage, and demo-readiness failures before claiming completion.

### Inputs / Dependencies

- Completed Batch01 through Batch04 frontend implementation.
- Generated `shared/api-contract.json`.
- Phase 4 backend running locally for manual end-to-end checks where needed.

### Tasks

- [ ] (05A): Complete contract and workflow tests
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 8. Implementation Steps`
    - `docs/plans/Plan_5.md` > `## 9. Verification & Testing Plan`
    - `shared/api-contract.json` > generated endpoint, schema, status, source, and transition data
  - Source Requirements:
    - Contract tests must cover JobStatus, JdStatus, ParseStatus, ExtractionStatus, source platform unions, endpoint metadata, response schema names, and StatusSelect transition options.
    - Tests must prove dashboard calls `GET /api/jobs` with `status=tracked`.
    - Tests must prove active batch keys are isolated per role profile.
    - Tests must prove profile switching uses the profile-specific key or shows empty metrics.
  - Details: Consolidate the required automated frontend coverage.
  - Dependencies: (04D).
  - User Action: None.
  - Agent Work: Fill remaining test gaps and keep them focused on Plan 5 requirements.
  - Specific Steps:
    1. Run the current frontend test suite and identify missing Plan 5 assertions.
    2. Ensure contract tests cover all required generated contract sections.
    3. Ensure active batch localStorage tests cover write, read, profile switch, no-key empty metrics, and 404 key removal.
    4. Ensure dashboard tests assert `status=tracked`.
    5. Ensure `StatusSelect` tests assert backend-approved options only.
    6. Ensure rendering tests cover null scores, ingestion warnings, and persisted `Job.error_reason`.
  - Output: Completed focused frontend test coverage.
  - Acceptance: Required Plan 5 frontend contract and workflow tests pass.
  - Validation: `cd frontend/job-agent-ui; npm test -- --run`.
  - Blocked Condition: None.
  - Files: `src/test/*.test.ts`, `src/test/*.test.tsx`, component files if defects are found.

- [ ] (05B): Run frontend build, typecheck, and contract verification
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Frontend Runtime`
  - Source Requirements:
    - `npm run build`, `npm run typecheck`, and `npm test -- --run` must pass.
    - The test runner must use Vitest with `jsdom`.
    - The backend contract should be regenerated before final frontend verification when backend code may have changed.
  - Details: Execute the required automated frontend checks and any contract export prerequisite.
  - Dependencies: (05A).
  - User Action: None unless local package installation or backend virtualenv setup is missing.
  - Agent Work: Regenerate backend contract if needed, install frontend dependencies if missing, and run the required commands.
  - Specific Steps:
    1. From `backend/`, run `python scripts/export_api_contract.py` if backend code changed or contract freshness is uncertain.
    2. From `frontend/job-agent-ui`, run `npm install` when dependencies are not installed.
    3. Run `npm run typecheck`.
    4. Run `npm test -- --run`.
    5. Run `npm run build`.
    6. Report exact failing command and safe error summary if any check fails.
  - Output: Automated verification results.
  - Acceptance: Build, typecheck, and tests pass, or failures are reported with actionable details.
  - Validation: Commands listed in the specific steps.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` only if local toolchain/package install or required backend environment setup cannot proceed without user action.
  - Files: No source edits expected unless verification exposes defects.

- [ ] (05C): Run manual MVP workflow verification
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 9. Verification & Testing Plan`
    - `docs/plans/Master_Plan.md` > `## 36. Final MVP Definition`
    - `README.md` > `## Demo Loader, Fixtures, Seed Script, and Mock Load (Phase 4 - Batch 04)`
  - Source Requirements:
    - User can create/select a profile.
    - User can load demo/mock jobs, parse raw text, and use ingestion controls.
    - Pending jobs appear in review.
    - User can approve, reject, and update status manually.
    - Score breakdown and batch metrics are visible.
    - Dashboard works from preloaded local demo data without external search/extraction access after data is seeded.
  - Details: Execute the end-to-end demo path that proves the final MVP behavior.
  - Dependencies: (05B).
  - User Action: User must provide live provider credentials only if validating Tavily/OpenAI-backed search/URL extraction; mock-load and existing seeded data checks should not require live providers.
  - Agent Work: Start required local services if feasible, run backend and frontend, perform the manual checklist, and document blocked live-provider checks separately.
  - Specific Steps:
    1. Start local Qdrant with `docker compose up -d qdrant` when running live backend verification.
    2. From `backend/`, activate the virtualenv and run `python scripts/seed_demo.py --reset` when credentials/services are available.
    3. Start `uvicorn app.main:app --reload --port 8000`.
    4. Start frontend with `npm run dev`.
    5. Create/select a role profile.
    6. Run mock load and confirm pending review jobs appear.
    7. Open score breakdown for scorable and non-scorable jobs.
    8. Approve one job and confirm it moves to tracked dashboard.
    9. Reject one job and confirm it leaves review.
    10. Update a tracked job through allowed manual statuses and confirm it remains on the dashboard.
    11. Confirm metrics update after ingestion and state-changing actions.
    12. Confirm profile switching uses isolated active batch metrics.
    13. Confirm browser console has no critical errors.
  - Output: Manual verification report with pass/fail/blocker status.
  - Acceptance: Final MVP workflow succeeds or any blocker is clearly tied to user-provided credentials/local service setup.
  - Validation: Manual checklist from Plan 5.
  - Blocked Condition: `BLOCKED_BY_USER_ACTION` for missing provider credentials, unavailable local Docker/Qdrant, missing backend `.env`, or manual setup outside the frontend implementation.
  - Files: No source edits expected unless manual verification exposes defects.

- [ ] (05D): Confirm phase boundary, environment, and non-goals
  - Source of Truth:
    - `docs/plans/Plan_5.md` > `## 5. Out of Scope`
    - `docs/plans/Plan_5.md` > `## 7. Technical Specifications` > `### Frontend Runtime`
    - `docs/plans/Plan_5.md` > `## 10. Handoff Notes for Phase 6`
    - `docs/plans/Master_Plan.md` > `## 3. MVP Scope`
    - `docs/plans/Master_Plan.md` > `## 32. Single Root .env`
  - Source Requirements:
    - No frontend `.env`, `frontend/.env.example`, or `frontend/job-agent-ui/.env.example` exists.
    - Frontend never exposes API keys or calls external AI/search/vector services directly.
    - No authentication, organizations, cover letter generation, auto-apply, authenticated LinkedIn/Facebook scraping, heavy analytics, or background jobs are added.
    - Future enhancements must be planned separately.
  - Details: Audit the final diff and runtime behavior for scope creep.
  - Dependencies: (05C).
  - User Action: None.
  - Agent Work: Inspect changed files, env paths, package dependencies, browser/network behavior, and final scope.
  - Specific Steps:
    1. Check the frontend env paths with `Test-Path`.
    2. Search frontend code for backend-only secret names and direct external service URLs.
    3. Inspect `package.json` for unapproved heavy architecture/framework additions.
    4. Inspect git diff for backend API redesign, schema changes, database changes, or out-of-scope features.
    5. Confirm final task/report notes state there is no required Phase 6.
  - Output: Scope-boundary verification result.
  - Acceptance: Final frontend implementation remains within Plan 5 and master MVP boundaries.
  - Validation: Env path checks, code search, package dependency review, git diff review.
  - Blocked Condition: None.
  - Files: No source edits expected unless boundary issues are found.

### Files or Modules Likely Created or Updated

- `frontend/job-agent-ui/src/test/apiContract.test.ts`
- `frontend/job-agent-ui/src/test/activeBatch.test.tsx`
- `frontend/job-agent-ui/src/test/StatusSelect.test.tsx`
- Additional focused tests for dashboard, metrics, warnings, score breakdown, and API client behavior.
- Existing frontend components if verification exposes defects.

### Required Outputs / Artifacts

- Passing frontend typecheck, test suite, and production build.
- Contract drift test coverage.
- Manual MVP workflow verification result.
- Environment and non-goal boundary check result.

### Acceptance Criteria

- `npm run typecheck` passes.
- `npm test -- --run` passes.
- `npm run build` passes.
- Required manual MVP workflow checks pass or are safely blocked by user-controlled setup.
- No frontend env files or backend secret exposure exists.
- No out-of-scope features are added.

### Required Tests or Validations

- `cd backend; python scripts/export_api_contract.py`
- `cd frontend/job-agent-ui; npm install`
- `cd frontend/job-agent-ui; npm run typecheck`
- `cd frontend/job-agent-ui; npm test -- --run`
- `cd frontend/job-agent-ui; npm run build`
- `Test-Path frontend/.env`
- `Test-Path frontend/.env.example`
- `Test-Path frontend/job-agent-ui/.env`
- `Test-Path frontend/job-agent-ui/.env.example`
- Manual Plan 5 verification checklist.

### Explicit Non-Goals

- Do not create a Phase 6 implementation task.
- Do not add new backend features to make frontend tests pass.
- Do not add provider credentials or fabricate external setup.
- Do not claim live Tavily/OpenAI URL/search checks are complete if user-controlled credentials or services are missing.

## Optional Future Tracks

No optional future track is part of the mandatory MVP batch chain.

Post-MVP work such as authentication, organizations, cover-letter generation, browser scraping, auto-apply behavior, heavier analytics, hosted deployment, or backend architecture migration must be planned as separate future scope and must preserve SQLite as the source of truth unless an explicit migration plan replaces it.

## Dependency Chain

- Batch01 -> Batch02
- Batch02 -> Batch03
- Batch03 -> Batch04
- Batch04 -> Batch05

Optional future tracks are outside the mandatory chain.

## Global Verification Checklist

- [ ] `frontend/job-agent-ui` exists and contains a Vite React TypeScript app.
- [ ] Required npm scripts exist: `dev`, `build`, `typecheck`, `test`, and `preview`.
- [ ] Frontend API client exposes every required Plan 5 function.
- [ ] Frontend types and runtime transition options are tested against `shared/api-contract.json`.
- [ ] Dashboard calls `getJobs(activeRoleProfileId, "tracked")`.
- [ ] Review queue calls `getReviewJobs(activeRoleProfileId)`.
- [ ] Active batch ID uses `job-agent.activeBatchId.{role_profile_id}` and is isolated per profile.
- [ ] No latest-batch backend endpoint is invented.
- [ ] `IngestionResponse.warnings` display only in the ingestion result area unless job-keyed metadata is later added by backend contract.
- [ ] Job cards display persisted `Job.error_reason`.
- [ ] Null score fields and non-scorable jobs render as `Not scored`.
- [ ] Manual status controls offer only backend-approved transitions and never offer `pending_review`, `saved`, or `ignored`.
- [ ] Batch metrics use `GET /api/batches/{batch_id}/summary` only when an active batch ID exists.
- [ ] Loading, empty, error, and disabled states are implemented for primary workflows.
- [ ] Responsive laptop and mobile layouts have no overlapping critical text or controls.
- [ ] Browser code calls FastAPI only and never calls OpenAI, Tavily, Qdrant, SQLite, LangGraph, or LangChain directly.
- [ ] No `frontend/.env`, `frontend/.env.example`, `frontend/job-agent-ui/.env`, or `frontend/job-agent-ui/.env.example` exists.
- [ ] Implementation code is clean, idiomatic, typed where appropriate, and easy to understand.
- [ ] Automated frontend typecheck, tests, and build pass.
- [ ] Final MVP manual demo workflow passes or user-controlled blockers are reported safely.

## Progress Tracker

### Batches

- [ ] Batch01 - Frontend Scaffold and API Contract Foundation
- [ ] Batch02 - App Shell, Role Profiles, Ingestion, and Active Batch State
- [ ] Batch03 - Review Queue, Tracked Dashboard, Score Breakdown, and Status Workflows
- [ ] Batch04 - Metrics, UI States, Responsive Design, and Demo Readiness
- [ ] Batch05 - Final Frontend Verification and MVP Completion Checks

### Task IDs

#### Batch01

- [ ] (01A): Verify Phase 5 prerequisites and frontend baseline
- [ ] (01B): Scaffold the Vite React TypeScript app and install required dependencies
- [ ] (01C): Add TypeScript API types and contract drift tests
- [x] (01D): Add a typed FastAPI client with safe error surfacing

#### Batch02

- [ ] (02A): Build compact app shell and navigation
- [x] (02B): Build role profile creation and selection UI
- [ ] (02C): Build ingestion controls and warning display
- [x] (02D): Implement active role and active batch state isolation

#### Batch03

- [x] (03A): Build shared job card and score breakdown components
- [x] (03B): Build review queue and approve/reject actions
- [x] (03C): Build tracked jobs dashboard using backend tracked status
- [x] (03D): Build status select and manual status update workflow

#### Batch04

- [x] (04A): Build batch metrics panel with active batch lifecycle
- [x] (04B): Complete loading, empty, disabled, warning, and error states
- [x] (04C): Implement responsive work-focused dashboard styling
- [x] (04D): Verify seeded local demo behavior and frontend boundary rules

#### Batch05

- [ ] (05A): Complete contract and workflow tests
- [ ] (05B): Run frontend build, typecheck, and contract verification
- [ ] (05C): Run manual MVP workflow verification
- [ ] (05D): Confirm phase boundary, environment, and non-goals

## Completion Reporting Rules for Future Execution Agents

### BatchXX Execution Result

#### Completed Task IDs

- (XXA): complete / partial / blocked

#### Files Created or Modified

- path

#### Tests or Validations Run

- command: result

#### User Actions Required

- action: completed / pending / not required
- details: safe summary only, never include secrets

#### Blocked-by-User Status

- status: none / BLOCKED_BY_USER_ACTION
- reason: missing API key, missing provider project, missing manual setup, missing local service, missing frontend/backend dependency install, or other safe summary

#### Validation Responsibility

- user-provided setup confirmed: yes / no / not required
- agent validation run after setup: yes / no
- validation command: result

#### Acceptance Criteria Check

- criterion: satisfied / not satisfied / blocked

#### Artifacts Produced

- artifact

#### Progress Tracker Update

- task IDs updated

#### Key Implementation Decisions

- decision

#### Risks or Open Issues

- issue

#### Notes for Next Batch

- handoff notes

Future execution agents must not claim completion unless task validations and acceptance criteria are satisfied.
