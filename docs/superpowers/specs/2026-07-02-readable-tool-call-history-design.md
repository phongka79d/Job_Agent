# Readable Tool-Call History Design

**Date:** 2026-07-02

## Goal

Make every real chat tool call visible and understandable while it runs and after
the conversation is reloaded. Replace internal tool identifiers in the primary
UI with user-facing language without changing backend orchestration or adding
multi-tool execution.

## Current Behavior and Root Cause

The backend already persists tool calls and emits lifecycle events for the chat
tools it executes. The frontend also fetches persisted tool calls when loading a
conversation.

The visibility problem is in presentation:

- cards lead with raw identifiers such as `retrieve_profile_cv_chunks`;
- most tools complete too quickly for their transient status to be noticeable;
- completed cards have weak hierarchy and are easy to miss in the transcript;
- live progress and permanent history use different visual treatments; and
- only the longer job-search flow consistently feels like an observable tool
  call.

No database or API change is required for this fix.

## Scope

### Included

- A centralized frontend presentation catalog for every registered tool.
- A readable fallback for unknown future tool identifiers.
- One compact, expandable tool-call component used for live calls and history.
- Clear running, success, failed, and pending states.
- Sanitized input, result, error, timing, and technical-name details.
- Correct in-place updates when lifecycle events arrive.
- Persisted non-search tool calls shown after conversation reload.
- Accessibility, responsive styling, automated tests, and browser verification.

### Excluded

- Multi-tool orchestration within one assistant turn.
- Changes to tool selection, execution, or confirmation behavior.
- Database migrations or new tool-call persistence.
- Persisting generic Server/LLM progress messages.
- Exposing raw tool arguments, model context, or unsafe payload data.

## Architecture

### Tool presentation catalog

Add one focused frontend module that maps each registered tool identifier to
user-facing running and completed wording. `ToolCallCard` is the only consumer
of this presentation API. Stream handling and backend API types continue to use
stable internal identifiers.

The catalog covers:

| Tool identifier | Running label | Completed label | Failed label |
| --- | --- | --- | --- |
| `search_jobs` | Searching for jobs | Job search completed | Job search failed |
| `extract_job_from_url` | Importing job link | Job link imported | Job link import failed |
| `extract_job_from_text` | Importing job description | Job description imported | Job description import failed |
| `update_job_status` | Updating job status | Job status updated | Job status update failed |
| `list_profile_cvs` | Loading your CVs | CV list loaded | CV list could not be loaded |
| `get_active_profile_cv` | Checking active CV | Active CV checked | Active CV check failed |
| `view_profile_cv_metadata` | Loading CV details | CV details loaded | CV details could not be loaded |
| `retrieve_profile_cv_chunks` | Reading your CV | CV reading completed | CV reading failed |
| `analyze_cv_structure` | Analyzing CV structure | CV structure analyzed | CV structure analysis failed |
| `retrieve_profile_documents` | Reading profile documents | Profile documents loaded | Profile documents could not be loaded |
| `suggest_cv_improvements` | Preparing CV suggestions | CV suggestions prepared | CV suggestions could not be prepared |
| `create_cv_edit_draft` | Creating CV draft | CV draft created | CV draft creation failed |
| `preview_cv_edit_draft` | Preparing CV preview | CV preview ready | CV preview could not be prepared |
| `export_cv_draft_to_pdf` | Exporting CV draft | CV draft exported | CV draft export failed |
| `score_cv_against_job` | Comparing CV with job | CV comparison completed | CV comparison failed |
| `set_active_cv_version` | Setting active CV | Active CV updated | Active CV update failed |

Pending calls use the running label with an “In progress” status. Unknown
identifiers are converted from snake_case to readable title text, never shown
raw in the collapsed row.

### Shared live and history rendering

The existing `AgentToolCall` type remains the source of truth. Live SSE events
continue to create or replace calls by ID in `applyToolCallStreamEvent`.
Conversation reload continues to fetch the persisted tool-call list. Both paths
render through the same `ToolCallCard`, preventing live/history presentation
drift.

The transcript keeps chronological ordering by the existing persisted
timestamps. A tool call created after the user message and before the assistant
message therefore remains in that position when history is reopened.

## Interaction Design

Each tool call renders as a compact `<details>` activity row.

The collapsed summary contains:

- a state icon;
- friendly running/completed/failed wording;
- a readable state label;
- the relevant start or completion time; and
- stronger emphasis while active, quieter styling after completion.

Expanding the row shows only already-sanitized data:

- the input summary, when present;
- the result summary, when present;
- the safe error message for failures;
- elapsed duration when both timestamps are available; and
- the technical tool identifier in a secondary “Technical name” field.

The row is collapsed by default. It remains keyboard-operable through native
`<details>/<summary>` behavior. Icons are decorative; the textual status is
always present.

Generic Server/LLM progress remains transient. Tool lifecycle progress is
reflected in the permanent activity row; detailed progress messages may still
appear in the existing live progress area but are not added to history.

## State and Error Handling

- Lifecycle updates replace an existing call with the same ID instead of
  creating duplicates.
- Missing input or result summaries omit that detail section.
- A failed call always displays its sanitized `error_message` when expanded.
- Persisted `pending` and `running` calls remain labeled “In progress”; the UI
  does not invent a failure or completion.
- Invalid timestamps omit time or duration rather than displaying an invalid
  value.
- Unknown tool names use the readable fallback and remain inspectable through
  the technical-name detail.

## Testing

Frontend tests will be written first and will cover:

- readable labels for all registered tool identifiers;
- unknown-name fallback behavior;
- raw identifiers absent from collapsed rows;
- compact rows expanding to sanitized details and technical names;
- running, success, failed, and pending states;
- safe omission of missing summaries and invalid timestamps;
- non-search SSE calls appearing immediately and updating in place;
- non-search persisted calls loading into conversation history;
- chronological transcript ordering; and
- keyboard-accessible expansion semantics.

Verification will run the focused frontend tests, the complete frontend test
suite, TypeScript/build checks, relevant backend chat tests, and a browser pass
covering live and reloaded tool-call history.

## Success Criteria

- Users see a readable activity row for every real tool call, not only job
  search.
- No collapsed tool-call row exposes snake_case identifiers.
- Calls remain visible and correctly ordered after reopening a conversation.
- Live lifecycle changes update one row without duplicates.
- Expanding a row reveals useful sanitized context and the technical identifier.
- Existing chat orchestration, backend persistence, and generic progress behavior
  remain unchanged.
