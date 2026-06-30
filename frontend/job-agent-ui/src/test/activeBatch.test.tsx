import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import {
  listRoleProfiles,
  loadMockJobs,
  searchJobs,
  parseJobUrl,
  parseJobText,
  getReviewJobs,
  getJobs,
  getBatchSummary
} from "../api/client";
import type { RoleProfile, IngestionResponse, BatchSummary } from "../types/api";

// Mock the API client
vi.mock("../api/client", () => {
  return {
    listRoleProfiles: vi.fn(),
    loadMockJobs: vi.fn(),
    searchJobs: vi.fn(),
    parseJobUrl: vi.fn(),
    parseJobText: vi.fn(),
    getReviewJobs: vi.fn(),
    getJobs: vi.fn(),
    getBatchSummary: vi.fn(),
    ApiClientError: class extends Error {
      message: string;
      constructor(message: string) {
        super(message);
        this.message = message;
      }
    },
  };
});

const mockProfiles: RoleProfile[] = [
  {
    id: "prof-1",
    target_role: "Software Engineer",
    level: "Mid",
    location: "San Francisco",
    accept_remote: true,
    skills: ["React", "TypeScript"],
    resume_text: "Resume 1",
    created_at: "2026-06-30T10:00:00Z",
    updated_at: "2026-06-30T10:00:00Z",
  },
  {
    id: "prof-2",
    target_role: "Data Scientist",
    level: "Senior",
    location: "New York",
    accept_remote: false,
    skills: ["Python", "SQL"],
    resume_text: null,
    created_at: "2026-06-30T11:00:00Z",
    updated_at: "2026-06-30T11:00:00Z",
  },
];

const mockIngestionResponse1: IngestionResponse = {
  batch_id: "batch-abc",
  inserted_jobs: 2,
  skipped_exact_duplicates: 0,
  skipped_dedup_key_duplicates: 0,
  inserted_duplicate_metadata: 0,
  qdrant_upserted: 2,
  qdrant_synced: true,
  jobs: [],
  warnings: [],
};

const mockIngestionResponse2: IngestionResponse = {
  batch_id: "batch-xyz",
  inserted_jobs: 3,
  skipped_exact_duplicates: 0,
  skipped_dedup_key_duplicates: 0,
  inserted_duplicate_metadata: 0,
  qdrant_upserted: 3,
  qdrant_synced: true,
  jobs: [],
  warnings: [],
};

const mockBatchSummary = (batchId: string): BatchSummary => ({
  batch_id: batchId,
  total_parsed_jobs: 4,
  scorable_jobs: 3,
  failed_extractions: 1,
  total_input_tokens: 1000,
  total_output_tokens: 500,
  total_tokens: 1500,
  estimated_cost_usd: 0.02,
  average_extraction_time_ms: 1200,
});

describe("Active Batch State and Role Isolation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(getReviewJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(getBatchSummary).mockImplementation(async (batchId) => mockBatchSummary(batchId));
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("should isolate active batch IDs between different role profiles in localStorage", async () => {
    // 1. Setup API mocks
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });
    vi.mocked(loadMockJobs).mockResolvedValue(mockIngestionResponse1);

    // 2. Render the App
    render(<App />);

    // Wait for the profiles select to load and auto-select the first one (prof-1)
    await waitFor(() => {
      expect(screen.getByTestId("profile-select")).toBeInTheDocument();
    });

    const profileSelect = screen.getByTestId("profile-select") as HTMLSelectElement;
    expect(profileSelect.value).toBe("prof-1");

    // Initially, there should be no active batch ID
    expect(screen.getByText(/Active Batch ID:/)).toHaveTextContent("Active Batch ID: None");

    // 3. Switch to Demo Ingestion and trigger mock load for prof-1
    fireEvent.click(screen.getByTestId("tab-mock"));
    const submitMockBtn = screen.getByTestId("btn-mock-submit");
    fireEvent.click(submitMockBtn);

    // Wait for API call and active batch ID to update to batch-abc
    await waitFor(() => {
      expect(loadMockJobs).toHaveBeenCalledWith({
        role_profile_id: "prof-1",
        reset_existing_demo: false,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Active Batch ID:/)).toHaveTextContent("Active Batch ID: batch-abc");
    });

    // 4. Verify localStorage has batch-abc only for prof-1
    expect(localStorage.getItem("job-agent.activeBatchId.prof-1")).toBe("batch-abc");
    expect(localStorage.getItem("job-agent.activeBatchId.prof-2")).toBeNull();
    const summaryCallsAfterProfileOneIngestion = vi.mocked(getBatchSummary).mock.calls.length;

    // 5. Switch to prof-2 and verify active batch ID is cleared (becomes None)
    fireEvent.change(profileSelect, { target: { value: "prof-2" } });
    expect(profileSelect.value).toBe("prof-2");

    await waitFor(() => {
      expect(screen.getByText(/Active Batch ID:/)).toHaveTextContent("Active Batch ID: None");
    });
    expect(getBatchSummary).toHaveBeenCalledTimes(summaryCallsAfterProfileOneIngestion);

    // 6. Mock ingestion response for prof-2 with a different batch ID (batch-xyz)
    vi.mocked(loadMockJobs).mockResolvedValue(mockIngestionResponse2);
    fireEvent.click(submitMockBtn);

    await waitFor(() => {
      expect(loadMockJobs).toHaveBeenLastCalledWith({
        role_profile_id: "prof-2",
        reset_existing_demo: false,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Active Batch ID:/)).toHaveTextContent("Active Batch ID: batch-xyz");
    });
    await waitFor(() => {
      expect(getBatchSummary).toHaveBeenLastCalledWith("batch-xyz");
    });

    // 7. Verify localStorage isolation holds
    expect(localStorage.getItem("job-agent.activeBatchId.prof-1")).toBe("batch-abc");
    expect(localStorage.getItem("job-agent.activeBatchId.prof-2")).toBe("batch-xyz");

    // 8. Switch back to prof-1 and verify active batch ID reloads to batch-abc
    fireEvent.change(profileSelect, { target: { value: "prof-1" } });
    await waitFor(() => {
      expect(screen.getByText(/Active Batch ID:/)).toHaveTextContent("Active Batch ID: batch-abc");
    });
    await waitFor(() => {
      expect(getBatchSummary).toHaveBeenLastCalledWith("batch-abc");
    });

    // 9. Switch back to prof-2 and verify active batch ID reloads to batch-xyz
    fireEvent.change(profileSelect, { target: { value: "prof-2" } });
    await waitFor(() => {
      expect(screen.getByText(/Active Batch ID:/)).toHaveTextContent("Active Batch ID: batch-xyz");
    });
    await waitFor(() => {
      expect(getBatchSummary).toHaveBeenLastCalledWith("batch-xyz");
    });
  });

  it("should never call a backend latest-batch endpoint", async () => {
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });
    
    // Create an arbitrary mock spy object representing api-client to check any other call
    // In our vi.mock, only defined functions are mocked. We can check that no other methods were called.
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("profile-select")).toBeInTheDocument();
    });

    // Switch profile
    const profileSelect = screen.getByTestId("profile-select") as HTMLSelectElement;
    fireEvent.change(profileSelect, { target: { value: "prof-2" } });

    // There should be no ingestion or dashboard calls. Review jobs may load for the selected profile,
    // but no latest-batch discovery endpoint exists or is called.
    expect(searchJobs).not.toHaveBeenCalled();
    expect(parseJobUrl).not.toHaveBeenCalled();
    expect(parseJobText).not.toHaveBeenCalled();
    expect(getJobs).not.toHaveBeenCalled();
    expect(getReviewJobs).toHaveBeenCalledWith("prof-2");

    // Verify localStorage key for prof-2 doesn't trigger any API fetch
    const storedBatchId = localStorage.getItem("job-agent.activeBatchId.prof-2");
    expect(storedBatchId).toBeNull();
    expect(getBatchSummary).not.toHaveBeenCalled();
    expect(screen.getByText("No active batch metrics available.")).toBeInTheDocument();
  });

  it("should remove only the selected profile active batch key when its summary returns 404", async () => {
    localStorage.setItem("job-agent.activeBatchId.prof-1", "stale-batch");
    localStorage.setItem("job-agent.activeBatchId.prof-2", "other-batch");
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });

    const error404 = new Error("Not Found") as any;
    error404.status = 404;
    vi.mocked(getBatchSummary).mockRejectedValue(error404);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("profile-select")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(getBatchSummary).toHaveBeenCalledWith("stale-batch");
      expect(screen.getByText("No active batch metrics available.")).toBeInTheDocument();
    });

    expect(localStorage.getItem("job-agent.activeBatchId.prof-1")).toBeNull();
    expect(localStorage.getItem("job-agent.activeBatchId.prof-2")).toBe("other-batch");
  });
});
