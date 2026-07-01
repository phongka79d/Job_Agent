# Agent Workspace UI Redesign

## Objective

Restructure the existing React frontend into the three-column AI Job Agent
workspace shown by the supplied reference while preserving all current
business behavior. The screenshot defines layout and density. `DESIGN.md`
defines the final Glacial Circuit color, type, spacing, border, and interaction
tokens.

The redesign must render only values supplied by existing application state or
API responses. It must not copy sample profile names, jobs, document names,
batch IDs, metrics, skills, messages, tool results, search providers, or search
queries from the reference HTML.

## Scope

The redesign applies to all existing routes:

- Agent Chat
- Review Queue
- Tracked Jobs

It preserves:

- Role profile listing, selection, and creation
- Profile PDF listing and upload
- Public search, URL parsing, and raw-text ingestion
- Batch selection and metrics
- Persisted chat conversations, messages, and deletion
- Visible agent tool calls
- Review Queue actions
- Tracked-job status changes

No settings page, unsupported navigation destination, or new backend behavior
will be introduced.

## Implementation Approach

Restructure and restyle the existing components. Do not duplicate API calls or
business logic in replacement components. State remains owned by the current
domain component unless layout composition requires lifting an existing value
into `App`.

This approach is preferred over a CSS-only reskin because the target requires a
new layout hierarchy. It is preferred over rebuilding components because the
current components already contain tested profile, ingestion, chat, review,
tracking, and metrics behavior.

## Workspace Layout

### Left Rail

The left rail contains:

- Real role profiles returned by `listRoleProfiles`
- Active profile selection
- Profile creation
- Navigation to Chat, Review Queue, and Tracked Jobs

The rail does not render a Settings item because the application has no
settings route.

### Top Bar

The top bar contains the current workspace or route label and the active batch
identifier when one exists. The batch badge is omitted when there is no active
batch. It must not render a fallback identifier or a textual fake value.

### Center Workspace

The center column contains route-owned content:

- Chat: conversation controls, messages, tool-call states, errors, and composer
- Review Queue: existing pending-review jobs and review actions
- Tracked Jobs: existing tracked jobs, score details, and status controls

Chat history is exposed through a compact conversation toolbar that supports
selection, creation, and deletion without introducing a fourth permanent
column.

### Right Context Rail

The right rail contains:

- Active profile document list and upload action
- Active profile skills and other existing profile fields where useful
- Ingestion controls with `Search`, `URL`, and `Text` tabs
- Current batch metrics

The right rail reuses `ProfileDocumentPanel`, `IngestionPanel`, and
`BatchMetrics`. Their network calls and mutation behavior remain in the
components that currently own them.

## Real-Data Mapping

| UI content | Source |
| --- | --- |
| Profile role, level, location, remote preference, skills | Active `RoleProfile` |
| PDF filename, status, size, chunks, and timestamps | `ProfileDocument` |
| Batch identifier | Active batch state |
| Parsed/scorable/error/token/cost metrics | `BatchSummary` |
| Conversation title and session time | `ChatConversation` |
| Chat text | `ChatMessage` |
| Tool name, summary, status, and error | `AgentToolCall` |
| Job content, score, source, and status | `Job` |
| Search, URL, and raw text values | Current controlled form state |

Optional values are conditionally omitted or represented by a truthful empty
state. Input controls use visible labels and empty controlled values instead of
sample placeholder content.

Reference-only content that must not enter runtime code includes:

- Named job boards or providers not reported by the backend
- Sample profile and document names
- Sample skills
- Sample batch IDs and metrics
- Sample assistant or user messages
- Suggested command chips that do not execute existing behavior
- Decorative progress values not derived from API data

## Component Boundaries

`App.tsx` continues to own the active profile, active batch, and metrics refresh
signal.

`AppShell` becomes the responsive workspace frame. It receives route context
and composed left/right content without taking ownership of API behavior.

`RoleProfilePanel` becomes the compact profile selector and creation experience
in the left rail. Existing fetching and validation remain unchanged.

`ChatWorkspacePage` remains responsible for conversations and chat turns. Its
conversation actions move into a compact toolbar, while the existing message,
tool-call, and composer components remain focused children.

`ReviewPage` and `DashboardPage` retain their existing data loading, filtering,
and mutation behavior. Only their presentation is adapted to the workspace.

`ProfileDocumentPanel`, `IngestionPanel`, and `BatchMetrics` are restyled and
composed into the right context rail. Ingestion modes remain tabs so all three
working entry points stay visible and direct.

No component should duplicate profile, document, ingestion, batch, chat, or job
business logic already present elsewhere.

## Visual System

Use the Glacial Circuit system from `DESIGN.md`:

- Near-black teal background and progressively lighter teal surfaces
- Electric cyan for primary actions, focus, and active states
- Royal blue for secondary data emphasis
- Existing semantic error and success colors for status communication
- Sora headings, Inter body text, and Space Grotesk technical labels
- Thin borders and restrained surface contrast
- Interaction-only diffused glow for hover, focus, active navigation, and
  running tool states
- Lucide icons for familiar actions
- Card radius no greater than 8px

Do not add decorative gradient blobs, fake charts, permanent glow, oversized
marketing typography, nested cards, or nonfunctional controls.

## Responsive Behavior

Desktop uses a fixed left rail, flexible center workspace, and fixed right
context rail.

Tablet keeps a compact left rail and places the right context content below the
route workspace.

Mobile presents profile and navigation controls in a compact header, followed
by the route workspace and then context controls. Chat composition, review
actions, and job status controls must remain visible without overlap or
horizontal clipping.

## States And Errors

Loading, disabled, success, empty, and failure states are driven by existing
component state.

An error in one domain panel must not clear valid data from another panel.
Existing safe API error normalization remains in place. Missing profiles,
documents, conversations, jobs, and batches use concise empty-state text and
never substitute sample records.

## Verification

Automated tests must verify:

- API/state profile and batch values render correctly
- Batch UI is absent when no real batch exists
- Optional data never falls back to reference samples
- Profile creation and selection still work
- PDF listing and upload still work
- Search, URL, and raw-text ingestion still work
- Conversation selection, creation, deletion, messages, and tool calls work
- Review and tracked-job mutations still work
- Navigation preserves active profile and batch context

Repository checks must include:

- Runtime source scan for copied reference sample values
- Frontend typecheck
- Frontend lint
- Full frontend tests
- Production frontend build
- Backend tests if any backend or contract file changes
- Local frontend and backend startup
- Desktop, tablet, and mobile visual verification when browser automation is
  available

Existing uncommitted agent-search work must be preserved and integrated. It
must not be reverted or overwritten by the UI restructuring.
