import { useEffect, useState, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import { createCvDraft } from "../api/profileDocumentsClient";
import { generateJobCvImprovements, getReviewJobs, approveJob, rejectJob } from "../api/client";
import type { GenerateJobCvImprovementsResponse, Job } from "../types/api";
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
  const [cvImprovementByJob, setCvImprovementByJob] = useState<Record<string, GenerateJobCvImprovementsResponse>>({});

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

  const handleGenerateCvImprovements = async (jobId: string) => {
    if (!activeProfileId) return;
    setActionLoading((prev) => ({ ...prev, [`cv-${jobId}`]: true }));
    setError(null);
    try {
      const result = await generateJobCvImprovements(jobId, {
        role_profile_id: activeProfileId,
        max_suggestions: 6,
      });
      setCvImprovementByJob((prev) => ({ ...prev, [jobId]: result }));
    } catch (err: any) {
      setError(err.message || "Failed to generate CV improvements.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`cv-${jobId}`]: false }));
    }
  };

  const handleCreateCvDraft = async (jobId: string) => {
    const improvement = cvImprovementByJob[jobId];
    if (!improvement) return;
    const wordingOnlySuggestionIds = improvement.suggestions
      .filter((suggestion) => suggestion.edit_kind === "wording_only")
      .map((suggestion) => suggestion.id);
    if (wordingOnlySuggestionIds.length === 0) {
      setError("No wording-only CV suggestions are available for drafting.");
      return;
    }
    const confirmed = window.confirm("Create a CV draft from wording-only suggestions? The original PDF will not change.");
    if (!confirmed) return;
    setActionLoading((prev) => ({ ...prev, [`draft-${jobId}`]: true }));
    setError(null);
    try {
      await createCvDraft(improvement.role_profile_id, improvement.document_id, improvement.version_id, {
        title: `CV draft for ${jobs.find((job) => job.id === jobId)?.title || "job"}`,
        suggestion_ids: wordingOnlySuggestionIds,
        confirmed: true,
      });
    } catch (err: any) {
      setError(err.message || "Failed to create CV draft.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`draft-${jobId}`]: false }));
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
              cvImprovementResult={cvImprovementByJob[job.id]}
              onGenerateCvImprovements={handleGenerateCvImprovements}
              onCreateCvDraft={handleCreateCvDraft}
              isCvImprovementLoading={Boolean(actionLoading[`cv-${job.id}`])}
            />
          ))}
        </div>
      )}
    </section>
  );
}
