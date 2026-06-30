import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import IngestionPanel from "../components/IngestionPanel";
import { searchJobs, parseJobUrl, parseJobText, ApiClientError } from "../api/client";
import type { IngestionResponse } from "../types/api";

// Mock the API client functions
vi.mock("../api/client", () => {
  return {
    searchJobs: vi.fn(),
    parseJobUrl: vi.fn(),
    parseJobText: vi.fn(),
    ApiClientError: class extends Error {
      message: string;
      constructor(message: string) {
        super(message);
        this.message = message;
      }
    },
  };
});

const mockSuccessResponse: IngestionResponse = {
  batch_id: "batch-123",
  inserted_jobs: 3,
  skipped_exact_duplicates: 1,
  skipped_dedup_key_duplicates: 0,
  inserted_duplicate_metadata: 0,
  qdrant_upserted: 3,
  qdrant_synced: true,
  jobs: [],
  warnings: ["Low-priority source warning"],
};

describe("IngestionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should require an active role profile before enabling ingestion actions", () => {
    // Render without an active profile
    render(<IngestionPanel activeProfileId={null} />);

    expect(screen.getByText(/Select or create a role profile to enable ingestion controls/i)).toBeInTheDocument();

    // Default tab is search, check if input and button are disabled
    const queryInput = screen.getByTestId("input-search-query");
    const searchBtn = screen.getByTestId("btn-search-submit");
    expect(queryInput).toBeDisabled();
    expect(searchBtn).toBeDisabled();
  });

  it("should switch tabs to reveal different form controls", async () => {
    render(<IngestionPanel activeProfileId="prof-1" />);

    // Default tab is Search
    expect(screen.getByTestId("form-search")).toBeInTheDocument();
    expect(screen.queryByTestId("form-url")).not.toBeInTheDocument();

    // Click URL tab
    fireEvent.click(screen.getByTestId("tab-url"));
    expect(screen.queryByTestId("form-search")).not.toBeInTheDocument();
    expect(screen.getByTestId("form-url")).toBeInTheDocument();

    // Click Text tab
    fireEvent.click(screen.getByTestId("tab-text"));
    expect(screen.queryByTestId("form-url")).not.toBeInTheDocument();
    expect(screen.getByTestId("form-text")).toBeInTheDocument();

    expect(screen.queryByTestId("tab-mock")).not.toBeInTheDocument();
    expect(screen.queryByTestId("form-mock")).not.toBeInTheDocument();
  });

  it("should handle in-flight disabled states and trigger searchJobs with correct inputs", async () => {
    const user = userEvent.setup();
    const onIngestionSuccess = vi.fn();
    vi.mocked(searchJobs).mockResolvedValue(mockSuccessResponse);

    render(
      <IngestionPanel activeProfileId="prof-1" onIngestionSuccess={onIngestionSuccess} />
    );

    const queryInput = screen.getByTestId("input-search-query");
    await user.type(queryInput, "React Developer");

    const searchBtn = screen.getByTestId("btn-search-submit");
    fireEvent.click(searchBtn);

    // Verify searchJobs API was called with the correct parameters
    await waitFor(() => {
      expect(searchJobs).toHaveBeenCalledWith({
        role_profile_id: "prof-1",
        query: "React Developer",
      });
    });

    // Verify callback was triggered with the batch ID
    await waitFor(() => {
      expect(onIngestionSuccess).toHaveBeenCalledWith("batch-123");
    });

    // Check that success details are displayed
    expect(screen.getByText(/Ingestion Complete/i)).toBeInTheDocument();
    expect(screen.getByText(/batch-123/i)).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument(); // jobs extracted

    // Check warnings
    expect(screen.getByText("Ingestion Warnings")).toBeInTheDocument();
    expect(screen.getByText("Low-priority source warning")).toBeInTheDocument();
  });

  it("should parse job URL and render Plan 5 specific user-facing warning if parse_status is needs_manual_input", async () => {
    const user = userEvent.setup();
    const onIngestionSuccess = vi.fn();

    const lowContentUrlResponse: IngestionResponse = {
      ...mockSuccessResponse,
      jobs: [
        {
          id: "job-1",
          batch_id: "batch-123",
          role_profile_id: "prof-1",
          title: "Incomplete Job",
          company: "Acme",
          location: "Remote",
          work_mode: null,
          level: null,
          employment_type: null,
          salary: null,
          responsibilities: null,
          requirements: null,
          skills: [],
          source_url: "https://example.com/low-content",
          source_platform: "manual_url",
          parse_status: "needs_manual_input",
          jd_status: "no_jd",
          extraction_status: "failed",
          error_reason: "Too short",
          should_score_similarity: false,
          embedding_similarity: null,
          skill_overlap_score: null,
          location_match_score: null,
          level_match_score: null,
          base_score: null,
          jd_confidence_multiplier: null,
          final_score: null,
          final_score_percent: null,
          status: "pending_review",
          input_tokens: null,
          output_tokens: null,
          estimated_cost_usd: null,
          extraction_time_ms: null,
          discovered_at: null,
          created_at: "2026-06-30T10:00:00Z",
          updated_at: "2026-06-30T10:00:00Z",
        },
      ],
    };

    vi.mocked(parseJobUrl).mockResolvedValue(lowContentUrlResponse);

    render(
      <IngestionPanel activeProfileId="prof-1" onIngestionSuccess={onIngestionSuccess} />
    );

    // Switch to URL tab
    fireEvent.click(screen.getByTestId("tab-url"));

    const urlInput = screen.getByTestId("input-url");
    await user.type(urlInput, "https://example.com/low-content");

    const submitBtn = screen.getByTestId("btn-url-submit");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(parseJobUrl).toHaveBeenCalledWith({
        role_profile_id: "prof-1",
        source_url: "https://example.com/low-content",
      });
    });

    // Assert the exact user-facing warning text from Plan 5 is displayed
    await waitFor(() => {
      expect(screen.getByTestId("url-manual-input-warning")).toBeInTheDocument();
    });
    
    expect(
      screen.getByText((content) =>
        content.includes("We could not extract enough job content from this URL")
      )
    ).toBeInTheDocument();
    
    expect(
      screen.getByText((content) =>
        content.includes("The page may require JavaScript rendering, login, or cookie acceptance")
      )
    ).toBeInTheDocument();

    expect(
      screen.getByText((content) =>
        content.includes("Please paste the job description text manually")
      )
    ).toBeInTheDocument();
  });

  it("should surface backend validation errors in a safe error state", async () => {
    const user = userEvent.setup();
    vi.mocked(parseJobText).mockRejectedValue(
      new ApiClientError("Validation Error: raw_text cannot be empty")
    );

    render(<IngestionPanel activeProfileId="prof-1" />);

    // Switch to Text tab
    fireEvent.click(screen.getByTestId("tab-text"));

    const textInput = screen.getByTestId("input-text");
    await user.type(textInput, "Some Job Text");

    const submitBtn = screen.getByTestId("btn-text-submit");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(parseJobText).toHaveBeenCalledWith({
        role_profile_id: "prof-1",
        raw_text: "Some Job Text",
      });
    });

    // Check that error is displayed
    await waitFor(() => {
      expect(screen.getByTestId("ingestion-error")).toBeInTheDocument();
    });
    expect(screen.getByText("Validation Error: raw_text cannot be empty")).toBeInTheDocument();
  });

});
