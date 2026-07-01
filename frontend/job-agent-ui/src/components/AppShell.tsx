import { NavLink, Outlet } from 'react-router-dom';
import { Briefcase, ClipboardList, Layers, MessageSquare } from 'lucide-react';

interface AppShellProps {
  sidebarContent: React.ReactNode;
  activeBatchId?: string | null;
  activeProfileId?: string | null;
  triggerMetricsRefresh?: () => void;
}

export default function AppShell({ sidebarContent, activeBatchId, activeProfileId, triggerMetricsRefresh }: AppShellProps) {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
          <Briefcase size={20} color="var(--accent)" />
          <h1 style={{ fontSize: '18px', fontWeight: 700, margin: 0, letterSpacing: '-0.025em' }}>Job Agent MVP</h1>
        </div>
        
        {sidebarContent}
      </aside>

      <main className="main-content">
        <header className="top-nav">
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
              Tracked Jobs Dashboard
            </NavLink>
          </nav>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
            Active Batch ID: <span className="tabular-metrics" style={{ color: activeBatchId ? 'var(--accent)' : 'var(--text-secondary)' }}>{activeBatchId || 'None'}</span>
          </div>
        </header>
        
        <section className="content-viewport">
          <Outlet context={{ activeProfileId, activeBatchId, triggerMetricsRefresh }} />
        </section>
      </main>
    </div>
  );
}
