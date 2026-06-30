import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import BatchMetrics from "../components/BatchMetrics";
import { getBatchSummary } from "../api/client";
import { saveActiveBatchId, loadActiveBatchId } from "../utils/activeBatchStorage";
import type { BatchSummary } from "../types/api";

vi.mock("../api/client", () => ({
  getBatchSummary: vi.fn(),
}));

describe("BatchMetrics Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("should render empty state when no active batch exists", () => {
    render(<BatchMetrics activeProfileId="prof-1" activeBatchId={null} refreshTrigger={0} />);
    expect(screen.getByText("No active batch metrics available.")).toBeInTheDocument();
  });

  it("should render empty state when no active profile exists", () => {
    render(<BatchMetrics activeProfileId={null} activeBatchId="batch-123" refreshTrigger={0} />);
    expect(screen.getByText("No active batch metrics available.")).toBeInTheDocument();
  });

  it("should render metrics successfully on successful fetch", async () => {
    const mockSummary: BatchSummary = {
      batch_id: "batch-123",
      total_parsed_jobs: 10,
      scorable_jobs: 8,
      failed_extractions: 1,
      total_input_tokens: 10000,
      total_output_tokens: 2000,
      total_tokens: 12000,
      estimated_cost_usd: 0.15,
      average_extraction_time_ms: 2500,
    };
    vi.mocked(getBatchSummary).mockResolvedValue(mockSummary);

    render(<BatchMetrics activeProfileId="prof-1" activeBatchId="batch-123" refreshTrigger={0} />);

    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument(); // total_parsed_jobs
      expect(screen.getByText("8")).toBeInTheDocument(); // scorable_jobs
      expect(screen.getByText("1")).toBeInTheDocument(); // failed_extractions
      expect(screen.getByText("12,000")).toBeInTheDocument(); // total_tokens
      expect(screen.getByText("$0.1500")).toBeInTheDocument(); // estimated_cost_usd
      expect(screen.getByText("2.50s")).toBeInTheDocument(); // average_extraction_time_ms
    });
  });

  it("should remove localStorage key and show empty state on 404", async () => {
    saveActiveBatchId("prof-1", "batch-123");
    
    const error404 = new Error("Not Found") as any;
    error404.status = 404;
    vi.mocked(getBatchSummary).mockRejectedValue(error404);

    render(<BatchMetrics activeProfileId="prof-1" activeBatchId="batch-123" refreshTrigger={0} />);

    await waitFor(() => {
      expect(screen.getByText("No active batch metrics available.")).toBeInTheDocument();
    });

    expect(loadActiveBatchId("prof-1")).toBeNull();
  });

  it("should show error state for other errors", async () => {
    saveActiveBatchId("prof-1", "batch-123");
    
    const error500 = new Error("Server Error") as any;
    error500.status = 500;
    vi.mocked(getBatchSummary).mockRejectedValue(error500);

    render(<BatchMetrics activeProfileId="prof-1" activeBatchId="batch-123" refreshTrigger={0} />);

    await waitFor(() => {
      expect(screen.getByText("Server Error")).toBeInTheDocument();
    });

    // Should not remove key on 500
    expect(loadActiveBatchId("prof-1")).toBe("batch-123");
  });
});
