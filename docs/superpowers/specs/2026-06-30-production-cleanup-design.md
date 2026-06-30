# Production Cleanup Design

## Objective

Turn the completed Job Agent MVP into a clean production-ready starting point by removing runtime demo functionality, obsolete development artifacts, confirmed dead code, unused dependencies, and historical execution documentation without redesigning the architecture or changing retained business behavior.

## Approved Boundaries

The production architecture remains:

`React -> FastAPI -> LangGraph and business services -> SQLite and Qdrant`

The cleanup must preserve:

- SQLite models, schema initialization, and database access.
- Qdrant integration and vector operations.
- LangGraph extraction workflow, nodes, prompts, and schemas used by real ingestion.
- Role profile, job ingestion, review, tracking, status, and batch-summary APIs.
- React review, dashboard, profile, ingestion, metrics, and shared job components.
- Environment loading, logging, validation, error handling, and Docker Qdrant setup.
- Existing interfaces except where a demo-only interface is removed.

The cleanup must not rename or move retained modules unless required to remove a demo-only dependency.

## Runtime Demo Slice To Remove

Remove the complete demo/mock vertical slice:

- `mock_data/` fixture datasets.
- `backend/scripts/seed_demo.py`.
- `backend/app/services/demo_loader.py`.
- `POST /api/jobs/mock-load`.
- `MockLoadRequest`.
- Backend `mock` input-source and source-platform contract values when no retained runtime caller requires them.
- Frontend Demo ingestion tab, reset control, loading state, and request path.
- Frontend `loadMockJobs` client function and `MockLoadRequest` type.
- Generated API contract entries for the removed route, schema, and runtime values.
- README instructions and architecture references for demo loading and seeding.

No replacement demo endpoint, seed path, fixture format, or sample dataset will be introduced.

## Local Data Cleanup

Known demo records must be removed before deleting the existing scoped reset logic.

The cleanup sequence is:

1. Inspect and record counts and identifiers for rows explicitly owned by the demo path without exposing record contents or secrets.
2. Verify the configured Qdrant service is available.
3. Run the existing scoped reset behavior while `demo_loader.py` still exists.
4. Remove only jobs identified by the runtime demo ownership marker, their dependent application rows, their Qdrant vectors, and demo profiles that satisfy the existing safe-deletion rules.
5. Verify the known demo rows no longer exist and unrelated user-created rows remain.

The cleanup must never wipe the SQLite database, recreate tables, clear the Qdrant collection, or delete the Qdrant volume. If Qdrant cannot be verified, local data cleanup stops and the unresolved demo state is reported instead of risking partial deletion.

## Test Policy

Runtime fake implementations are not allowed. `FakeJobExtractionClient` must be removed from production modules and production package exports.

Deterministic test doubles remain allowed when they:

- Live only under `backend/tests/` or frontend test files.
- Cannot be imported through production package APIs.
- Use neutral minimal records rather than demo users, demo jobs, fake companies, or canned showcase output.
- Exercise retained production interfaces without adding test branches to production code.
- Avoid duplicated helper logic by using focused shared test support only when multiple tests require the same behavior.

The phrase "no mock data remains" applies to runtime code, runtime APIs, generated contracts, local demo records, seed utilities, and repository datasets. It does not prohibit `unittest.mock`, `pytest` monkeypatching, Vitest mocks, HTTP stubs, or minimal deterministic test fixtures.

## Contract-First Removal Sequence

The backend API surface owns the generated contract. Removal order is mandatory:

1. Remove the backend demo route, request schema, runtime constants, and contract-export declarations.
2. Regenerate `shared/api-contract.json`.
3. Verify the regenerated contract contains no `mock-load`, `MockLoadRequest`, or removed runtime `mock` values.
4. Remove stale frontend Demo UI, client functions, types, and contract assertions against the regenerated contract.
5. Run frontend typecheck and tests immediately to catch stale client or type usage.

A contract regeneration failure blocks completion of the frontend contract cleanup.

## Dead Code And Dependency Cleanup

Every deletion requires a caller/reference search first.

Candidates already identified for confirmation include:

- Unreachable AppShell fallback placeholder UI.
- Unused Vite/React starter assets and unused stylesheets.
- Production package re-exports used only by tests.
- Development comments that describe already-completed placeholder work.
- Unused direct Python requirements such as broad LangChain packages, NumPy, Alembic, python-dotenv, and Tenacity, but only when repository imports and runtime checks confirm they are unnecessary.
- Empty directories after tracked files are removed, except required `.gitkeep` directories that serve an active runtime purpose.

Uncertain code or dependencies remain in place and are listed in the final report with the reason safe deletion could not be proven.

## Debug And Comment Cleanup

Remove runtime:

- `print(...)` calls, replacing necessary CLI status output with normal logging.
- `console.log(...)`.
- `logger.debug(...)`.
- Explicit `TODO` and `FIXME` markers.
- Temporary assertions used as development checks.
- Commented-out implementations and obsolete placeholder narration.

Real error logging, validation, and concise intent comments remain. Assertions that currently enforce production validation must be replaced with explicit validation before removal rather than silently dropped.

## Documentation Cleanup

Delete historical implementation artifacts:

- `docs/tasks/`
- `docs/reports/`
- `docs/review/`
- Obsolete phase plans under `docs/plans/`

Maintain:

- Root `README.md` as the current setup, architecture, workflow, and operations guide.
- This approved design specification.
- The implementation plan generated from this specification.

README must describe only retained production behavior and must not include demo loading, seed commands, mock datasets, removed endpoints, or obsolete phase history.

## Verification

Completion requires fresh evidence for all applicable checks:

### Data

- Known demo-row count is zero after scoped cleanup.
- Related demo application rows and Qdrant vectors are absent.
- Unrelated user-created rows are preserved.

### Static Integrity

- No runtime reference remains to removed files, symbols, routes, schemas, or contract values.
- Runtime scans find no demo loaders, seed paths, fake production clients, debug endpoints, `print`, `console.log`, `logger.debug`, `TODO`, or `FIXME`.
- Test-only mocks remain confined to test paths.
- Generated contract and frontend contract expectations agree.

### Backend

- Python compilation succeeds.
- Full backend test suite passes.
- API contract export succeeds.
- Dependency consistency check passes.
- FastAPI starts with Qdrant available.
- OpenAPI responds and excludes the removed demo endpoint.

### Frontend

- Lint passes.
- Typecheck passes.
- Full Vitest suite passes.
- Production build passes.
- Dependency tree check passes.
- Vite starts and serves the application.

### Repository

- Git diff contains only cleanup-scope changes.
- No empty obsolete directories remain.
- README matches the retained implementation.

Any failed required check blocks a completion claim and is reported with exact evidence.

## Final Report

The completion response must include:

1. Files removed.
2. Files modified.
3. Dependencies removed.
4. Remaining unresolved work.
5. Items retained because safe deletion could not be proven.

The report must distinguish runtime/demo removal from intentionally retained test doubles and must disclose any local demo data that could not be safely removed.
