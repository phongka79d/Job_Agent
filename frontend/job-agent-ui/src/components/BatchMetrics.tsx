import { useEffect, useState, useCallback } from "react";
import { getBatchSummary } from "../api/client";
import { loadActiveBatchId, clearActiveBatchId } from "../utils/activeBatchStorage";
import type { BatchSummary } from "../types/api";
import { AlertCircle, Loader, BarChart2 } from "lucide-react";

interface BatchMetricsProps {
  activeProfileId: string | null;
  activeBatchId: string | null;
  refreshTrigger: number;
}

export default function BatchMetrics({ activeProfileId, activeBatchId, refreshTrigger }: BatchMetricsProps) {
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    if (!activeProfileId || !activeBatchId) {
      setSummary(null);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await getBatchSummary(activeBatchId);
      setSummary(data);
    } catch (err: any) {
      if (err.status === 404) {
        // If the summary endpoint returns 404 for a stored batch, remove only that profile's localStorage key
        const storedBatchId = loadActiveBatchId(activeProfileId);
        if (storedBatchId === activeBatchId) {
          clearActiveBatchId(activeProfileId);
        }
        setSummary(null);
      } else {
        setError(err.message || "Failed to load batch metrics.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [activeProfileId, activeBatchId, refreshTrigger]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const formatCurrency = (val: number | null | undefined) => {
    if (val == null) return "N/A";
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 4 }).format(val);
  };

  const formatTime = (ms: number | null | undefined) => {
    if (ms == null) return "N/A";
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatNumber = (val: number | null | undefined) => {
    if (val == null) return "N/A";
    return new Intl.NumberFormat("en-US").format(val);
  };

  if (!activeProfileId || !activeBatchId || (error == null && summary == null && !isLoading)) {
    return (
      <div className="glass-panel" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
          <BarChart2 size={14} /> Batch Metrics
        </div>
        <div style={{ color: "var(--text-secondary)", fontSize: "13px", textAlign: "center", padding: "16px 0" }}>
          No active batch metrics available.
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
      <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
        <BarChart2 size={14} /> Batch Metrics
      </div>
      
      {error && (
        <div style={{ color: "var(--text-danger)", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {isLoading && !summary && (
        <div style={{ display: "flex", justifyContent: "center", padding: "16px 0", color: "var(--accent)" }}>
          <Loader className="animate-spin" size={20} />
        </div>
      )}

      {summary && (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Jobs Parsed</span>
            <span className="tabular-metrics" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{formatNumber(summary.total_parsed_jobs)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Scorable Jobs</span>
            <span className="tabular-metrics" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{formatNumber(summary.scorable_jobs)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Failed Extractions</span>
            <span className="tabular-metrics" style={{ color: "var(--text-danger)", fontWeight: 500 }}>{formatNumber(summary.failed_extractions)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", borderTop: "1px solid var(--border-color)", paddingTop: "8px", marginTop: "4px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Total Tokens</span>
            <span className="tabular-metrics" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{formatNumber(summary.total_tokens)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Estimated Cost</span>
            <span className="tabular-metrics" style={{ color: "var(--accent)", fontWeight: 500 }}>{formatCurrency(summary.estimated_cost_usd)}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
            <span style={{ color: "var(--text-secondary)" }}>Avg Extraction Time</span>
            <span className="tabular-metrics" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{formatTime(summary.average_extraction_time_ms)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
