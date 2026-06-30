export default function DashboardPage() {
  return (
    <div className="dashboard-page">
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Tracked Jobs Dashboard</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Monitor your saved, applied, and active job applications.
        </p>
      </div>
      
      <div className="glass-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
        No tracked jobs found. Create or select a role profile and ingest jobs to populate the dashboard.
      </div>
    </div>
  );
}
