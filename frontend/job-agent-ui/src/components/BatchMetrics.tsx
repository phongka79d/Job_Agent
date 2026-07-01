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

  const formatNumber = (val: number | null | undefined) => {
    if (val == null) return null;
    return new Intl.NumberFormat("en-US").format(val);
  };

  if (!activeProfileId || !activeBatchId || (error == null && summary == null && !isLoading)) {
    return (
      <section className="rail-section batch-metrics-panel" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <h2 className="rail-section-title" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <BarChart2 size={14} /> Batch Metrics
        </h2>
        <div style={{ color: "var(--text-secondary)", fontSize: "13px", textAlign: "center", padding: "16px 0" }}>
          No active batch metrics available.
        </div>
      </section>
    );
  }

  return (
    <section className="rail-section batch-metrics-panel" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <h2 className="rail-section-title" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <BarChart2 size={14} /> Batch Metrics
      </h2>
      
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
          <div className="metric-row">
            <span>Jobs parsed</span>
            <strong className="tabular-metrics">{formatNumber(summary.total_parsed_jobs)}</strong>
          </div>
          <div className="metric-row">
            <span>Scorable jobs</span>
            <strong className="tabular-metrics">{formatNumber(summary.scorable_jobs)}</strong>
          </div>
          <div className="metric-row">
            <span>Failed extractions</span>
            <strong className="tabular-metrics">{formatNumber(summary.failed_extractions)}</strong>
          </div>
          <div className="metric-row">
            <span>Total tokens</span>
            <strong className="tabular-metrics">{formatNumber(summary.total_tokens)}</strong>
          </div>
          <div className="metric-row">
            <span>Estimated cost</span>
            <strong className="tabular-metrics">
              {summary.estimated_cost_usd != null
                ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 4 }).format(summary.estimated_cost_usd)
                : null}
            </strong>
          </div>
          {summary.average_extraction_time_ms != null ? (
            <div className="metric-row">
              <span>Average extraction time</span>
              <strong className="tabular-metrics">
                {(summary.average_extraction_time_ms / 1000).toFixed(2)}s
              </strong>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
