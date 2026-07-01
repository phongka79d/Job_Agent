# Agent Workspace UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure all existing frontend views into the approved three-column Glacial Circuit agent workspace without introducing fake, sample, placeholder, or hardcoded domain values.

**Architecture:** Keep `App` as the owner of active profile, active batch, and metrics refresh state. Recompose existing API-backed domain components into a responsive workspace shell, extracting presentation units from the two oversized panels while preserving their network and mutation behavior. Build all visible domain content from existing `RoleProfile`, `ProfileDocument`, `BatchSummary`, `ChatConversation`, `ChatMessage`, `AgentToolCall`, and `Job` values.

**Tech Stack:** React 19, TypeScript 6, React Router 7, Lucide React, Axios, Vitest, Testing Library, Vite, CSS custom properties.

---

## Execution Constraints

- Work in the current workspace because the approved uncommitted chat-search tool flow is required by the redesigned UI.
- Before each edit, inspect `git diff -- <file>` and preserve every pre-existing hunk.
- Do not copy sample strings or numbers from the supplied `code.html`.
- Do not add a Settings route, fake metrics, sample messages, suggested prompts, or named search providers.
- Static interface labels such as `Agent Chat` and `Review Queue` are allowed. Domain values must come from application state or API responses.
- Keep cards at 8px radius or less and use Lucide icons.
- Use path-scoped commits. If a file contains pre-existing uncommitted hunks, do not stage it until the integrated diff has been reviewed.

## File Structure

**Create**

- `frontend/job-agent-ui/src/components/workspace/ActiveProfileSummary.tsx`  
  Renders only non-null active profile fields.
- `frontend/job-agent-ui/src/components/profile/RoleProfileForm.tsx`  
  Owns profile-creation form state, validation, and submission.
- `frontend/job-agent-ui/src/components/ingestion/IngestionModeTabs.tsx`  
  Renders the Search/URL/Text segmented control.
- `frontend/job-agent-ui/src/components/ingestion/SearchIngestionForm.tsx`  
  Controlled public-search form with no example value.
- `frontend/job-agent-ui/src/components/ingestion/UrlIngestionForm.tsx`  
  Controlled job-URL form with no example value.
- `frontend/job-agent-ui/src/components/ingestion/TextIngestionForm.tsx`  
  Controlled raw-text form with no example value.
- `frontend/job-agent-ui/src/components/chat/ConversationToolbar.tsx`  
  Renders real persisted conversations and new/delete actions.
- `frontend/job-agent-ui/src/components/PageState.tsx`  
  Shared loading, error, and empty state presentation.
- `frontend/job-agent-ui/src/test/AppShell.test.tsx`
- `frontend/job-agent-ui/src/test/ActiveProfileSummary.test.tsx`
- `frontend/job-agent-ui/src/test/ConversationToolbar.test.tsx`
- `frontend/job-agent-ui/src/test/PageState.test.tsx`

**Modify**

- `frontend/job-agent-ui/index.html`
- `frontend/job-agent-ui/src/App.tsx`
- `frontend/job-agent-ui/src/components/AppShell.tsx`
- `frontend/job-agent-ui/src/components/RoleProfilePanel.tsx`
- `frontend/job-agent-ui/src/components/IngestionPanel.tsx`
- `frontend/job-agent-ui/src/components/BatchMetrics.tsx`
- `frontend/job-agent-ui/src/components/JobCard.tsx`
- `frontend/job-agent-ui/src/components/ScoreBreakdown.tsx`
- `frontend/job-agent-ui/src/components/StatusSelect.tsx`
- `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
- `frontend/job-agent-ui/src/components/profile/ProfileDocumentUpload.tsx`
- `frontend/job-agent-ui/src/components/chat/ChatComposer.tsx`
- `frontend/job-agent-ui/src/components/chat/ChatMessageList.tsx`
- `frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx`
- `frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx`
- `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
- `frontend/job-agent-ui/src/pages/DashboardPage.tsx`
- `frontend/job-agent-ui/src/styles/app.css`
- Existing tests for every modified component

**Delete**

- `frontend/job-agent-ui/src/index.css`  
  This file is not imported. The redesign keeps one global stylesheet in
  `src/styles/app.css`.

---

### Task 1: Establish the Glacial Circuit shell and real-value guards

**Files:**
- Create: `frontend/job-agent-ui/src/test/AppShell.test.tsx`
- Modify: `frontend/job-agent-ui/src/components/AppShell.tsx`
- Modify: `frontend/job-agent-ui/src/App.tsx`
- Modify: `frontend/job-agent-ui/index.html`
- Modify: `frontend/job-agent-ui/src/styles/app.css`
- Delete: `frontend/job-agent-ui/src/index.css`

- [ ] **Step 1: Write failing shell tests**

Create `src/test/AppShell.test.tsx` with tests that render the shell inside
`MemoryRouter`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import AppShell from "../components/AppShell";

function renderShell(activeBatchId: string | null) {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route
          path="/"
          element={
            <AppShell
              sidebarContent={<div>Profile rail</div>}
              contextContent={<div>Context rail</div>}
              activeBatchId={activeBatchId}
              activeProfileId="profile-1"
            />
          }
        >
          <Route index element={<div>Route content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("renders all three workspace regions and existing routes", () => {
    renderShell("batch-from-api");
    expect(screen.getByText("Profile rail")).toBeInTheDocument();
    expect(screen.getByText("Context rail")).toBeInTheDocument();
    expect(screen.getByText("Route content")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /agent chat/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /review queue/i })).toHaveAttribute("href", "/review");
    expect(screen.getByRole("link", { name: /tracked jobs/i })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByText("batch-from-api")).toBeInTheDocument();
  });

  it("omits the batch badge when no active batch exists", () => {
    renderShell(null);
    expect(screen.queryByText(/active batch/i)).not.toBeInTheDocument();
    expect(screen.queryByText("None")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the shell tests and verify RED**

Run:

```powershell
cd frontend/job-agent-ui
npm test -- --run src/test/AppShell.test.tsx
```

Expected: FAIL because `contextContent` is not an `AppShell` prop and the
current shell always renders a batch fallback.

- [ ] **Step 3: Implement the workspace shell**

Change `AppShellProps` and the component skeleton to:

```tsx
interface AppShellProps {
  sidebarContent: React.ReactNode;
  contextContent: React.ReactNode;
  activeBatchId?: string | null;
  activeProfileId?: string | null;
  triggerMetricsRefresh?: () => void;
}

export default function AppShell({
  sidebarContent,
  contextContent,
  activeBatchId,
  activeProfileId,
  triggerMetricsRefresh,
}: AppShellProps) {
  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">{sidebarContent}</aside>
      <main className="workspace-main">
        <header className="workspace-topbar">
          <NavLink className="workspace-brand" to="/">Agent Workspace</NavLink>
          <nav className="workspace-tabs" aria-label="Workspace">
            <NavLink to="/" end className={({ isActive }) => `nav-tab${isActive ? " active" : ""}`}>
              <MessageSquare size={16} />
              <span>Agent Chat</span>
            </NavLink>
            <NavLink to="/review" className={({ isActive }) => `nav-tab${isActive ? " active" : ""}`}>
              <ClipboardList size={16} />
              <span>Review Queue</span>
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => `nav-tab${isActive ? " active" : ""}`}>
              <Layers size={16} />
              <span>Tracked Jobs</span>
            </NavLink>
          </nav>
          {activeBatchId ? (
            <div className="batch-badge">
              <span>Active batch</span>
              <strong>{activeBatchId}</strong>
            </div>
          ) : null}
        </header>
        <section className="workspace-route">
          <Outlet context={{ activeProfileId, activeBatchId, triggerMetricsRefresh }} />
        </section>
      </main>
      <aside className="workspace-context">{contextContent}</aside>
    </div>
  );
}
```

In `App.tsx`, compose the rails without moving API logic:

```tsx
const sidebar = (
  <RoleProfilePanel
    activeProfile={activeProfile}
    onProfileChange={handleProfileChange}
  />
);

const contextPanel = (
  <>
    <ActiveProfileSummary profile={activeProfile} />
    <ProfileDocumentPanel activeProfileId={activeProfile?.id ?? null} />
    <IngestionPanel
      activeProfileId={activeProfile?.id ?? null}
      onIngestionSuccess={handleIngestionSuccess}
    />
    <BatchMetrics
      activeProfileId={activeProfile?.id ?? null}
      activeBatchId={activeBatchId}
      refreshTrigger={metricsRefreshCount}
    />
  </>
);
```

Pass `contextContent={contextPanel}` to `AppShell`.

- [ ] **Step 4: Replace global tokens and base layout**

Set `index.html` title to `Job Agent Workspace` and load Sora, Inter, and Space
Grotesk. Replace the top token block in `app.css` with:

```css
:root {
  --surface: #00161d;
  --surface-lowest: #001016;
  --surface-low: #001f27;
  --surface-container: #00232c;
  --surface-high: #002f3a;
  --surface-highest: #003a47;
  --surface-bright: #003f4d;
  --text-primary: #b7ebfd;
  --text-secondary: #bac9cc;
  --text-muted: #849396;
  --border-color: #3b494c;
  --accent: #00e7fe;
  --accent-hover: #c6f7ff;
  --accent-muted: rgba(0, 231, 254, 0.1);
  --secondary: #2578d1;
  --text-danger: #ffb4ab;
  --text-success: #27d8ff;
  --font-heading: "Sora", sans-serif;
  --font-sans: "Inter", sans-serif;
  --font-label: "Space Grotesk", sans-serif;
  --font-mono: "Space Grotesk", monospace;
  --radius-lg: 8px;
  --radius-md: 6px;
  --radius-sm: 2px;
}

.workspace-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr) minmax(280px, 320px);
  background: var(--surface);
  color: var(--text-primary);
  overflow: hidden;
}

.workspace-sidebar,
.workspace-context {
  min-height: 0;
  overflow-y: auto;
  background: var(--surface-lowest);
}

.workspace-sidebar { border-right: 1px solid var(--border-color); }
.workspace-context { border-left: 1px solid var(--border-color); }
.workspace-main { min-width: 0; min-height: 0; display: grid; grid-template-rows: 56px minmax(0, 1fr); }
.workspace-route { min-width: 0; min-height: 0; overflow: auto; padding: 24px; }
```

Delete the unused `src/index.css`.

- [ ] **Step 5: Run focused tests and typecheck**

Run:

```powershell
npm test -- --run src/test/AppShell.test.tsx src/test/activeBatch.test.tsx
npm run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit clean shell files**

```powershell
git add frontend/job-agent-ui/index.html frontend/job-agent-ui/src/App.tsx frontend/job-agent-ui/src/components/AppShell.tsx frontend/job-agent-ui/src/styles/app.css frontend/job-agent-ui/src/index.css frontend/job-agent-ui/src/test/AppShell.test.tsx
git commit -m "feat: restructure agent workspace shell"
```

If any listed file includes pre-existing uncommitted hunks, defer that file from
the commit and record it for the final integrated commit.

---

### Task 2: Refactor role profiles into the left rail

**Files:**
- Create: `frontend/job-agent-ui/src/components/profile/RoleProfileForm.tsx`
- Modify: `frontend/job-agent-ui/src/components/RoleProfilePanel.tsx`
- Modify: `frontend/job-agent-ui/src/test/RoleProfilePanel.test.tsx`

- [ ] **Step 1: Add failing tests for real profile rendering**

Extend `RoleProfilePanel.test.tsx`:

```tsx
it("renders only API profiles and active profile metadata", async () => {
  vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });
  render(
    <RoleProfilePanel
      activeProfile={mockProfiles[0]}
      onProfileChange={vi.fn()}
    />,
  );

  await waitFor(() => {
    expect(screen.getByRole("option", { name: /Software Engineer/ })).toBeInTheDocument();
  });
  expect(screen.getByText("San Francisco")).toBeInTheDocument();
  expect(screen.queryByText("AI Engineer Intern")).not.toBeInTheDocument();
  expect(screen.queryByText("User Workspace Avatar")).not.toBeInTheDocument();
});
```

Update the existing select-option count assertion to expect exactly the API
profiles, because auto-selection means no synthetic placeholder option is
needed.

- [ ] **Step 2: Run the profile test and verify RED**

```powershell
npm test -- --run src/test/RoleProfilePanel.test.tsx
```

Expected: FAIL because the current selector includes a placeholder option and
does not expose the active location in the compact rail.

- [ ] **Step 3: Extract `RoleProfileForm`**

Move the six controlled fields and `createRoleProfile` call into
`RoleProfileForm.tsx`. Use this interface:

```tsx
interface RoleProfileFormProps {
  onCreated: (profile: RoleProfile) => Promise<void> | void;
  onCancel: () => void;
}
```

Submit exactly:

```tsx
const skills = skillsInput
  .split(",")
  .map((skill) => skill.trim())
  .filter(Boolean);

const payload: RoleProfileCreateRequest = {
  target_role: targetRole.trim(),
  level: level.trim() || null,
  location: location.trim() || null,
  accept_remote: acceptRemote,
  skills: skills.length > 0 ? skills : undefined,
  resume_text: resumeText.trim() || null,
};

const created = await createRoleProfile(payload);
await onCreated(created);
```

Keep visible `<label>` elements and remove example `placeholder` attributes.
Preserve the existing test IDs so current integration tests remain valid.

- [ ] **Step 4: Reduce `RoleProfilePanel` to fetch/select/layout**

Render:

```tsx
<section className="rail-section role-profile-panel">
  <div className="rail-section-heading">
    <span>Role profiles</span>
    <button
      type="button"
      className="icon-command"
      aria-label="Create profile"
      onClick={() => setShowForm(true)}
      data-testid="create-profile-btn"
    >
      <Plus size={14} />
    </button>
  </div>
  {profiles.length > 0 ? (
    <>
      <select
        value={activeProfile?.id ?? profiles[0].id}
        onChange={handleSelect}
        data-testid="profile-select"
      >
        {profiles.map((profile) => (
          <option key={profile.id} value={profile.id}>
            {[profile.target_role, profile.level].filter(Boolean).join(" - ")}
          </option>
        ))}
      </select>
      {activeProfile ? (
        <div className="active-profile-meta">
          {activeProfile.location ? <span>{activeProfile.location}</span> : null}
          {activeProfile.accept_remote ? <span>Remote</span> : null}
        </div>
      ) : null}
    </>
  ) : (
    <p data-testid="empty-profiles-state">No profiles found.</p>
  )}
  {showForm ? (
    <RoleProfileForm
      onCreated={handleCreated}
      onCancel={() => setShowForm(false)}
    />
  ) : null}
</section>
```

Keep the existing auto-selection behavior after fetching.

- [ ] **Step 5: Run profile tests**

```powershell
npm test -- --run src/test/RoleProfilePanel.test.tsx
npm run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add frontend/job-agent-ui/src/components/profile/RoleProfileForm.tsx frontend/job-agent-ui/src/components/RoleProfilePanel.tsx frontend/job-agent-ui/src/test/RoleProfilePanel.test.tsx
git commit -m "refactor: adapt role profiles to workspace rail"
```

---

### Task 3: Split and restyle the ingestion controls

**Files:**
- Create: `frontend/job-agent-ui/src/components/ingestion/IngestionModeTabs.tsx`
- Create: `frontend/job-agent-ui/src/components/ingestion/SearchIngestionForm.tsx`
- Create: `frontend/job-agent-ui/src/components/ingestion/UrlIngestionForm.tsx`
- Create: `frontend/job-agent-ui/src/components/ingestion/TextIngestionForm.tsx`
- Modify: `frontend/job-agent-ui/src/components/IngestionPanel.tsx`
- Modify: `frontend/job-agent-ui/src/test/IngestionPanel.test.tsx`

- [ ] **Step 1: Add a failing no-placeholder test**

Add:

```tsx
it("renders labeled empty ingestion controls without reference sample values", () => {
  render(<IngestionPanel activeProfileId="prof-1" />);
  const query = screen.getByLabelText("Public job search query");
  expect(query).toHaveValue("");
  expect(query).not.toHaveAttribute("placeholder");
  expect(screen.queryByDisplayValue(/AI Engineer OR Machine Learning/i)).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue(/Ha Noi, Vietnam/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the ingestion test and verify RED**

```powershell
npm test -- --run src/test/IngestionPanel.test.tsx
```

Expected: FAIL because current fields use example placeholders and labels are not
connected by `htmlFor`.

- [ ] **Step 3: Implement the mode tabs**

Use:

```tsx
export type IngestionMode = "search" | "url" | "text";

interface IngestionModeTabsProps {
  activeMode: IngestionMode;
  disabled: boolean;
  onChange: (mode: IngestionMode) => void;
}

const modes = [
  { id: "search" as const, label: "Search", icon: Search },
  { id: "url" as const, label: "URL", icon: Link },
  { id: "text" as const, label: "Text", icon: FileText },
];
```

Render buttons with `role="tab"`, `aria-selected`, existing `data-testid`
values, and Lucide icons.

- [ ] **Step 4: Implement the three controlled forms**

Each form receives value, disabled state, in-flight state, change handler, and
submit handler. For example:

```tsx
interface SearchIngestionFormProps {
  value: string;
  disabled: boolean;
  isInFlight: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}

export default function SearchIngestionForm(props: SearchIngestionFormProps) {
  return (
    <form className="ingestion-form" onSubmit={props.onSubmit} data-testid="form-search">
      <label htmlFor="public-job-query">Public job search query</label>
      <input
        id="public-job-query"
        value={props.value}
        onChange={(event) => props.onChange(event.target.value)}
        disabled={props.disabled}
        data-testid="input-search-query"
      />
      <button
        type="submit"
        className="btn-primary"
        disabled={props.disabled || !props.value.trim()}
        data-testid="btn-search-submit"
      >
        {props.isInFlight ? <Loader2 aria-label="Searching" size={14} /> : <Search size={14} />}
        <span>{props.isInFlight ? "Searching" : "Search jobs"}</span>
      </button>
    </form>
  );
}
```

Apply the same pattern to URL and Text forms. Do not add placeholder
attributes. Keep every existing test ID and submitted payload unchanged.

- [ ] **Step 5: Recompose `IngestionPanel`**

Keep `handleSearchSubmit`, `handleUrlSubmit`, `handleTextSubmit`,
`successResult`, warning handling, and API calls in `IngestionPanel`. Replace
only the tab/form JSX with the extracted components:

```tsx
<section className="rail-section ingestion-panel" data-testid="ingestion-panel">
  <h2 className="rail-section-title">Job ingestion</h2>
  <IngestionModeTabs
    activeMode={activeTab}
    disabled={isInFlight}
    onChange={(mode) => {
      setActiveTab(mode);
      resetMessages();
    }}
  />
  {activeTab === "search" ? (
    <SearchIngestionForm
      value={searchQuery}
      disabled={isDisabled}
      isInFlight={isInFlight}
      onChange={setSearchQuery}
      onSubmit={handleSearchSubmit}
    />
  ) : null}
  {activeTab === "url" ? (
    <UrlIngestionForm
      value={jobUrl}
      disabled={isDisabled}
      isInFlight={isInFlight}
      onChange={setJobUrl}
      onSubmit={handleUrlSubmit}
    />
  ) : null}
  {activeTab === "text" ? (
    <TextIngestionForm
      value={jobText}
      disabled={isDisabled}
      isInFlight={isInFlight}
      onChange={setJobText}
      onSubmit={handleTextSubmit}
    />
  ) : null}
</section>
```

After the form block, retain the existing `ingestion-error`,
`url-manual-input-warning`, `ingestion-result`, and
`ingestion-warnings-list` elements with their existing state conditions and
text.

- [ ] **Step 6: Run ingestion tests**

```powershell
npm test -- --run src/test/IngestionPanel.test.tsx src/test/apiClient.test.ts
npm run typecheck
```

Expected: PASS with the same request payload assertions.

- [ ] **Step 7: Commit**

```powershell
git add frontend/job-agent-ui/src/components/ingestion frontend/job-agent-ui/src/components/IngestionPanel.tsx frontend/job-agent-ui/src/test/IngestionPanel.test.tsx
git commit -m "refactor: split workspace ingestion controls"
```

---

### Task 4: Build the real-data context rail

**Files:**
- Create: `frontend/job-agent-ui/src/components/workspace/ActiveProfileSummary.tsx`
- Create: `frontend/job-agent-ui/src/test/ActiveProfileSummary.test.tsx`
- Modify: `frontend/job-agent-ui/src/components/profile/ProfileDocumentPanel.tsx`
- Modify: `frontend/job-agent-ui/src/components/profile/ProfileDocumentUpload.tsx`
- Modify: `frontend/job-agent-ui/src/components/BatchMetrics.tsx`
- Modify: `frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/BatchMetrics.test.tsx`

- [ ] **Step 1: Write failing active-profile tests**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ActiveProfileSummary from "../components/workspace/ActiveProfileSummary";
import type { RoleProfile } from "../types/api";

const profile: RoleProfile = {
  id: "profile-api",
  target_role: "Platform Engineer",
  level: "Senior",
  location: "Da Nang",
  accept_remote: true,
  skills: ["Go", "Kubernetes"],
  resume_text: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

describe("ActiveProfileSummary", () => {
  it("renders only fields supplied by the active profile", () => {
    render(<ActiveProfileSummary profile={profile} />);
    expect(screen.getByText("Platform Engineer")).toBeInTheDocument();
    expect(screen.getByText("Senior")).toBeInTheDocument();
    expect(screen.getByText("Da Nang")).toBeInTheDocument();
    expect(screen.getByText("Go")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
  });

  it("renders a truthful empty state without sample profile data", () => {
    render(<ActiveProfileSummary profile={null} />);
    expect(screen.getByText("Select a role profile.")).toBeInTheDocument();
    expect(screen.queryByText("AI Engineer Intern")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run context tests and verify RED**

```powershell
npm test -- --run src/test/ActiveProfileSummary.test.tsx
```

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement `ActiveProfileSummary`**

```tsx
interface ActiveProfileSummaryProps {
  profile: RoleProfile | null;
}

export default function ActiveProfileSummary({ profile }: ActiveProfileSummaryProps) {
  return (
    <section className="rail-section active-profile-summary">
      <h2 className="rail-section-title">Active profile</h2>
      {!profile ? (
        <p className="empty-copy">Select a role profile.</p>
      ) : (
        <>
          <strong>{profile.target_role}</strong>
          <div className="profile-facts">
            {profile.level ? <span>{profile.level}</span> : null}
            {profile.location ? <span>{profile.location}</span> : null}
            {profile.accept_remote ? <span>Remote</span> : null}
          </div>
          {profile.skills.length > 0 ? (
            <div className="skill-list">
              {profile.skills.map((skill) => <span key={skill}>{skill}</span>)}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Restyle documents using only document fields**

For each document, render `original_filename`, `status`, `file_size_bytes`,
`chunk_count`, and a localized `updated_at`. Compute the date:

```tsx
const updatedAt = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
}).format(new Date(document.updated_at));
```

Do not render relative phrases such as a hardcoded “4 mins ago”. Keep upload
behavior and API tests unchanged.

- [ ] **Step 5: Remove metric fallback values**

Replace `N/A` formatters with conditional rows:

```tsx
{summary.average_extraction_time_ms != null ? (
  <div className="metric-row">
    <span>Average extraction time</span>
    <strong className="tabular-metrics">
      {(summary.average_extraction_time_ms / 1000).toFixed(2)}s
    </strong>
  </div>
) : null}
```

Render numeric zero values normally. Continue to show the existing truthful
empty state when no batch exists. Add an assertion that `"N/A"` is absent when
nullable metrics are missing.

- [ ] **Step 6: Run context tests**

```powershell
npm test -- --run src/test/ActiveProfileSummary.test.tsx src/test/ProfileDocumentPanel.test.tsx src/test/BatchMetrics.test.tsx
npm run typecheck
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/job-agent-ui/src/components/workspace/ActiveProfileSummary.tsx frontend/job-agent-ui/src/components/profile frontend/job-agent-ui/src/components/BatchMetrics.tsx frontend/job-agent-ui/src/test/ActiveProfileSummary.test.tsx frontend/job-agent-ui/src/test/ProfileDocumentPanel.test.tsx frontend/job-agent-ui/src/test/BatchMetrics.test.tsx
git commit -m "feat: add API-backed workspace context rail"
```

---

### Task 5: Restructure chat history, messages, tools, and composer

**Files:**
- Create: `frontend/job-agent-ui/src/components/chat/ConversationToolbar.tsx`
- Create: `frontend/job-agent-ui/src/test/ConversationToolbar.test.tsx`
- Modify: `frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx`
- Modify: `frontend/job-agent-ui/src/components/chat/ChatMessageList.tsx`
- Modify: `frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx`
- Modify: `frontend/job-agent-ui/src/components/chat/ChatComposer.tsx`
- Modify: `frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/ToolCallTimeline.test.tsx`

- [ ] **Step 1: Write failing conversation toolbar tests**

```tsx
it("renders only persisted conversations and exposes icon commands", () => {
  render(
    <ConversationToolbar
      conversations={[existingConversation]}
      activeConversationId={existingConversation.id}
      disabled={false}
      onSelect={vi.fn()}
      onCreate={vi.fn()}
      onDelete={vi.fn()}
    />,
  );
  expect(screen.getByRole("option", { name: "Existing chat" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "New chat" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete current chat" })).toBeInTheDocument();
  expect(screen.queryByText("New session started")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run toolbar tests and verify RED**

```powershell
npm test -- --run src/test/ConversationToolbar.test.tsx
```

Expected: FAIL because `ConversationToolbar` does not exist.

- [ ] **Step 3: Implement `ConversationToolbar`**

Use a real conversation `<select>` and icon commands:

```tsx
interface ConversationToolbarProps {
  conversations: ChatConversation[];
  activeConversationId: string | null;
  disabled: boolean;
  onSelect: (conversation: ChatConversation) => void;
  onCreate: () => void;
  onDelete: (conversation: ChatConversation) => void;
}

export default function ConversationToolbar({
  conversations,
  activeConversationId,
  disabled,
  onSelect,
  onCreate,
  onDelete,
}: ConversationToolbarProps) {
  const activeConversation =
    conversations.find((item) => item.id === activeConversationId) ?? null;

  return (
<div className="conversation-toolbar">
  <select
    aria-label="Chat history"
    value={activeConversationId ?? ""}
    onChange={(event) => {
      const selected = conversations.find((item) => item.id === event.target.value);
      if (selected) onSelect(selected);
    }}
    disabled={disabled || conversations.length === 0}
  >
    {activeConversationId == null ? <option value="">Chat history</option> : null}
    {conversations.map((conversation) => (
      <option key={conversation.id} value={conversation.id}>
        {conversation.title || new Date(conversation.created_at).toLocaleString()}
      </option>
    ))}
  </select>
  <button type="button" aria-label="New chat" onClick={onCreate} disabled={disabled}>
    <Plus size={16} />
  </button>
  <button
    type="button"
    aria-label="Delete current chat"
    onClick={() => activeConversation && onDelete(activeConversation)}
    disabled={disabled || !activeConversation}
  >
    <Trash2 size={16} />
  </button>
</div>
  );
}
```

The `Chat history` option is a control label, not a domain record.

- [ ] **Step 4: Recompose `ChatWorkspacePage` without replacing logic**

Preserve all current refs, stale-request guards, tool-call refreshes, and
Review Queue navigation. Replace only the returned JSX and conversation button
list:

```tsx
return (
  <section className="chat-workspace">
    <ConversationToolbar
      conversations={conversations}
      activeConversationId={conversation?.conversation.id ?? null}
      disabled={!activeProfileId || isSending}
      onSelect={(selected) => void handleSelectConversation(selected)}
      onCreate={handleNewConversation}
      onDelete={(target) => void handleDeleteConversation(target)}
    />
    <div className="chat-transcript">
      <ChatMessageList messages={messages} />
      <ToolCallTimeline toolCalls={toolCalls} />
    </div>
    {error ? <div className="chat-error" role="alert">{error}</div> : null}
    <ChatComposer disabled={!activeProfileId || isSending} onSend={handleSend} />
  </section>
);
```

When creating a conversation, submit only real required context:

```tsx
createConversation({ role_profile_id: profileId })
```

Do not set the synthetic `"Job agent session"` title. Update existing tests to
expect the request without `title`.

- [ ] **Step 5: Restyle real messages and tool calls**

`ChatMessageList` must render an assistant or user Lucide icon, message content,
and actual timestamp:

```tsx
<time dateTime={message.created_at}>
  {new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(message.created_at))}
</time>
```

`ToolCallCard` must map persisted status to icons and CSS classes. It may render
only `tool_name`, `status`, `input_summary`, `result_summary`, and
`error_message`.

- [ ] **Step 6: Restyle the composer**

Keep the controlled empty value and no placeholder. Use a stable one-row
minimum height, an icon-only Send button with `aria-label`, and visible focus
styles. Do not add attachment or suggestion buttons because they are not
implemented.

- [ ] **Step 7: Run chat tests**

```powershell
npm test -- --run src/test/ConversationToolbar.test.tsx src/test/ChatWorkspacePage.test.tsx src/test/ToolCallTimeline.test.tsx src/test/chatClient.test.ts
npm run typecheck
```

Expected: PASS, including the existing tool-driven search and `/review`
navigation test.

- [ ] **Step 8: Commit non-overlapping files and review integrated chat diff**

```powershell
git diff -- frontend/job-agent-ui/src/pages/ChatWorkspacePage.tsx frontend/job-agent-ui/src/test/ChatWorkspacePage.test.tsx
git add frontend/job-agent-ui/src/components/chat/ConversationToolbar.tsx frontend/job-agent-ui/src/components/chat/ChatComposer.tsx frontend/job-agent-ui/src/components/chat/ChatMessageList.tsx frontend/job-agent-ui/src/components/chat/ToolCallCard.tsx frontend/job-agent-ui/src/test/ConversationToolbar.test.tsx frontend/job-agent-ui/src/test/ToolCallTimeline.test.tsx
git commit -m "feat: restructure agent chat workspace"
```

Defer `ChatWorkspacePage.tsx` and its test to the final integrated commit because
they contain the approved uncommitted search-tool flow.

---

### Task 6: Unify Review Queue and Tracked Jobs presentation

**Files:**
- Create: `frontend/job-agent-ui/src/components/PageState.tsx`
- Create: `frontend/job-agent-ui/src/test/PageState.test.tsx`
- Modify: `frontend/job-agent-ui/src/pages/ReviewPage.tsx`
- Modify: `frontend/job-agent-ui/src/pages/DashboardPage.tsx`
- Modify: `frontend/job-agent-ui/src/components/JobCard.tsx`
- Modify: `frontend/job-agent-ui/src/components/ScoreBreakdown.tsx`
- Modify: `frontend/job-agent-ui/src/components/StatusSelect.tsx`
- Modify: `frontend/job-agent-ui/src/test/ReviewPage.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/DashboardPage.test.tsx`
- Modify: `frontend/job-agent-ui/src/test/JobCard.test.tsx`

- [ ] **Step 1: Write failing shared-state and null-job tests**

Create `PageState.test.tsx`:

```tsx
it("renders the supplied empty message without adding domain values", () => {
  render(<PageState kind="empty">No tracked jobs found.</PageState>);
  expect(screen.getByText("No tracked jobs found.")).toBeInTheDocument();
  expect(screen.queryByText(/AI Engineer/i)).not.toBeInTheDocument();
});
```

Add to `JobCard.test.tsx`:

```tsx
it("omits absent job fields instead of rendering placeholder values", () => {
  render(<JobCard job={{ ...mockScorableJob, title: null, company: null, source_platform: null }} />);
  expect(screen.queryByText("Untitled Position")).not.toBeInTheDocument();
  expect(screen.queryByText("Unknown Company")).not.toBeInTheDocument();
  expect(screen.queryByText("Unknown")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
npm test -- --run src/test/PageState.test.tsx src/test/JobCard.test.tsx
```

Expected: FAIL because `PageState` does not exist and `JobCard` currently
renders synthetic fallback labels.

- [ ] **Step 3: Implement `PageState`**

```tsx
interface PageStateProps {
  kind: "loading" | "empty" | "error";
  children?: React.ReactNode;
}

export default function PageState({ kind, children }: PageStateProps) {
  return (
    <div className={`page-state page-state-${kind}`} role={kind === "error" ? "alert" : undefined}>
      {kind === "loading" ? <Loader2 aria-label="Loading" className="animate-spin" /> : null}
      {kind === "error" ? <AlertCircle aria-hidden="true" /> : null}
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Recompose both pages**

Use the same route structure:

```tsx
<section className="jobs-page">
  <header className="page-header">
    <h1>Review Queue</h1>
    <p>Evaluate matches, inspect scores, and approve or reject ingested jobs.</p>
  </header>
  {error ? <PageState kind="error">{error}</PageState> : null}
  {!activeProfileId ? (
    <PageState kind="empty">Select or create a role profile.</PageState>
  ) : isLoading ? (
    <PageState kind="loading" />
  ) : jobs.length === 0 ? (
    <PageState kind="empty">No jobs pending review.</PageState>
  ) : (
    <div className="job-list">
      {jobs.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          onApprove={handleApprove}
          onReject={handleReject}
          isActionLoading={actionLoading[job.id]}
        />
      ))}
    </div>
  )}
</section>
```

Use the same state ordering in `DashboardPage`, with heading `Tracked Jobs`,
description `Monitor saved jobs and application progress.`, empty text
`No tracked jobs found.`, and:

```tsx
<div className="job-list">
  {jobs.map((job) => (
    <JobCard
      key={job.id}
      job={job}
      onStatusChange={handleStatusChange}
    />
  ))}
</div>
```

Do not change fetch scope: Review remains profile-wide pending review; Dashboard
remains profile-wide tracked jobs.

- [ ] **Step 5: Remove synthetic job fallbacks**

Render title, company, source, JD status, location, and other metadata only when
the corresponding `Job` property exists. Keep `"Not scored"` because it is a
truthful computed state from `formatPercentScore`, not a fabricated score.

Use CSS classes instead of inline layout styles. Keep approve, reject, source
link, score breakdown, and status mutation behavior unchanged.

- [ ] **Step 6: Run page and card tests**

```powershell
npm test -- --run src/test/PageState.test.tsx src/test/ReviewPage.test.tsx src/test/DashboardPage.test.tsx src/test/JobCard.test.tsx src/test/StatusSelect.test.tsx
npm run typecheck
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add frontend/job-agent-ui/src/components/PageState.tsx frontend/job-agent-ui/src/components/JobCard.tsx frontend/job-agent-ui/src/components/ScoreBreakdown.tsx frontend/job-agent-ui/src/components/StatusSelect.tsx frontend/job-agent-ui/src/pages/ReviewPage.tsx frontend/job-agent-ui/src/pages/DashboardPage.tsx frontend/job-agent-ui/src/test/PageState.test.tsx frontend/job-agent-ui/src/test/ReviewPage.test.tsx frontend/job-agent-ui/src/test/DashboardPage.test.tsx frontend/job-agent-ui/src/test/JobCard.test.tsx
git commit -m "feat: unify job workflow views"
```

---

### Task 7: Complete responsive styling and accessibility

**Files:**
- Modify: `frontend/job-agent-ui/src/styles/app.css`
- Modify: `frontend/job-agent-ui/src/components/AppShell.tsx`
- Modify: `frontend/job-agent-ui/src/test/AppShell.test.tsx`

- [ ] **Step 1: Add a failing structure assertion**

Extend `AppShell.test.tsx`:

```tsx
expect(screen.getByRole("navigation", { name: "Workspace" })).toBeInTheDocument();
expect(screen.getByRole("main")).toBeInTheDocument();
expect(screen.getByRole("complementary", { name: "Profile and navigation" })).toBeInTheDocument();
expect(screen.getByRole("complementary", { name: "Workspace context" })).toBeInTheDocument();
```

- [ ] **Step 2: Run and verify RED**

```powershell
npm test -- --run src/test/AppShell.test.tsx
```

Expected: FAIL until the two asides have accessible labels and the landmark
structure is complete.

- [ ] **Step 3: Add responsive layout rules**

Append:

```css
@media (max-width: 1180px) {
  .workspace-shell {
    grid-template-columns: 220px minmax(0, 1fr);
    overflow: auto;
  }

  .workspace-context {
    grid-column: 2;
    border-left: 0;
    border-top: 1px solid var(--border-color);
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }
}

@media (max-width: 760px) {
  .workspace-shell { display: block; overflow: visible; }
  .workspace-sidebar,
  .workspace-main,
  .workspace-context { width: 100%; min-height: auto; overflow: visible; }
  .workspace-sidebar { border-right: 0; border-bottom: 1px solid var(--border-color); }
  .workspace-topbar { position: sticky; top: 0; z-index: 10; overflow-x: auto; }
  .workspace-tabs { min-width: max-content; }
  .workspace-route { padding: 16px; }
  .workspace-context { display: block; }
  .chat-transcript { min-height: 420px; }
  .job-card-header,
  .job-card-actions { align-items: stretch; flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 4: Enforce interaction and sizing rules**

Ensure:

- All icon buttons have a stable `32px` or `36px` square.
- Focus-visible uses a cyan outline.
- Hover glow appears only on interactive controls.
- Text uses `overflow-wrap: anywhere` where API values can be long.
- The composer and route headers do not overlap.
- No font size is computed from viewport width.
- No card radius exceeds `8px`.

Use:

```css
:where(button, a, input, select, textarea):focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.icon-command {
  width: 32px;
  height: 32px;
  display: inline-grid;
  place-items: center;
}

.btn-primary:hover:not(:disabled),
.icon-command:hover:not(:disabled) {
  box-shadow: 0 0 16px rgba(0, 231, 254, 0.28);
}
```

- [ ] **Step 5: Run all frontend tests, lint, and build**

```powershell
npm run typecheck
npm run lint
npm test -- --run
npm run build
```

Expected: all commands exit `0`. Record pre-existing lint warnings separately;
do not add new warnings.

- [ ] **Step 6: Commit stylesheet and accessibility adjustments**

```powershell
git add frontend/job-agent-ui/src/styles/app.css frontend/job-agent-ui/src/test/AppShell.test.tsx
git commit -m "style: complete responsive glacial workspace"
```

Defer the stylesheet if it contains pre-existing uncommitted tool-timeline
styles; include it in the final integrated commit after diff review.

---

### Task 8: Verify no sample data and integrate overlapping changes

**Files:**
- Review all modified frontend files
- Review pre-existing backend and frontend chat-search changes

- [ ] **Step 1: Scan runtime source for forbidden reference values**

Run:

```powershell
rg -n "07d78eef|CV_Harvard_like|LinkedIn|TopCV|New session started|AI Engineer OR Machine Learning|Ha Noi, Vietnam|PyTorch|Jobs Parsed[^\\n]*142|Scorable[^\\n]*38|User Workspace Avatar|Expand radius to HCMC" frontend/job-agent-ui/src frontend/job-agent-ui/index.html
```

Expected: no matches.

- [ ] **Step 2: Scan for placeholder attributes and synthetic fallbacks**

Run:

```powershell
rg -n "placeholder=|Untitled Position|Unknown Company|>Unknown<|\\|\\| ['\\\"]None['\\\"]|Job agent session" frontend/job-agent-ui/src
```

Expected: no runtime matches. Test fixtures may contain fake values because
test-only doubles are allowed, but runtime source must not.

- [ ] **Step 3: Review the complete integrated diff**

Run:

```powershell
git status --short
git diff --check
git diff -- frontend/job-agent-ui
git diff -- backend/app backend/tests
```

Confirm:

- Existing search-tool execution remains present.
- Existing tool result persistence remains present.
- Existing Review Queue navigation remains present.
- No backend file was changed by the UI redesign.
- No user change was reverted.

- [ ] **Step 4: Run complete verification**

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
```

Frontend:

```powershell
cd frontend/job-agent-ui
npm run typecheck
npm run lint
npm test -- --run
npm run build
```

Expected: backend tests pass, compileall exits `0`, frontend tests pass,
typecheck exits `0`, lint adds no warnings, and the production build succeeds.

- [ ] **Step 5: Start the real local stack**

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend/job-agent-ui
npm run dev -- --host 127.0.0.1 --port 5173
```

Probe `http://127.0.0.1:8000/openapi.json` and
`http://127.0.0.1:5173/`; both must return HTTP `200`.

- [ ] **Step 6: Perform visual verification**

Use the in-app browser at:

- Desktop: `1440x900`
- Tablet: `1024x768`
- Mobile: `390x844`

Verify each route with real local data:

- `/`
- `/review`
- `/dashboard`

Confirm no overlap, clipping, blank panels, inaccessible controls, copied
reference values, or fake metrics. Confirm Chat can select/delete a persisted
conversation and a search tool result still navigates to Review Queue.

- [ ] **Step 7: Create the final integrated commit**

Stage only reviewed project files:

```powershell
git add frontend/job-agent-ui backend/app/api/routes_chat.py backend/app/api/routes_jobs.py backend/app/services/agent_event_service.py backend/app/services/tool_registry.py backend/app/services/job_search_workflow.py backend/tests/test_agent_event_service.py backend/tests/test_routes_chat.py backend/tests/test_routes_jobs.py backend/tests/test_tool_registry.py
git commit -m "feat: deliver agent workspace UI"
```

Do not stage unrelated files.
