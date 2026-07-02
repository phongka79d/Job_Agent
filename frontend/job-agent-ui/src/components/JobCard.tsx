import React, { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, Check, X, MapPin, Building, ExternalLink, Briefcase } from "lucide-react";
import type { GenerateJobCvImprovementsResponse, Job } from "../types/api";
import type { CvDraft, CvDraftPreview } from "../types/profileDocuments";
import ScoreBreakdown, { formatPercentScore } from "./ScoreBreakdown";
import StatusSelect from "./StatusSelect";

interface JobCardProps {
  job: Job;
  onApprove?: (id: string) => void | Promise<void>;
  onReject?: (id: string) => void | Promise<void>;
  statusControl?: React.ReactNode;
  onStatusChange?: () => void;
  isActionLoading?: boolean;
  cvImprovementResult?: GenerateJobCvImprovementsResponse;
  cvDraft?: CvDraft;
  cvDraftPreview?: CvDraftPreview;
  onGenerateCvImprovements?: (id: string) => void | Promise<void>;
  onCreateCvDraft?: (id: string) => void | Promise<void>;
  onPreviewCvDraft?: (id: string) => void | Promise<void>;
  isCvImprovementLoading?: boolean;
  isCvDraftLoading?: boolean;
}

function formatSource(src: string | null): string | null {
  if (!src) return null;
  return src.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatJdStatus(status: string | null): string | null {
  if (!status) return null;
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatJobStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function JobCard({
  job,
  onApprove,
  onReject,
  statusControl,
  onStatusChange,
  isActionLoading = false,
  cvImprovementResult,
  cvDraft,
  cvDraftPreview,
  onGenerateCvImprovements,
  onCreateCvDraft,
  onPreviewCvDraft,
  isCvImprovementLoading = false,
  isCvDraftLoading = false,
}: JobCardProps) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  const shouldScore = job.should_score_similarity && job.final_score !== null && job.final_score_percent !== null;
  const formattedFinalScore = formatPercentScore(job.final_score_percent, shouldScore);

  return (
    <div className="job-card">
      <div className="job-card-main">
        <div className="job-card-header">
          <div className="job-card-title-group">
            {job.title ? <h3>{job.title}</h3> : null}
            {job.company ? (
              <div className="job-card-company">
                <Building size={14} />
                <span>{job.company}</span>
              </div>
            ) : null}
          </div>
          <div className="job-card-score">
            <div className={`score-badge${formattedFinalScore === "Not scored" ? " not-scored" : ""}`}>
              {formattedFinalScore}
            </div>
            <div className="score-label">Match Score</div>
          </div>
        </div>

        <div className="job-card-meta">
          {job.location ? (
            <span>
              <MapPin size={13} /> {job.location}
            </span>
          ) : null}
          {job.work_mode ? (
            <span>
              <Briefcase size={13} /> {job.work_mode}
            </span>
          ) : null}
        </div>

        {job.error_reason && (
          <div className="job-card-error">
            <AlertTriangle size={16} />
            <span>{job.error_reason}</span>
          </div>
        )}

        <div className="job-card-badges">
          {formatSource(job.source_platform) ? (
            <span className="badge">Source: {formatSource(job.source_platform)}</span>
          ) : null}
          {formatJdStatus(job.jd_status) ? (
            <span className={`badge${job.jd_status === "full_jd" ? " badge-success" : ""}`}>
              JD: {formatJdStatus(job.jd_status)}
            </span>
          ) : null}
          <span className={`badge${job.status === "pending_review" ? " badge-accent" : ""}`}>
            Status: {formatJobStatus(job.status)}
          </span>
        </div>

        <div className="job-card-actions">
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="btn-secondary"
          >
            <span>Breakdown</span>
            {showBreakdown ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {onGenerateCvImprovements ? (
            <button
              type="button"
              onClick={() => onGenerateCvImprovements(job.id)}
              disabled={isCvImprovementLoading}
              className="btn-secondary"
            >
              <span>{isCvImprovementLoading ? "Generating..." : "Improve CV"}</span>
            </button>
          ) : null}

          {job.source_url && (
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-link"
            >
              <span>View JD</span>
              <ExternalLink size={13} />
            </a>
          )}

          <div className="job-card-action-buttons">
            {job.status === "pending_review" && onApprove && onReject && (
              <>
                <button
                  onClick={() => onReject(job.id)}
                  disabled={isActionLoading}
                  className="btn-secondary btn-danger"
                >
                  <X size={14} />
                  <span>Reject</span>
                </button>
                <button
                  onClick={() => onApprove(job.id)}
                  disabled={isActionLoading}
                  className="btn-secondary btn-success"
                >
                  <Check size={14} />
                  <span>Approve</span>
                </button>
              </>
            )}
            {statusControl || (job.status !== "pending_review" && job.status !== "ignored" && (
              <StatusSelect
                jobId={job.id}
                currentStatus={job.status}
                onStatusChangeSuccess={onStatusChange}
              />
            ))}
          </div>
        </div>
      </div>

      {showBreakdown && <ScoreBreakdown job={job} />}

      {cvImprovementResult ? (
        <div className="job-cv-suggestions">
          <div className="job-cv-suggestions-header">
            <strong>CV improvement suggestions</strong>
            {cvImprovementResult.suggestions.some((suggestion) => suggestion.edit_kind === "wording_only") &&
            onCreateCvDraft &&
            !cvDraft ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => onCreateCvDraft(job.id)}
                disabled={isCvDraftLoading}
              >
                {isCvDraftLoading ? "Creating draft..." : "Create CV draft"}
              </button>
            ) : null}
          </div>
          {cvImprovementResult.suggestions.map((suggestion) => (
            <article key={suggestion.id} className="job-cv-suggestion">
              <div>
                <strong>{suggestion.requirement}</strong>
                <span>{suggestion.proposed_edit}</span>
              </div>
              <small>
                {suggestion.edit_kind === "requires_user_fact" ? "Requires user facts" : "Wording only"} - {suggestion.risk_level}
              </small>
            </article>
          ))}
          {cvDraft ? (
            <div className="job-cv-draft">
              <div className="job-cv-draft-header">
                <div>
                  <strong>CV draft created</strong>
                  <span>{cvDraft.title}</span>
                </div>
                {onPreviewCvDraft ? (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => onPreviewCvDraft(job.id)}
                    disabled={isCvDraftLoading}
                  >
                    Preview draft
                  </button>
                ) : null}
              </div>
              {cvDraftPreview ? (
                <div className="job-cv-draft-preview">
                  {cvDraftPreview.recommendation ? <p>{cvDraftPreview.recommendation}</p> : null}
                  {cvDraftPreview.edits.map((edit) => (
                    <article key={`${cvDraftPreview.draft_id}-${edit.requirement}`}>
                      <strong>{edit.requirement}</strong>
                      <span>{edit.proposed_edit}</span>
                    </article>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
