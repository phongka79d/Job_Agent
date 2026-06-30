import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReviewPage from "../pages/ReviewPage";
import { getReviewJobs, approveJob, rejectJob } from "../api/client";
import { useOutletContext } from "react-router-dom";
import type { Job } from "../types/api";

// Mock the API client functions
vi.mock("../api/client", () => ({
  getReviewJobs: vi.fn(),
  approveJob: vi.fn(),
  rejectJob: vi.fn(),
}));

// Mock useOutletContext
vi.mock("react-router-dom", () => ({
  useOutletContext: vi.fn(),
}));

const mockJobs: Job[] = [
  {
    id: "job-1",
    batch_id: "batch-123",
    role_profile_id: "profile-456",
    title: "React Developer",
    company: "Tech Corp",
    location: "SF",
    work_mode: "Remote",
    level: "Senior",
    employment_type: "Full-time",
    salary: "$120k",
    responsibilities: "",
    requirements: "",
    skills: [],
    source_url: "",
    source_platform: "mock",
    parse_status: "success",
    jd_status: "full_jd",
    extraction_status: "success",
    error_reason: null,
    should_score_similarity: true,
    embedding_similarity: 0.8,
    skill_overlap_score: 0.8,
    location_match_score: 1.0,
    level_match_score: 1.0,
    base_score: 0.8,
    jd_confidence_multiplier: 1.0,
    final_score: 0.8,
    final_score_percent: 80.0,
    status: "pending_review",
    input_tokens: 0,
    output_tokens: 0,
    estimated_cost_usd: 0,
    extraction_time_ms: 0,
    discovered_at: "",
    created_at: "",
    updated_at: "",
  },
  {
    id: "job-2",
    batch_id: "batch-123",
    role_profile_id: "profile-456",
    title: "Vue Developer",
    company: "Other Corp",
    location: "NY",
    work_mode: "Hybrid",
    level: "Mid",
    employment_type: "Full-time",
    salary: "$100k",
    responsibilities: "",
    requirements: "",
    skills: [],
    source_url: "",
    source_platform: "mock",
    parse_status: "success",
    jd_status: "full_jd",
    extraction_status: "success",
    error_reason: null,
    should_score_similarity: true,
    embedding_similarity: 0.7,
    skill_overlap_score: 0.7,
    location_match_score: 1.0,
    level_match_score: 1.0,
    base_score: 0.7,
    jd_confidence_multiplier: 1.0,
    final_score: 0.7,
    final_score_percent: 70.0,
    status: "pending_review",
    input_tokens: 0,
    output_tokens: 0,
    estimated_cost_usd: 0,
    extraction_time_ms: 0,
    discovered_at: "",
    created_at: "",
    updated_at: "",
  },
  {
    id: "job-3",
    batch_id: "batch-different",
    role_profile_id: "profile-456",
    title: "Angular Developer",
    company: "Big Corp",
    location: "TX",
    work_mode: "Onsite",
    level: "Junior",
    employment_type: "Full-time",
    salary: "$80k",
    responsibilities: "",
    requirements: "",
    skills: [],
    source_url: "",
    source_platform: "mock",
    parse_status: "success",
    jd_status: "full_jd",
    extraction_status: "success",
    error_reason: null,
    should_score_similarity: true,
    embedding_similarity: 0.6,
    skill_overlap_score: 0.6,
    location_match_score: 1.0,
    level_match_score: 1.0,
    base_score: 0.6,
    jd_confidence_multiplier: 1.0,
    final_score: 0.6,
    final_score_percent: 60.0,
    status: "pending_review",
    input_tokens: 0,
    output_tokens: 0,
    estimated_cost_usd: 0,
    extraction_time_ms: 0,
    discovered_at: "",
    created_at: "",
    updated_at: "",
  }
];

describe("ReviewPage component tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders role profile selection prompt when activeProfileId is missing", () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: null, activeBatchId: null });
    render(<ReviewPage />);
    expect(screen.getByText(/Please select or create a role profile/i)).toBeInTheDocument();
  });

  it("fetches review jobs when activeBatchId is missing", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: null });
    vi.mocked(getReviewJobs).mockResolvedValue({ jobs: [mockJobs[0]] });
    render(<ReviewPage />);

    await waitFor(() => {
      expect(getReviewJobs).toHaveBeenCalledWith("profile-456");
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });
  });

  it("renders empty state when there are no pending review jobs", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: null });
    vi.mocked(getReviewJobs).mockResolvedValue({ jobs: [] });
    render(<ReviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/No jobs pending review/i)).toBeInTheDocument();
    });
  });

  it("fetches and renders backend pending review jobs across batches", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    vi.mocked(getReviewJobs).mockResolvedValue({ jobs: mockJobs });
    render(<ReviewPage />);

    // Review queue scope is the role profile. Active batch is only used by metrics.
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
      expect(screen.getByText("Vue Developer")).toBeInTheDocument();
      expect(screen.getByText("Angular Developer")).toBeInTheDocument();
    });
  });

  it("approving a job calls the API and refreshes the list from the backend", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    vi.mocked(getReviewJobs)
      .mockResolvedValueOnce({ jobs: [mockJobs[0]] })
      .mockResolvedValueOnce({ jobs: [] });
    vi.mocked(approveJob).mockResolvedValue({ ...mockJobs[0], status: "saved" });

    render(<ReviewPage />);
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    fireEvent.click(approveBtn);

    expect(approveJob).toHaveBeenCalledWith("job-1");
    await waitFor(() => {
      expect(getReviewJobs).toHaveBeenCalledTimes(2);
      expect(screen.queryByText("React Developer")).not.toBeInTheDocument();
      expect(screen.getByText(/No jobs pending review/i)).toBeInTheDocument();
    });
  });

  it("rejecting a job calls the API and refreshes the list from the backend", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    vi.mocked(getReviewJobs)
      .mockResolvedValueOnce({ jobs: [mockJobs[0]] })
      .mockResolvedValueOnce({ jobs: [] });
    vi.mocked(rejectJob).mockResolvedValue({ ...mockJobs[0], status: "ignored" });

    render(<ReviewPage />);
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });

    const rejectBtn = screen.getByRole("button", { name: /reject/i });
    fireEvent.click(rejectBtn);

    expect(rejectJob).toHaveBeenCalledWith("job-1");
    await waitFor(() => {
      expect(getReviewJobs).toHaveBeenCalledTimes(2);
      expect(screen.queryByText("React Developer")).not.toBeInTheDocument();
      expect(screen.getByText(/No jobs pending review/i)).toBeInTheDocument();
    });
  });

  it("displays error message when action fails and keeps the job in the list", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    vi.mocked(getReviewJobs).mockResolvedValue({ jobs: [mockJobs[0]] });
    vi.mocked(approveJob).mockRejectedValue(new Error("Network Error"));

    render(<ReviewPage />);
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    fireEvent.click(approveBtn);

    expect(approveJob).toHaveBeenCalledWith("job-1");
    await waitFor(() => {
      expect(screen.getByText("Network Error")).toBeInTheDocument();
      // Job should still be there because action failed
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });
  });
});
