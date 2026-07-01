import { useEffect, useState, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { getReviewJobs, approveJob, rejectJob } from "../api/client";
import type { Job } from "../types/api";
import JobCard from "../components/JobCard";
import PageState from "../components/PageState";

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
  );
}
