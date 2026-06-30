import React, { useState } from "react";
import { Search, Link, FileText, Database, Loader2, AlertCircle, AlertTriangle, CheckCircle } from "lucide-react";
import { searchJobs, parseJobUrl, parseJobText, loadMockJobs, ApiClientError } from "../api/client";
import type { IngestionResponse } from "../types/api";

interface IngestionPanelProps {
  activeProfileId: string | null;
  onIngestionSuccess?: (batchId: string) => void;
}

type TabType = "search" | "url" | "text" | "mock";

export default function IngestionPanel({
  activeProfileId,
  onIngestionSuccess,
}: IngestionPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("search");
  const [isInFlight, setIsInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<IngestionResponse | null>(null);
  const [showUrlManualInputWarning, setShowUrlManualInputWarning] = useState(false);

  // Form states
  const [searchQuery, setSearchQuery] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [jobText, setJobText] = useState("");
  const [resetExistingDemo, setResetExistingDemo] = useState(false);

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

  const handleMockLoadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProfileId) return;

    resetMessages();
    setIsInFlight(true);
    try {
      const response = await loadMockJobs({
        role_profile_id: activeProfileId,
        reset_existing_demo: resetExistingDemo,
      });
      setSuccessResult(response);
      if (onIngestionSuccess && response.batch_id) {
        onIngestionSuccess(response.batch_id);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to run mock jobs load");
      }
    } finally {
      setIsInFlight(false);
    }
  };

  const isDisabled = !activeProfileId || isInFlight;

  return (
    <div className="glass-panel" style={{ padding: "16px" }} data-testid="ingestion-panel">
      <div
        style={{
          fontSize: "11px",
          color: "var(--text-muted)",
          marginBottom: "12px",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 600,
        }}
      >
        Ingestion Controls
      </div>

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

      {/* Tab Selectors */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--border-color)",
          marginBottom: "12px",
          gap: "4px",
        }}
      >
        <button
          onClick={() => {
            setActiveTab("search");
            resetMessages();
          }}
          disabled={isInFlight}
          style={{
            background: "transparent",
            border: "none",
            borderBottom: activeTab === "search" ? "2px solid var(--accent)" : "2px solid transparent",
            color: activeTab === "search" ? "var(--accent)" : "var(--text-muted)",
            padding: "6px 8px",
            cursor: isInFlight ? "not-allowed" : "pointer",
            fontSize: "12px",
            fontWeight: activeTab === "search" ? 600 : 400,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            opacity: isDisabled && activeTab !== "search" ? 0.5 : 1,
          }}
          data-testid="tab-search"
        >
          <Search size={12} /> Search
        </button>
        <button
          onClick={() => {
            setActiveTab("url");
            resetMessages();
          }}
          disabled={isInFlight}
          style={{
            background: "transparent",
            border: "none",
            borderBottom: activeTab === "url" ? "2px solid var(--accent)" : "2px solid transparent",
            color: activeTab === "url" ? "var(--accent)" : "var(--text-muted)",
            padding: "6px 8px",
            cursor: isInFlight ? "not-allowed" : "pointer",
            fontSize: "12px",
            fontWeight: activeTab === "url" ? 600 : 400,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            opacity: isDisabled && activeTab !== "url" ? 0.5 : 1,
          }}
          data-testid="tab-url"
        >
          <Link size={12} /> URL
        </button>
        <button
          onClick={() => {
            setActiveTab("text");
            resetMessages();
          }}
          disabled={isInFlight}
          style={{
            background: "transparent",
            border: "none",
            borderBottom: activeTab === "text" ? "2px solid var(--accent)" : "2px solid transparent",
            color: activeTab === "text" ? "var(--accent)" : "var(--text-muted)",
            padding: "6px 8px",
            cursor: isInFlight ? "not-allowed" : "pointer",
            fontSize: "12px",
            fontWeight: activeTab === "text" ? 600 : 400,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            opacity: isDisabled && activeTab !== "text" ? 0.5 : 1,
          }}
          data-testid="tab-text"
        >
          <FileText size={12} /> Text
        </button>
        <button
          onClick={() => {
            setActiveTab("mock");
            resetMessages();
          }}
          disabled={isInFlight}
          style={{
            background: "transparent",
            border: "none",
            borderBottom: activeTab === "mock" ? "2px solid var(--accent)" : "2px solid transparent",
            color: activeTab === "mock" ? "var(--accent)" : "var(--text-muted)",
            padding: "6px 8px",
            cursor: isInFlight ? "not-allowed" : "pointer",
            fontSize: "12px",
            fontWeight: activeTab === "mock" ? 600 : 400,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            opacity: isDisabled && activeTab !== "mock" ? 0.5 : 1,
          }}
          data-testid="tab-mock"
        >
          <Database size={12} /> Demo
        </button>
      </div>

      {/* Forms based on active tab */}
      {activeTab === "search" && (
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }} data-testid="form-search">
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              Public Job Search Query
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. React Developer in London"
              disabled={isDisabled}
              style={{
                padding: "8px 10px",
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontSize: "13px",
                outline: "none",
                opacity: isDisabled ? 0.6 : 1,
              }}
              required
              data-testid="input-search-query"
            />
          </div>
          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
            disabled={isDisabled || !searchQuery.trim()}
            data-testid="btn-search-submit"
          >
            {isInFlight ? (
              <>
                <Loader2 size={14} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                Searching...
              </>
            ) : (
              "Search Jobs"
            )}
          </button>
        </form>
      )}

      {activeTab === "url" && (
        <form onSubmit={handleUrlSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }} data-testid="form-url">
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              Job Posting URL
            </label>
            <input
              type="url"
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              placeholder="https://example.com/jobs/react-engineer"
              disabled={isDisabled}
              style={{
                padding: "8px 10px",
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontSize: "13px",
                outline: "none",
                opacity: isDisabled ? 0.6 : 1,
              }}
              required
              data-testid="input-url"
            />
          </div>
          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
            disabled={isDisabled || !jobUrl.trim()}
            data-testid="btn-url-submit"
          >
            {isInFlight ? (
              <>
                <Loader2 size={14} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                Parsing...
              </>
            ) : (
              "Parse URL"
            )}
          </button>
        </form>
      )}

      {activeTab === "text" && (
        <form onSubmit={handleTextSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }} data-testid="form-text">
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              Job Description Text
            </label>
            <textarea
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              placeholder="Paste the raw job description here..."
              disabled={isDisabled}
              style={{
                padding: "8px 10px",
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontSize: "13px",
                outline: "none",
                resize: "vertical",
                minHeight: "100px",
                fontFamily: "var(--font-sans)",
                opacity: isDisabled ? 0.6 : 1,
              }}
              required
              data-testid="input-text"
            />
          </div>
          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
            disabled={isDisabled || !jobText.trim()}
            data-testid="btn-text-submit"
          >
            {isInFlight ? (
              <>
                <Loader2 size={14} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                Parsing...
              </>
            ) : (
              "Parse Text"
            )}
          </button>
        </form>
      )}

      {activeTab === "mock" && (
        <form onSubmit={handleMockLoadSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }} data-testid="form-mock">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "4px 0" }}>
            <input
              type="checkbox"
              id="resetExistingDemo"
              checked={resetExistingDemo}
              onChange={(e) => setResetExistingDemo(e.target.checked)}
              disabled={isDisabled}
              style={{ cursor: isDisabled ? "not-allowed" : "pointer" }}
              data-testid="input-reset-demo"
            />
            <label
              htmlFor="resetExistingDemo"
              style={{
                fontSize: "12px",
                color: "var(--text-secondary)",
                cursor: isDisabled ? "not-allowed" : "pointer",
              }}
            >
              Reset existing demo data
            </label>
          </div>
          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
            disabled={isDisabled}
            data-testid="btn-mock-submit"
          >
            {isInFlight ? (
              <>
                <Loader2 size={14} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                Loading Mock...
              </>
            ) : (
              "Load Mock Jobs"
            )}
          </button>
        </form>
      )}

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
            color: "#eab308", // Amber
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
    </div>
  );
}
