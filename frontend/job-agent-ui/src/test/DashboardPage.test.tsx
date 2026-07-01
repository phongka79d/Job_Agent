import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "../pages/DashboardPage";
import { getJobs } from "../api/client";
import { useOutletContext } from "react-router-dom";
import type { Job } from "../types/api";

// Mock the API client functions
vi.mock("../api/client", () => ({
  getJobs: vi.fn(),
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
    source_platform: "manual_text",
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
    status: "applied",
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
    source_platform: "manual_text",
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
    status: "interview",
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
    source_platform: "manual_text",
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
    status: "offer",
    input_tokens: 0,
    output_tokens: 0,
    estimated_cost_usd: 0,
    extraction_time_ms: 0,
    discovered_at: "",
    created_at: "",
    updated_at: "",
  }
];

describe("DashboardPage component tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders role profile selection prompt when activeProfileId is missing", () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: null, activeBatchId: null });
    render(<DashboardPage />);
    expect(screen.getByText(/Select or create a role profile/i)).toBeInTheDocument();
  });

  it("fetches tracked jobs when activeBatchId is missing", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: null });
    vi.mocked(getJobs).mockResolvedValue({ jobs: [mockJobs[0]] });
    render(<DashboardPage />);

    await waitFor(() => {
      expect(getJobs).toHaveBeenCalledWith("profile-456", "tracked");
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });
  });

  it("renders empty state when there are no tracked jobs", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: null });
    vi.mocked(getJobs).mockResolvedValue({ jobs: [] });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/No tracked jobs found/i)).toBeInTheDocument();
    });
  });

  it("renders loading state initially then displays jobs", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    
    // Set up getJobs mock that takes a bit to resolve to test loading state
    let resolveGetJobs: any;
    const promise = new Promise<any>((resolve) => {
      resolveGetJobs = resolve;
    });
    vi.mocked(getJobs).mockReturnValue(promise);

    render(<DashboardPage />);
    
    // Check loading indicator
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();

    // Resolve promise
    resolveGetJobs({ jobs: mockJobs });

    // Wait for the jobs to render
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
      expect(screen.getByText("Vue Developer")).toBeInTheDocument();
    });
  });

  it("fetches tracked jobs and preserves backend returned statuses across batches", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    vi.mocked(getJobs).mockResolvedValue({ jobs: mockJobs });
    render(<DashboardPage />);

    // Dashboard scope is the role profile and backend-tracked status filter.
    // Active batch is only used by the metrics panel, so older tracked jobs stay visible.
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
      expect(screen.getByText("Vue Developer")).toBeInTheDocument();
      expect(screen.getByText("Angular Developer")).toBeInTheDocument();
    });

    // Verify it called API with correct status="tracked" and role_profile_id="profile-456"
    expect(getJobs).toHaveBeenCalledWith("profile-456", "tracked");
  });
});
