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

  // Formatting helpers for metadata display
  const formatSource = (src: string | null) => {
    if (!src) return "Unknown";
    return src.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const formatJdStatus = (status: string | null) => {
    if (!status) return "Unknown";
    return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const formatJobStatus = (status: string) => {
    return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div 
      className="glass-panel job-card" 
      style={{ 
        display: "flex", 
        flexDirection: "column", 
        width: "100%", 
        textAlign: "left",
        overflow: "hidden",
        position: "relative",
        background: "var(--bg-surface)",
        backdropFilter: "blur(12px)",
        border: "1px solid var(--border-color)",
        borderRadius: "var(--radius-lg)"
      }}
    >
      {/* Top Main Section */}
      <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px", flexGrow: 1 }}>
        
        {/* Title, Company, and Score Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "600", color: "var(--text-primary)", margin: 0 }}>
              {job.title || "Untitled Position"}
            </h3>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--text-secondary)", fontSize: "14px" }}>
              <Building size={14} style={{ color: "var(--text-muted)" }} />
              <span>{job.company || "Unknown Company"}</span>
            </div>
          </div>
          
          {/* Score Badge */}
          <div 
            style={{ 
              display: "flex", 
              flexDirection: "column", 
              alignItems: "flex-end",
              flexShrink: 0
            }}
          >
            <div 
              style={{ 
                fontSize: "20px", 
                fontWeight: "700", 
                color: formattedFinalScore === "Not scored" ? "var(--text-muted)" : "var(--accent)",
                fontFamily: "var(--font-mono)",
                letterSpacing: "-0.5px"
              }}
            >
              {formattedFinalScore}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Match Score
            </div>
          </div>
        </div>

        {/* Location and Work Mode Info */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", fontSize: "13px", color: "var(--text-secondary)" }}>
          {job.location && (
            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <MapPin size={13} style={{ color: "var(--text-muted)" }} />
              <span>{job.location}</span>
            </div>
          )}
          {job.work_mode && (
            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <Briefcase size={13} style={{ color: "var(--text-muted)" }} />
              <span>{job.work_mode}</span>
            </div>
          )}
        </div>

        {/* Persisted Job Error / Processing Warnings */}
        {job.error_reason && (
          <div 
            style={{ 
              display: "flex", 
              gap: "8px", 
              padding: "10px 12px", 
              backgroundColor: "rgba(248, 113, 113, 0.1)", 
              border: "1px solid rgba(248, 113, 113, 0.2)", 
              borderRadius: "var(--radius-md)",
              color: "var(--text-danger)",
              fontSize: "13px",
              lineHeight: "1.4"
            }}
          >
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: "1px" }} />
            <span>{job.error_reason}</span>
          </div>
        )}

        {/* Meta Badges Grid */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "4px" }}>
          {/* Source Platform */}
          <span 
            style={{ 
              fontSize: "12px", 
              padding: "3px 8px", 
              borderRadius: "var(--radius-sm)", 
              backgroundColor: "rgba(255, 255, 255, 0.04)", 
              color: "var(--text-muted)",
              border: "1px solid var(--border-color)"
            }}
          >
            Source: {formatSource(job.source_platform)}
          </span>

          {/* JD Status */}
          <span 
            style={{ 
              fontSize: "12px", 
              padding: "3px 8px", 
              borderRadius: "var(--radius-sm)", 
              backgroundColor: "rgba(255, 255, 255, 0.04)", 
              color: job.jd_status === "full_jd" ? "var(--text-success)" : "var(--text-muted)",
              border: "1px solid var(--border-color)"
            }}
          >
            JD: {formatJdStatus(job.jd_status)}
          </span>

          {/* Current Status */}
          <span 
            style={{ 
              fontSize: "12px", 
              padding: "3px 8px", 
              borderRadius: "var(--radius-sm)", 
              backgroundColor: job.status === "pending_review" ? "rgba(34, 211, 238, 0.1)" : "rgba(255, 255, 255, 0.04)", 
              color: job.status === "pending_review" ? "var(--accent)" : "var(--text-secondary)",
              border: job.status === "pending_review" ? "1px solid rgba(34, 211, 238, 0.3)" : "1px solid var(--border-color)"
            }}
          >
            Status: {formatJobStatus(job.status)}
          </span>
        </div>

        {/* Action Panel */}
        <div 
          style={{ 
            display: "flex", 
            justifyContent: "space-between", 
            alignItems: "center", 
            gap: "16px",
            marginTop: "12px",
            paddingTop: "12px",
            borderTop: "1px solid var(--border-color)"
          }}
        >
          {/* In-card Accordion Toggle for Score Breakdown */}
          <button
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="btn-secondary"
            style={{ 
              fontSize: "13px", 
              padding: "6px 12px", 
              display: "flex", 
              alignItems: "center", 
              gap: "4px" 
            }}
          >
            <span>Breakdown</span>
            {showBreakdown ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {/* Ingestion & Link Icon */}
          {job.source_url && (
            <a 
              href={job.source_url} 
              target="_blank" 
              rel="noopener noreferrer"
              style={{ 
                color: "var(--text-muted)", 
                display: "inline-flex", 
                alignItems: "center", 
                gap: "4px",
                textDecoration: "none",
                fontSize: "13px"
              }}
              hover-color="var(--text-primary)"
            >
              <span>View JD</span>
              <ExternalLink size={13} />
            </a>
          )}

          {/* Workflow specific actions */}
          <div style={{ display: "flex", gap: "8px", marginLeft: "auto", alignItems: "center" }}>
            
            {/* Approve / Reject buttons for Review queue */}
            {job.status === "pending_review" && onApprove && onReject && (
              <>
                <button
                  onClick={() => onReject(job.id)}
                  disabled={isActionLoading}
                  className="btn-secondary"
                  style={{ 
                    color: "var(--text-danger)", 
                    borderColor: "rgba(248, 113, 113, 0.3)",
                    padding: "6px 12px",
                    fontSize: "13px"
                  }}
                >
                  <X size={14} />
                  <span>Reject</span>
                </button>
                
                <button
                  onClick={() => onApprove(job.id)}
                  disabled={isActionLoading}
                  className="btn-secondary"
                  style={{ 
                    color: "var(--text-success)", 
                    borderColor: "rgba(74, 222, 128, 0.3)",
                    padding: "6px 12px",
                    fontSize: "13px"
                  }}
                >
                  <Check size={14} />
                  <span>Approve</span>
                </button>
              </>
            )}

            {/* Manual Status Select for Dashboard page */}
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

      {/* Accordion content - Score Breakdown */}
      {showBreakdown && <ScoreBreakdown job={job} />}
    </div>
  );
}
