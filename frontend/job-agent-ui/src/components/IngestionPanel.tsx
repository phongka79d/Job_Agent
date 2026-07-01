import React, { useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle } from "lucide-react";
import { searchJobs, parseJobUrl, parseJobText, ApiClientError } from "../api/client";
import type { IngestionResponse } from "../types/api";
import IngestionModeTabs from "./ingestion/IngestionModeTabs";
import type { IngestionMode } from "./ingestion/IngestionModeTabs";
import SearchIngestionForm from "./ingestion/SearchIngestionForm";
import UrlIngestionForm from "./ingestion/UrlIngestionForm";
import TextIngestionForm from "./ingestion/TextIngestionForm";

interface IngestionPanelProps {
  activeProfileId: string | null;
  onIngestionSuccess?: (batchId: string) => void;
}

export default function IngestionPanel({
  activeProfileId,
  onIngestionSuccess,
}: IngestionPanelProps) {
  const [activeTab, setActiveTab] = useState<IngestionMode>("search");
  const [isInFlight, setIsInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<IngestionResponse | null>(null);
  const [showUrlManualInputWarning, setShowUrlManualInputWarning] = useState(false);

  // Form states
  const [searchQuery, setSearchQuery] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [jobText, setJobText] = useState("");

  const resetMessages = () => {
    setError(null);
    setSuccessResult(null);
    setShowUrlManualInputWarning(false);
  };

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProfileId || !searchQuery.trim()) return;

    resetMessages();
    setIsInFlight(true);
    try {
      const response = await searchJobs({
        role_profile_id: activeProfileId,
        query: searchQuery.trim(),
      });
      setSuccessResult(response);
      if (onIngestionSuccess && response.batch_id) {
        onIngestionSuccess(response.batch_id);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to run job search ingestion");
      }
    } finally {
      setIsInFlight(false);
    }
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProfileId || !jobUrl.trim()) return;

    resetMessages();
    setIsInFlight(true);
    try {
      const response = await parseJobUrl({
        role_profile_id: activeProfileId,
        source_url: jobUrl.trim(),
      });
      setSuccessResult(response);

      // Check if any job in the response has parse_status === "needs_manual_input"
      const hasNeedsManualInput = response.jobs?.some(
        (job) => job.parse_status === "needs_manual_input"
      );
      if (hasNeedsManualInput) {
        setShowUrlManualInputWarning(true);
      }

      if (onIngestionSuccess && response.batch_id) {
        onIngestionSuccess(response.batch_id);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to run URL parse ingestion");
      }
    } finally {
      setIsInFlight(false);
    }
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProfileId || !jobText.trim()) return;

    resetMessages();
    setIsInFlight(true);
    try {
      const response = await parseJobText({
        role_profile_id: activeProfileId,
        raw_text: jobText.trim(),
      });
      setSuccessResult(response);
      if (onIngestionSuccess && response.batch_id) {
        onIngestionSuccess(response.batch_id);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to run raw text parse ingestion");
      }
    } finally {
      setIsInFlight(false);
    }
  };

  const isDisabled = !activeProfileId || isInFlight;

  return (
    <section className="rail-section ingestion-panel" data-testid="ingestion-panel">
      <h2 className="rail-section-title">Job ingestion</h2>

      {!activeProfileId && (
        <div
          style={{
            color: "var(--text-muted)",
            fontSize: "13px",
            fontStyle: "italic",
            marginBottom: "12px",
          }}
        >
          Select or create a role profile to enable ingestion controls.
        </div>
      )}

      <IngestionModeTabs
        activeMode={activeTab}
        disabled={isInFlight}
        onChange={(mode) => {
          setActiveTab(mode);
          resetMessages();
        }}
      />

      {activeTab === "search" ? (
        <SearchIngestionForm
          value={searchQuery}
          disabled={isDisabled}
          isInFlight={isInFlight}
          onChange={setSearchQuery}
          onSubmit={handleSearchSubmit}
        />
      ) : null}

      {activeTab === "url" ? (
        <UrlIngestionForm
          value={jobUrl}
          disabled={isDisabled}
          isInFlight={isInFlight}
          onChange={setJobUrl}
          onSubmit={handleUrlSubmit}
        />
      ) : null}

      {activeTab === "text" ? (
        <TextIngestionForm
          value={jobText}
          disabled={isDisabled}
          isInFlight={isInFlight}
          onChange={setJobText}
          onSubmit={handleTextSubmit}
        />
      ) : null}

      {/* Safe Error display */}
      {error && (
        <div
          style={{
            color: "var(--text-danger)",
            fontSize: "12px",
            display: "flex",
            alignItems: "flex-start",
            gap: "6px",
            marginTop: "12px",
            background: "rgba(248, 113, 113, 0.08)",
            padding: "8px 12px",
            borderRadius: "var(--radius-md)",
            border: "1px solid rgba(248, 113, 113, 0.2)",
          }}
          data-testid="ingestion-error"
        >
          <AlertCircle size={14} style={{ marginTop: "2px", flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {/* Special URL Manual Input Warning */}
      {showUrlManualInputWarning && (
        <div
          style={{
            color: "#eab308",
            fontSize: "12px",
            display: "flex",
            alignItems: "flex-start",
            gap: "6px",
            marginTop: "12px",
            background: "rgba(234, 179, 8, 0.08)",
            padding: "10px 12px",
            borderRadius: "var(--radius-md)",
            border: "1px solid rgba(234, 179, 8, 0.2)",
            lineHeight: "1.4",
          }}
          data-testid="url-manual-input-warning"
        >
          <AlertTriangle size={14} style={{ marginTop: "2px", flexShrink: 0 }} />
          <div>
            We could not extract enough job content from this URL.
            <br />
            The page may require JavaScript rendering, login, or cookie acceptance.
            <br />
            Please paste the job description text manually.
          </div>
        </div>
      )}

      {/* Ingestion result area */}
      {successResult && (
        <div
          style={{
            marginTop: "12px",
            fontSize: "12px",
            background: "rgba(255, 255, 255, 0.02)",
            padding: "10px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-color)",
          }}
          data-testid="ingestion-result"
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              color: "var(--text-success)",
              fontWeight: 600,
              marginBottom: "8px",
            }}
          >
            <CheckCircle size={14} /> Ingestion Complete
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px", color: "var(--text-secondary)" }}>
            <div>
              <strong>Batch ID:</strong>{" "}
              <span className="tabular-metrics" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                {successResult.batch_id}
              </span>
            </div>
            <div>
              <strong>Jobs Extracted:</strong>{" "}
              <span className="tabular-metrics">{successResult.inserted_jobs}</span>
            </div>
            <div>
              <strong>Duplicates Skipped:</strong>{" "}
              <span className="tabular-metrics">
                {successResult.skipped_exact_duplicates + successResult.skipped_dedup_key_duplicates}
              </span>
            </div>
          </div>

          {/* Render all response warnings */}
          {successResult.warnings && successResult.warnings.length > 0 && (
            <div style={{ marginTop: "8px", borderTop: "1px solid var(--border-color)", paddingTop: "8px" }} data-testid="ingestion-warnings-list">
              <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "#eab308", fontWeight: 600, marginBottom: "4px" }}>
                <AlertTriangle size={12} /> Ingestion Warnings
              </div>
              <ul style={{ margin: 0, paddingLeft: "16px", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "2px" }}>
                {successResult.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
