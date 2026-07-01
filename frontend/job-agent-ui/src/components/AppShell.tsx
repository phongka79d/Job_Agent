import { NavLink, Outlet } from 'react-router-dom';
import { Briefcase, ClipboardList, Layers, MessageSquare } from 'lucide-react';

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
    <div className="app-container">
      <aside className="workspace-sidebar">
        {sidebarContent}
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div className="workspace-brand">
            <Briefcase size={20} color="var(--accent)" />
            <span>Agent Workspace</span>
          </div>
          <nav className="top-nav-tabs">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}
            >
              <MessageSquare size={16} />
              Agent Chat
            </NavLink>
            <NavLink
              to="/review"
              className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}
            >
              <ClipboardList size={16} />
              Review Queue
            </NavLink>
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}
            >
              <Layers size={16} />
              Tracked Jobs
            </NavLink>
          </nav>

          {activeBatchId && (
            <div className="active-batch-badge">
              <span>Active batch</span>
              <strong className="tabular-metrics">{activeBatchId}</strong>
            </div>
          )}
        </header>

        <section className="workspace-route">
          <Outlet context={{ activeProfileId, activeBatchId, triggerMetricsRefresh }} />
        </section>
      </main>

      <aside className="workspace-context">
        {contextContent}
      </aside>
    </div>
  );
}
