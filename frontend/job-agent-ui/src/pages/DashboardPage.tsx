import { useEffect, useState, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { getJobs } from "../api/client";
import type { Job } from "../types/api";
import JobCard from "../components/JobCard";
import PageState from "../components/PageState";

export default function DashboardPage() {
  const { activeProfileId, activeBatchId, triggerMetricsRefresh } = useOutletContext<{
    activeProfileId: string | null;
    activeBatchId: string | null;
    triggerMetricsRefresh?: () => void;
  }>();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    if (!activeProfileId) {
      setJobs([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await getJobs(activeProfileId, "tracked");
      setJobs(response.jobs || []);
    } catch (err: any) {
      setError(err.message || "Failed to fetch tracked jobs.");
    } finally {
      setIsLoading(false);
    }
  }, [activeProfileId]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleStatusChange = useCallback(() => {
    fetchJobs();
    if (activeBatchId) {
      triggerMetricsRefresh?.();
    }
  }, [activeBatchId, fetchJobs, triggerMetricsRefresh]);

  return (
    <section className="jobs-page">
      <header className="page-header">
        <h1>Tracked Jobs</h1>
        <p>Monitor saved jobs and application progress.</p>
      </header>
      {error ? <PageState kind="error">{error}</PageState> : null}
      {!activeProfileId ? (
        <PageState kind="empty">Select or create a role profile.</PageState>
      ) : isLoading ? (
        <PageState kind="loading" />
      ) : jobs.length === 0 ? (
        <PageState kind="empty">No tracked jobs found.</PageState>
      ) : (
        <div className="job-list">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </section>
  );
}
