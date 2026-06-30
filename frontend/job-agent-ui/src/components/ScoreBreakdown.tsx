import React from "react";
import type { Job } from "../types/api";

interface ScoreBreakdownProps {
  job: Job;
}

export const formatDecimalScore = (val: number | null | undefined, shouldScore: boolean): string => {
  if (!shouldScore || val === null || val === undefined) return "Not scored";
  return `${Math.round(val * 100)}%`;
};

export const formatPercentScore = (val: number | null | undefined, shouldScore: boolean): string => {
  if (!shouldScore || val === null || val === undefined) return "Not scored";
  return `${Math.round(val)}%`;
};

export default function ScoreBreakdown({ job }: ScoreBreakdownProps) {
  const shouldScore = job.should_score_similarity && job.final_score !== null && job.final_score_percent !== null;
  
  const factors = [
    { label: "Semantic Similarity", value: formatDecimalScore(job.embedding_similarity, shouldScore) },
    { label: "Skill Overlap", value: formatDecimalScore(job.skill_overlap_score, shouldScore) },
    { label: "Location Match", value: formatDecimalScore(job.location_match_score, shouldScore) },
    { label: "Level Match", value: formatDecimalScore(job.level_match_score, shouldScore) },
    { label: "JD Confidence", value: formatDecimalScore(job.jd_confidence_multiplier, shouldScore) },
    { label: "Final Score", value: formatDecimalScore(job.final_score, shouldScore), isBold: true },
  ];

  return (
    <div 
      className="score-breakdown-container" 
      style={{ 
        padding: "16px", 
        marginTop: "12px", 
        borderTop: "1px solid var(--border-color)",
        backgroundColor: "rgba(0, 0, 0, 0.2)",
        borderRadius: "0 0 var(--radius-md) var(--radius-md)"
      }}
    >
      <div 
        style={{ 
          display: "grid", 
          gridTemplateColumns: "1fr auto", 
          rowGap: "10px", 
          columnGap: "24px",
          fontSize: "14px" 
        }}
      >
        {factors.map((factor) => (
          <React.Fragment key={factor.label}>
            <span 
              style={{ 
                color: factor.isBold ? "var(--text-primary)" : "var(--text-secondary)", 
                fontWeight: factor.isBold ? "600" : "normal" 
              }}
            >
              {factor.label}
            </span>
            <span 
              className="tabular-metrics" 
              style={{ 
                color: factor.value === "Not scored" 
                  ? "var(--text-muted)" 
                  : (factor.isBold ? "var(--accent)" : "var(--text-primary)"),
                fontWeight: factor.isBold ? "600" : "normal" 
              }}
            >
              {factor.value}
            </span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
