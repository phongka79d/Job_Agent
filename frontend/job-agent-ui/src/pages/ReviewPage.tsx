import { useEffect, useState, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { AlertCircle, Loader } from "lucide-react";
import { getReviewJobs, approveJob, rejectJob } from "../api/client";
import type { Job } from "../types/api";
import JobCard from "../components/JobCard";

export default function ReviewPage() {
  const { activeProfileId, activeBatchId, triggerMetricsRefresh } = useOutletContext<{
    activeProfileId: string | null;
    activeBatchId: string | null;
    triggerMetricsRefresh?: () => void;
  }>();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  const fetchJobs = useCallback(async () => {
    if (!activeProfileId) {
      setJobs([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await getReviewJobs(activeProfileId);
      setJobs(response.jobs || []);
    } catch (err: any) {
      setError(err.message || "Failed to fetch review jobs.");
    } finally {
      setIsLoading(false);
    }
  }, [activeProfileId]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleApprove = async (jobId: string) => {
    setActionLoading((prev) => ({ ...prev, [jobId]: true }));
    setError(null);
    try {
      await approveJob(jobId);
      await fetchJobs();
      if (activeBatchId) {
        triggerMetricsRefresh?.();
      }
    } catch (err: any) {
      setError(err.message || "Failed to approve job.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [jobId]: false }));
    }
  };

  const handleReject = async (jobId: string) => {
    setActionLoading((prev) => ({ ...prev, [jobId]: true }));
    setError(null);
    try {
      await rejectJob(jobId);
      await fetchJobs();
      if (activeBatchId) {
        triggerMetricsRefresh?.();
      }
    } catch (err: any) {
      setError(err.message || "Failed to reject job.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [jobId]: false }));
    }
  };

  return (
    <div className="review-page" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div style={{ marginBottom: "8px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 600, color: "var(--text-primary)" }}>Review Queue</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "14px", marginTop: "4px" }}>
          Evaluate matches, inspect scores, and approve or reject ingested jobs.
        </p>
      </div>

      {error && (
        <div
          className="glass-panel"
          style={{
            padding: "16px",
            borderColor: "rgba(248, 113, 113, 0.3)",
            backgroundColor: "rgba(248, 113, 113, 0.05)",
            color: "var(--text-danger)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "14px",
          }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {!activeProfileId ? (
        <div
          className="glass-panel"
          style={{
            padding: "32px",
            textAlign: "center",
            color: "var(--text-muted)",
            fontSize: "14px",
          }}
      >
        Please select or create a role profile to view pending review jobs.
      </div>
      ) : isLoading ? (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: "64px",
            color: "var(--accent)",
          }}
        >
          <Loader className="animate-spin" size={32} />
        </div>
      ) : jobs.length === 0 ? (
        <div
          className="glass-panel"
          style={{
            padding: "32px",
            textAlign: "center",
            color: "var(--text-muted)",
            fontSize: "14px",
          }}
        >
          No jobs pending review.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
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
    </div>
  );
}
