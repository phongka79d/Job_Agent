import React, { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, Check, X, MapPin, Building, ExternalLink, Briefcase } from "lucide-react";
import type { Job } from "../types/api";
import ScoreBreakdown, { formatPercentScore } from "./ScoreBreakdown";
import StatusSelect from "./StatusSelect";

interface JobCardProps {
  job: Job;
  onApprove?: (id: string) => void | Promise<void>;
  onReject?: (id: string) => void | Promise<void>;
  statusControl?: React.ReactNode;
  onStatusChange?: () => void;
  isActionLoading?: boolean;
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
    </div>
  );
}
