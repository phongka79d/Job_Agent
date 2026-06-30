export default function ReviewPage() {
  return (
    <div className="review-page">
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Review Queue</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Evaluate matches, inspect scores, and approve or reject ingested jobs.
        </p>
      </div>
      
      <div className="glass-panel" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
        No jobs pending review. Create or select a role profile and ingest jobs to start evaluating.
      </div>
    </div>
  );
}
