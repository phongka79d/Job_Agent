import { NavLink, Outlet } from 'react-router-dom';
import { Briefcase, ClipboardList, Layers } from 'lucide-react';

interface AppShellProps {
  sidebarContent?: React.ReactNode;
  activeBatchId?: string | null;
  activeProfileId?: string | null;
}

export default function AppShell({ sidebarContent, activeBatchId, activeProfileId }: AppShellProps) {
  return (
    <div className="app-container">
      {/* Sidebar for role profile selection/creation and ingestion controls */}
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
          <Briefcase size={20} color="var(--accent)" />
          <h1 style={{ fontSize: '18px', fontWeight: 700, margin: 0, letterSpacing: '-0.025em' }}>Job Agent MVP</h1>
        </div>
        
        {sidebarContent ? (
          sidebarContent
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flexGrow: 1 }}>
            {/* Placeholders for profile selection/creation and ingestion panels */}
            <div className="glass-panel" style={{ padding: '16px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                Role Profile
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                Placeholder: Profile Selection UI (Implemented in 02B)
              </div>
            </div>
            
            <div className="glass-panel" style={{ padding: '16px', flexGrow: 1 }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                Ingestion Controls
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                Placeholder: Job Ingestion UI (Implemented in 02C)
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main application workspace */}
      <main className="main-content">
        <header className="top-nav">
          <nav className="top-nav-tabs">
            <NavLink
              to="/"
              end
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
          <Outlet context={{ activeProfileId, activeBatchId }} />
        </section>
      </main>
    </div>
  );
}
