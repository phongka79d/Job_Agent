import React, { useState, useEffect } from "react";
import { updateJobStatus } from "../api/client";
import { ALLOWED_STATUS_TRANSITIONS } from "../types/api";
import type { JobStatus } from "../types/api";
import { AlertCircle } from "lucide-react";

interface StatusSelectProps {
  jobId: string;
  currentStatus: JobStatus;
  onStatusChangeSuccess?: () => void;
}

export default function StatusSelect({
  jobId,
  currentStatus,
  onStatusChangeSuccess,
}: StatusSelectProps) {
  const [status, setStatus] = useState<JobStatus>(currentStatus);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync status if currentStatus prop changes from outside
  useEffect(() => {
    setStatus(currentStatus);
  }, [currentStatus]);

  const targets = ALLOWED_STATUS_TRANSITIONS[currentStatus] || [];
  const isTerminal = targets.length === 0;

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as JobStatus;
    if (newStatus === status) return;

    setIsUpdating(true);
    setError(null);

    try {
      await updateJobStatus(jobId, { status: newStatus as any });
      setStatus(newStatus);
      if (onStatusChangeSuccess) {
        onStatusChangeSuccess();
      }
    } catch (err: any) {
      setError(err.message || "Failed to update status.");
      // Revert status to current (which is still the prop or previous status)
      setStatus(currentStatus);
      // Automatically clear error after some seconds to keep UI clean
      setTimeout(() => setError(null), 5000);
    } finally {
      setIsUpdating(false);
    }
  };

  const formatLabel = (val: string) => {
    return val.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  // Color mappings for badge indicators based on currentStatus
  const getBadgeColors = (s: JobStatus) => {
    switch (s) {
      case "saved":
        return { bg: "rgba(255, 255, 255, 0.05)", text: "var(--text-secondary)", border: "var(--border-color)" };
      case "applied":
        return { bg: "rgba(34, 211, 238, 0.15)", text: "var(--accent)", border: "rgba(34, 211, 238, 0.3)" };
      case "interview":
        return { bg: "rgba(234, 179, 8, 0.15)", text: "#fde047", border: "rgba(234, 179, 8, 0.3)" };
      case "offer":
        return { bg: "rgba(74, 222, 128, 0.15)", text: "var(--text-success)", border: "rgba(74, 222, 128, 0.3)" };
      case "rejected":
        return { bg: "rgba(248, 113, 113, 0.15)", text: "var(--text-danger)", border: "rgba(248, 113, 113, 0.3)" };
      case "ignored":
        return { bg: "rgba(148, 163, 184, 0.1)", text: "var(--text-muted)", border: "var(--border-color)" };
      default:
        return { bg: "rgba(255, 255, 255, 0.05)", text: "var(--text-muted)", border: "var(--border-color)" };
    }
  };

  const colors = getBadgeColors(status);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px", alignItems: "flex-end", position: "relative" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {isUpdating && (
          <span 
            data-testid="status-loader"
            style={{ 
              fontSize: "12px", 
              color: "var(--accent)", 
              animation: "spin 1s linear infinite",
              display: "inline-block",
              width: "12px",
              height: "12px",
              border: "2px solid var(--accent)",
              borderTopColor: "transparent",
              borderRadius: "50%"
            }} 
          />
        )}
        
        <select
          data-testid="status-select"
          value={status}
          onChange={handleChange}
          disabled={isUpdating || isTerminal}
          style={{
            backgroundColor: colors.bg,
            color: colors.text,
            border: `1px solid ${colors.border}`,
            borderRadius: "var(--radius-md)",
            padding: "4px 8px",
            fontSize: "13px",
            fontWeight: "500",
            cursor: isTerminal ? "not-allowed" : "pointer",
            outline: "none",
            transition: "all 0.2s ease",
            WebkitAppearance: "none",
            MozAppearance: "none",
            appearance: "none",
            paddingRight: isTerminal ? "8px" : "24px",
            backgroundImage: isTerminal 
              ? "none" 
              : "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.5)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>\")",
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 4px center",
            backgroundSize: "16px"
          }}
        >
          {/* Always render current status option */}
          <option value={status} style={{ background: "#0f172a", color: "var(--text-primary)" }}>
            {formatLabel(status)}
          </option>
          
          {/* Render allowed transition targets */}
          {targets.map((tgt) => (
            <option key={tgt} value={tgt} style={{ background: "#0f172a", color: "var(--text-primary)" }}>
              {formatLabel(tgt)}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div 
          data-testid="status-error"
          style={{ 
            color: "var(--text-danger)", 
            fontSize: "11px", 
            display: "flex", 
            alignItems: "center", 
            gap: "4px",
            position: "absolute",
            top: "100%",
            right: 0,
            whiteSpace: "nowrap",
            backgroundColor: "rgba(15, 23, 42, 0.9)",
            padding: "4px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid rgba(248, 113, 113, 0.2)",
            zIndex: 10,
            marginTop: "2px"
          }}
        >
          <AlertCircle size={12} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
