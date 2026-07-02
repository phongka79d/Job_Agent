# Readable Tool-Call History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every live and persisted chat tool call as a compact, expandable activity row with user-readable wording.

**Architecture:** A focused frontend presentation module translates stable backend tool identifiers and statuses into readable UI text. The existing `ToolCallCard` uses that module for both SSE-created calls and API-loaded history, while backend events, persistence, and single-tool orchestration remain unchanged.

**Tech Stack:** React 19, TypeScript 6, Vitest, Testing Library, Lucide React, CSS

---

### Task 1: Centralize readable tool presentation

**Files:**
- Create: `frontend/job-agent-ui/src/utils/toolCallPresentation.ts`
- Create: `frontend/job-agent-ui/src/test/toolCallPresentation.test.ts`

- [ ] **Step 1: Search for reusable name and status presentation logic**

Run:

```powershell
rg -n "split\\(\"_\"|replace.*_|statusLabel|tool.*label|humaniz" frontend/job-agent-ui/src
```

Expected: no existing shared tool-name presentation helper. Reuse any equivalent
found instead of creating a duplicate.

- [ ] **Step 2: Write the failing presentation tests**

Create `frontend/job-agent-ui/src/test/toolCallPresentation.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { getToolCallPresentation } from "../utils/toolCallPresentation";

const expectedLabels = {
  search_jobs: ["Searching for jobs", "Job search completed", "Job search failed"],
  extract_job_from_url: ["Importing job link", "Job link imported", "Job link import failed"],
  extract_job_from_text: [
    "Importing job description",
    "Job description imported",
    "Job description import failed",
  ],
  update_job_status: ["Updating job status", "Job status updated", "Job status update failed"],
  list_profile_cvs: ["Loading your CVs", "CV list loaded", "CV list could not be loaded"],
  get_active_profile_cv: ["Checking active CV", "Active CV checked", "Active CV check failed"],
  view_profile_cv_metadata: [
    "Loading CV details",
    "CV details loaded",
    "CV details could not be loaded",
  ],
  retrieve_profile_cv_chunks: ["Reading your CV", "CV reading completed", "CV reading failed"],
  analyze_cv_structure: [
    "Analyzing CV structure",
    "CV structure analyzed",
    "CV structure analysis failed",
  ],
  retrieve_profile_documents: [
    "Reading profile documents",
    "Profile documents loaded",
    "Profile documents could not be loaded",
  ],
  suggest_cv_improvements: [
    "Preparing CV suggestions",
    "CV suggestions prepared",
    "CV suggestions could not be prepared",
  ],
  create_cv_edit_draft: ["Creating CV draft", "CV draft created", "CV draft creation failed"],
  preview_cv_edit_draft: [
    "Preparing CV preview",
    "CV preview ready",
    "CV preview could not be prepared",
  ],
  export_cv_draft_to_pdf: [
    "Exporting CV draft",
    "CV draft exported",
    "CV draft export failed",
  ],
  score_cv_against_job: [
    "Comparing CV with job",
    "CV comparison completed",
    "CV comparison failed",
  ],
  set_active_cv_version: ["Setting active CV", "Active CV updated", "Active CV update failed"],
} as const;

describe("getToolCallPresentation", () => {
  it.each(Object.entries(expectedLabels))(
    "returns readable lifecycle labels for %s",
    (toolName, [running, completed, failed]) => {
      expect(getToolCallPresentation(toolName, "running")).toEqual({
        label: running,
        statusLabel: "In progress",
      });
      expect(getToolCallPresentation(toolName, "pending")).toEqual({
        label: running,
        statusLabel: "In progress",
      });
      expect(getToolCallPresentation(toolName, "success")).toEqual({
        label: completed,
        statusLabel: "Completed",
      });
      expect(getToolCallPresentation(toolName, "failed")).toEqual({
        label: failed,
        statusLabel: "Needs attention",
      });
    }
  );

  it("humanizes an unknown tool without exposing snake case", () => {
    expect(getToolCallPresentation("generate_custom_report", "running")).toEqual({
      label: "Generate custom report in progress",
      statusLabel: "In progress",
    });
    expect(getToolCallPresentation("generate_custom_report", "success")).toEqual({
      label: "Generate custom report completed",
      statusLabel: "Completed",
    });
    expect(getToolCallPresentation("generate_custom_report", "failed")).toEqual({
      label: "Generate custom report failed",
      statusLabel: "Needs attention",
    });
  });
});
```

- [ ] **Step 3: Run the test and verify the missing-module failure**

Run:

```powershell
cd frontend/job-agent-ui
npm test -- --run src/test/toolCallPresentation.test.ts
```

Expected: FAIL because `../utils/toolCallPresentation` does not exist.

- [ ] **Step 4: Implement the minimal presentation catalog**

Create `frontend/job-agent-ui/src/utils/toolCallPresentation.ts`:

```typescript
import type { ToolCallStatus } from "../types/chat";

interface ToolLifecycleLabels {
  running: string;
  success: string;
  failed: string;
}

interface ToolCallPresentation {
  label: string;
  statusLabel: string;
}

const TOOL_LABELS: Record<string, ToolLifecycleLabels> = {
  search_jobs: {
    running: "Searching for jobs",
    success: "Job search completed",
    failed: "Job search failed",
  },
  extract_job_from_url: {
    running: "Importing job link",
    success: "Job link imported",
    failed: "Job link import failed",
  },
  extract_job_from_text: {
    running: "Importing job description",
    success: "Job description imported",
    failed: "Job description import failed",
  },
  update_job_status: {
    running: "Updating job status",
    success: "Job status updated",
    failed: "Job status update failed",
  },
  list_profile_cvs: {
    running: "Loading your CVs",
    success: "CV list loaded",
    failed: "CV list could not be loaded",
  },
  get_active_profile_cv: {
    running: "Checking active CV",
    success: "Active CV checked",
    failed: "Active CV check failed",
  },
  view_profile_cv_metadata: {
    running: "Loading CV details",
    success: "CV details loaded",
    failed: "CV details could not be loaded",
  },
  retrieve_profile_cv_chunks: {
    running: "Reading your CV",
    success: "CV reading completed",
    failed: "CV reading failed",
  },
  analyze_cv_structure: {
    running: "Analyzing CV structure",
    success: "CV structure analyzed",
    failed: "CV structure analysis failed",
  },
  retrieve_profile_documents: {
    running: "Reading profile documents",
    success: "Profile documents loaded",
    failed: "Profile documents could not be loaded",
  },
  suggest_cv_improvements: {
    running: "Preparing CV suggestions",
    success: "CV suggestions prepared",
    failed: "CV suggestions could not be prepared",
  },
  create_cv_edit_draft: {
    running: "Creating CV draft",
    success: "CV draft created",
    failed: "CV draft creation failed",
  },
  preview_cv_edit_draft: {
    running: "Preparing CV preview",
    success: "CV preview ready",
    failed: "CV preview could not be prepared",
  },
  export_cv_draft_to_pdf: {
    running: "Exporting CV draft",
    success: "CV draft exported",
    failed: "CV draft export failed",
  },
  score_cv_against_job: {
    running: "Comparing CV with job",
    success: "CV comparison completed",
    failed: "CV comparison failed",
  },
  set_active_cv_version: {
    running: "Setting active CV",
    success: "Active CV updated",
    failed: "Active CV update failed",
  },
};

export function getToolCallPresentation(
  toolName: string,
  status: ToolCallStatus
): ToolCallPresentation {
  const fallbackName =
    toolName
      .split("_")
      .filter(Boolean)
      .join(" ")
      .replace(/^./, (character) => character.toUpperCase()) || "Tool";
  const labels = TOOL_LABELS[toolName];

  if (status === "success") {
    return {
      label: labels?.success ?? `${fallbackName} completed`,
      statusLabel: "Completed",
    };
  }
  if (status === "failed") {
    return {
      label: labels?.failed ?? `${fallbackName} failed`,
      statusLabel: "Needs attention",
    };
  }
  return {
    label: labels?.running ?? `${fallbackName} in progress`,
    statusLabel: "In progress",
  };
}
```

- [ ] **Step 5: Run the focused test and verify green**

Run:

```powershell
npm test -- --run src/test/toolCallPresentation.test.ts
```

Expected: all presentation cases pass.

- [ ] **Step 6: Commit the presentation catalog**

```powershell
git add -- frontend/job-agent-ui/src/utils/toolCallPresentation.ts frontend/job-agent-ui/src/test/toolCallPresentation.test.ts
git commit -m "feat: add readable tool call labels"
```

### Task 2: Replace raw cards with expandable activity history

**Files:**
- Create: `frontend/job-agent-ui/src/test/ToolCallCard.test.tsx`
- Modify: `frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx`
- Modify: `frontend/job-agent-ui/src/styles/app.css`
- Modify: `frontend/job-agent-ui/src/test/ChatTranscript.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx`

- [ ] **Step 1: Search existing expandable and time-format patterns**

Run:

```powershell
rg -n "<details|<summary|Intl\\.DateTimeFormat|completed_at|started_at|tool-call-" frontend/job-agent-ui/src
```

Expected: reuse the transcript's existing `Intl.DateTimeFormat` pattern and the
existing tool-call status classes; do not add a second generic accordion helper.

- [ ] **Step 2: Write failing component tests**

Create `frontend/job-agent-ui/src/test/ToolCallCard.test.tsx`:

```tsx
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ToolCallCard from "../components/chat/ToolCallCard";
import type { AgentToolCall } from "../types/chat";

const completedCall: AgentToolCall = {
  id: "call-1",
  conversation_id: "conv-1",
  assistant_message_id: null,
  tool_name: "retrieve_profile_cv_chunks",
  status: "success",
  input_summary: "Find evidence for Python experience",
  result_summary: "Retrieved 3 active CV chunks",
  safe_payload_json: null,
  error_message: null,
  started_at: "2026-07-02T10:00:00Z",
  completed_at: "2026-07-02T10:00:02Z",
  created_at: "2026-07-02T10:00:00Z",
  updated_at: "2026-07-02T10:00:02Z",
};

describe("ToolCallCard", () => {
  it("renders a compact readable summary and expands sanitized details", () => {
    const { container } = render(<ToolCallCard toolCall={completedCall} />);
    const details = container.querySelector("details");
    const summary = container.querySelector("summary");

    expect(details).not.toBeNull();
    expect(summary).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
    expect(within(summary as HTMLElement).getByText("CV reading completed")).toBeInTheDocument();
    expect(within(summary as HTMLElement).getByText("Completed")).toBeInTheDocument();
    expect(
      within(summary as HTMLElement).queryByText("retrieve_profile_cv_chunks")
    ).not.toBeInTheDocument();

    fireEvent.click(summary as HTMLElement);

    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Find evidence for Python experience")).toBeInTheDocument();
    expect(screen.getByText("Retrieved 3 active CV chunks")).toBeInTheDocument();
    expect(screen.getByText("2s")).toBeInTheDocument();
    expect(screen.getByText("Technical name")).toBeInTheDocument();
    expect(screen.getByText("retrieve_profile_cv_chunks")).toBeInTheDocument();
  });

  it("surfaces a readable failed state and safe error", () => {
    const { container } = render(
      <ToolCallCard
        toolCall={{
          ...completedCall,
          status: "failed",
          result_summary: null,
          error_message: "No active CV is selected.",
        }}
      />
    );

    expect(screen.getByText("CV reading failed")).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    fireEvent.click(container.querySelector("summary") as HTMLElement);
    expect(screen.getByText("No active CV is selected.")).toBeInTheDocument();
  });

  it("renders pending calls as readable in-progress activity", () => {
    render(
      <ToolCallCard
        toolCall={{
          ...completedCall,
          status: "pending",
          completed_at: null,
          result_summary: null,
        }}
      />
    );

    expect(screen.getByText("Reading your CV")).toBeInTheDocument();
    expect(screen.getByText("In progress")).toBeInTheDocument();
  });

  it("omits unavailable request and result sections", () => {
    render(
      <ToolCallCard
        toolCall={{
          ...completedCall,
          input_summary: "",
          result_summary: null,
        }}
      />
    );

    expect(screen.queryByText("Request")).not.toBeInTheDocument();
    expect(screen.queryByText("Result")).not.toBeInTheDocument();
    expect(screen.getByText("Technical name")).toBeInTheDocument();
  });

  it("omits invalid timing details", () => {
    const { container } = render(
      <ToolCallCard
        toolCall={{
          ...completedCall,
          started_at: "invalid",
          completed_at: "invalid",
          created_at: "invalid",
        }}
      />
    );

    expect(container.querySelector("time")).not.toBeInTheDocument();
    expect(container.querySelector(".tool-call-duration")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Change transcript expectations to the readable compact row**

In `frontend/job-agent-ui/src/test/ChatTranscript.test.tsx`, change the raw-name
assertion in the chronological-order test:

```typescript
expect(screen.getByText("Job search completed")).toBeInTheDocument();
expect(screen.getByText("search_jobs")).toBeInTheDocument();
```

The first assertion verifies the collapsed row. The second verifies that the
technical name remains available in its details.

- [ ] **Step 4: Add a failing persisted non-search history test**

Append this test to `frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx`:

```tsx
it("loads a readable non-search tool call from conversation history", async () => {
  vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
  vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);
  vi.mocked(listAgentToolCalls).mockResolvedValue([
    {
      ...textExtractionToolCall,
      id: "tool-cv-1",
      tool_name: "score_cv_against_job",
      input_summary: "Generate CV improvements for the selected job",
      result_summary: "Generated 3 CV improvement suggestions",
    },
  ]);

  render(
    <ChatWorkspacePage
      contextOverride={{
        ...defaultContextOverride,
        activeConversationId: "conv-existing",
      }}
    />
  );

  await waitFor(() => {
    expect(listAgentToolCalls).toHaveBeenCalledWith("conv-existing");
    expect(screen.getByText("CV comparison completed")).toBeInTheDocument();
  });

  const summary = screen.getByText("CV comparison completed").closest("summary");
  expect(summary).not.toHaveTextContent("score_cv_against_job");
  expect(screen.getByText("score_cv_against_job")).toBeInTheDocument();
});
```

Update existing `ChatWorkspacePage` expectations:

```typescript
// Keep the existing non-search event sequence:
// event: "tool_call_started", tool_name: "extract_job_from_text"
// event: "tool_call_completed", tool_name: "extract_job_from_text"

// Successful search
expect(screen.getByText("Job search completed")).toBeInTheDocument();

// Successful text extraction
expect(screen.getByText("Job description imported")).toBeInTheDocument();

// Live text extraction start
expect(screen.getByText("Importing job description")).toBeInTheDocument();
expect(screen.getByText("In progress")).toBeInTheDocument();

// Live text extraction completion
expect(screen.getByText("Job description imported")).toBeInTheDocument();
expect(screen.getByText("Completed")).toBeInTheDocument();
```

- [ ] **Step 5: Run the UI tests and verify the expected failures**

Run:

```powershell
npm test -- --run src/test/ToolCallCard.test.tsx src/test/ChatTranscript.test.tsx src/test/ChatWorkspacePage.test.tsx
```

Expected: FAIL because the current card has no readable labels, native expandable
summary, timing detail, or friendly persisted-history presentation.

- [ ] **Step 6: Implement the expandable activity row**

Replace `frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx` with:

```tsx
import {
  CheckCircle,
  ChevronDown,
  Clock,
  Loader2,
  XCircle,
} from "lucide-react";
import type { AgentToolCall } from "../../types/chat";
import { getToolCallPresentation } from "../../utils/toolCallPresentation";

interface ToolCallCardProps {
  toolCall: AgentToolCall;
}

function statusIcon(status: AgentToolCall["status"]) {
  switch (status) {
    case "running":
      return <Loader2 size={15} className="animate-spin" aria-hidden="true" />;
    case "success":
      return <CheckCircle size={15} aria-hidden="true" />;
    case "failed":
      return <XCircle size={15} aria-hidden="true" />;
    default:
      return <Clock size={15} aria-hidden="true" />;
  }
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const presentation = getToolCallPresentation(toolCall.tool_name, toolCall.status);
  const timestamp = toolCall.completed_at ?? toolCall.started_at ?? toolCall.created_at;
  const timestampValue = Date.parse(timestamp);
  const hasValidTimestamp = Number.isFinite(timestampValue);
  const startedValue = toolCall.started_at ? Date.parse(toolCall.started_at) : Number.NaN;
  const completedValue = toolCall.completed_at ? Date.parse(toolCall.completed_at) : Number.NaN;
  const durationMs = completedValue - startedValue;
  const duration =
    Number.isFinite(durationMs) && durationMs >= 0
      ? durationMs < 1000
        ? "<1s"
        : `${Math.round(durationMs / 1000)}s`
      : null;

  return (
    <article className={`tool-call-card tool-call-${toolCall.status}`}>
      <details className="tool-call-details">
        <summary
          className="tool-call-summary"
          aria-label={`${presentation.label}. ${presentation.statusLabel}. Show details`}
        >
          <span className="tool-call-primary">
            {statusIcon(toolCall.status)}
            <strong>{presentation.label}</strong>
          </span>
          <span className="tool-call-meta">
            <span className="tool-call-status">{presentation.statusLabel}</span>
            {hasValidTimestamp ? (
              <time dateTime={timestamp}>
                {new Intl.DateTimeFormat(undefined, {
                  hour: "2-digit",
                  minute: "2-digit",
                }).format(new Date(timestampValue))}
              </time>
            ) : null}
            <ChevronDown className="tool-call-chevron" size={15} aria-hidden="true" />
          </span>
        </summary>

        <div className="tool-call-body">
          {toolCall.input_summary ? (
            <div className="tool-call-detail">
              <span>Request</span>
              <p>{toolCall.input_summary}</p>
            </div>
          ) : null}
          {toolCall.result_summary ? (
            <div className="tool-call-detail">
              <span>Result</span>
              <p>{toolCall.result_summary}</p>
            </div>
          ) : null}
          {toolCall.error_message ? (
            <div className="tool-call-detail">
              <span>Error</span>
              <p className="error-text">{toolCall.error_message}</p>
            </div>
          ) : null}
          <div className="tool-call-technical">
            {duration ? (
              <span>
                Duration <strong className="tool-call-duration">{duration}</strong>
              </span>
            ) : null}
            <span>
              Technical name <code>{toolCall.tool_name}</code>
            </span>
          </div>
        </div>
      </details>
    </article>
  );
}
```

- [ ] **Step 7: Replace the existing tool-card styles**

In `frontend/job-agent-ui/src/styles/app.css`, replace the existing
`.tool-call-card` through `.tool-call-failed` block with:

```css
.tool-call-card {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: color-mix(in srgb, var(--bg-surface) 78%, transparent);
  overflow: hidden;
}

.tool-call-details {
  display: block;
}

.tool-call-summary {
  min-height: 44px;
  padding: 9px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  list-style: none;
}

.tool-call-summary::-webkit-details-marker {
  display: none;
}

.tool-call-summary:hover {
  background: var(--bg-surface-hover);
}

.tool-call-primary,
.tool-call-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tool-call-primary strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: 13px;
}

.tool-call-meta {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 11px;
}

.tool-call-status {
  padding: 2px 7px;
  border: 1px solid currentColor;
  border-radius: 999px;
}

.tool-call-chevron {
  transition: transform 0.15s ease;
}

.tool-call-details[open] .tool-call-chevron {
  transform: rotate(180deg);
}

.tool-call-body {
  display: grid;
  gap: 10px;
  padding: 0 12px 12px 35px;
  border-top: 1px solid var(--border-color);
}

.tool-call-detail {
  padding-top: 10px;
}

.tool-call-detail > span,
.tool-call-technical {
  color: var(--text-muted);
  font-size: 11px;
}

.tool-call-detail p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.tool-call-technical {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.tool-call-technical code {
  color: var(--text-secondary);
}

.tool-call-success {
  border-color: rgba(34, 197, 94, 0.28);
}

.tool-call-running,
.tool-call-pending {
  border-color: rgba(34, 211, 238, 0.55);
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.08);
}

.tool-call-failed {
  border-color: rgba(248, 113, 113, 0.45);
}

@media (max-width: 640px) {
  .tool-call-summary {
    align-items: flex-start;
  }

  .tool-call-meta time {
    display: none;
  }

  .tool-call-body {
    padding-left: 12px;
  }
}
```

- [ ] **Step 8: Run focused tests and fix only implementation defects**

Run:

```powershell
npm test -- --run src/test/toolCallPresentation.test.ts src/test/ToolCallCard.test.tsx src/test/ChatTranscript.test.tsx src/test/ChatWorkspacePage.test.tsx
```

Expected: all selected tests pass. If native `<details>` toggling behaves
differently under JSDOM, assert and set the real `open` property through the
user interaction; do not weaken the readable-label or details requirements.

- [ ] **Step 9: Commit the activity history UI**

```powershell
git add -- frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx frontend/job-agent-ui/src/styles/app.css frontend/job-agent-ui/src/test/ToolCallCard.test.tsx frontend/job-agent-ui/src/test/ChatTranscript.test.tsx frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx
git commit -m "feat: show readable tool call history"
```

### Task 3: Verify complete UI behavior

**Files:**
- Verify: `frontend/job-agent-ui/src/utils/toolCallPresentation.ts`
- Verify: `frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx`
- Verify: `frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx`
- Verify: `backend/app/api/routes_chat.py`

- [ ] **Step 1: Run the complete frontend quality gate**

Run:

```powershell
cd frontend/job-agent-ui
npm test -- --run
npm run typecheck
npm run lint
npm run build
```

Expected: all tests pass; TypeScript, lint, and production build exit
successfully without new warnings.

- [ ] **Step 2: Verify backend tool persistence and event contracts**

Run from the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q backend/tests/test_agent_event_service.py backend/tests/test_routes_chat.py backend/tests/test_tool_registry.py
```

Expected: all selected backend tests pass. No backend files should be changed.

- [ ] **Step 3: Audit registered names and raw-name rendering**

Run:

```powershell
rg -n '^\s+"[a-z_]+": ToolDefinition' backend/app/services/tool_registry.py
rg -n "toolCall\\.tool_name" frontend/job-agent-ui/src
```

Expected:

- every registered name from the first command exists in the presentation test;
- the production raw-name match is only the expanded “Technical name” detail;
- stream and API logic continue to use identifiers internally.

- [ ] **Step 4: Verify in the browser**

Start the backend from the repository root:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Start the frontend from `frontend/job-agent-ui`:

```powershell
npm run dev -- --host 127.0.0.1
```

Using the in-app browser, open `http://127.0.0.1:5173` and verify:

1. Select an active role profile and open Chat.
2. Trigger a job import or CV-reading request.
3. Confirm the running row appears immediately with a spinner and readable text.
4. Confirm completion updates the same row rather than adding a duplicate.
5. Expand the row and confirm request/result, duration, and technical name.
6. Reopen the conversation from Chat history.
7. Confirm the completed row remains in chronological position with the same
   readable label.
8. Check a narrow viewport and keyboard-toggle the summary.

- [ ] **Step 5: Review the final diff**

Run:

```powershell
git diff --check
git status --short
git diff --stat HEAD~2..HEAD
```

Expected: only the presentation utility/tests, tool-call component/tests, and
focused CSS changes are present. No backend, persistence, or orchestration files
are modified.
