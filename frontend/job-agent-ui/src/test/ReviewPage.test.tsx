import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReviewPage from "../pages/ReviewPage";
import { getReviewJobs, approveJob, rejectJob, generateJobCvImprovements } from "../api/client";
import { createCvDraft, previewCvDraft } from "../api/profileDocumentsClient";
import { useOutletContext } from "react-router-dom";
import type { Job } from "../types/api";

// Mock the API client functions
vi.mock("../api/client", () => ({
  getReviewJobs: vi.fn(),
  approveJob: vi.fn(),
  rejectJob: vi.fn(),
  generateJobCvImprovements: vi.fn(),
}));

vi.mock("../api/profileDocumentsClient", () => ({
  createCvDraft: vi.fn(),
  previewCvDraft: vi.fn(),
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
    expect(screen.getByText(/Select or create a role profile/i)).toBeInTheDocument();
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

  it("creates and previews a CV draft from generated wording-only suggestions", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-456", activeBatchId: "batch-123" });
    vi.mocked(getReviewJobs).mockResolvedValue({ jobs: [mockJobs[0]] });
    vi.mocked(generateJobCvImprovements).mockResolvedValue({
      job_id: "job-1",
      role_profile_id: "profile-456",
      document_id: "doc-1",
      version_id: "version-1",
      suggestion_count: 1,
      suggestions: [
        {
          id: "suggestion-1",
          role_profile_id: "profile-456",
          document_id: "doc-1",
          version_id: "version-1",
          job_id: "job-1",
          requirement: "React",
          current_cv_evidence: "Built React components.",
          missing_or_weak_evidence: "React impact can be clearer.",
          proposed_edit: "Rewrite the React bullet with stronger impact.",
          edit_kind: "wording_only",
          risk_level: "low",
          requires_confirmation: true,
          status: "suggested",
          created_at: "2026-07-02T00:00:00Z",
          updated_at: "2026-07-02T00:00:00Z",
        },
      ],
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(createCvDraft).mockResolvedValue({
      id: "draft-1",
      role_profile_id: "profile-456",
      document_id: "doc-1",
      base_version_id: "version-1",
      status: "draft",
      title: "CV draft for React Developer",
      structure_status_at_creation: "reliable",
      created_by: "ai",
      created_at: "2026-07-02T00:00:00Z",
      updated_at: "2026-07-02T00:00:00Z",
    });
    vi.mocked(previewCvDraft).mockResolvedValue({
      draft_id: "draft-1",
      title: "CV draft for React Developer",
      status: "draft",
      structure_status: "reliable",
      recommendation: null,
      sections: [],
      edits: [
        {
          requirement: "React",
          current_cv_evidence: "Built React components.",
          proposed_edit: "Rewrite the React bullet with stronger impact.",
          edit_kind: "wording_only",
          risk_level: "low",
        },
      ],
    });

    render(<ReviewPage />);
    await waitFor(() => {
      expect(screen.getByText("React Developer")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /improve cv/i }));

    await waitFor(() => {
      expect(createCvDraft).toHaveBeenCalledWith("profile-456", "doc-1", "version-1", {
        title: "CV draft for React Developer",
        suggestion_ids: ["suggestion-1"],
        confirmed: true,
      });
      expect(previewCvDraft).toHaveBeenCalledWith("profile-456", "doc-1", "draft-1");
      expect(screen.getByText("CV draft created")).toBeInTheDocument();
      expect(screen.getByText("CV draft for React Developer")).toBeInTheDocument();
      expect(screen.getAllByText("Rewrite the React bullet with stronger impact.").length).toBeGreaterThanOrEqual(2);
    });
  });
});
