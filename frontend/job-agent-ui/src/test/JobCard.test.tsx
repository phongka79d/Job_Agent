import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import JobCard from "../components/JobCard";
import type { Job } from "../types/api";

const mockScorableJob: Job = {
  id: "job-1",
  batch_id: "batch-1",
  role_profile_id: "profile-1",
  title: "React Developer",
  company: "Tech Corp",
  location: "San Francisco, CA",
  work_mode: "Remote",
  level: "Senior",
  employment_type: "Full-time",
  salary: "$120k - $150k",
  responsibilities: "Build components",
  requirements: "React, TS",
  skills: ["React", "TypeScript"],
  source_url: "https://example.com/job",
  source_platform: "manual_text",
  parse_status: "success",
  jd_status: "full_jd",
  extraction_status: "success",
  error_reason: null,
  should_score_similarity: true,
  embedding_similarity: 0.85,
  skill_overlap_score: 0.90,
  location_match_score: 1.0,
  level_match_score: 0.75,
  base_score: 0.85,
  jd_confidence_multiplier: 1.0,
  final_score: 0.85,
  final_score_percent: 85.0,
  status: "pending_review",
  input_tokens: 100,
  output_tokens: 50,
  estimated_cost_usd: 0.003,
  extraction_time_ms: 1200,
  discovered_at: "2026-06-30T10:00:00Z",
  created_at: "2026-06-30T10:00:00Z",
  updated_at: "2026-06-30T10:00:00Z"
};

const mockNullScoreJob: Job = {
  ...mockScorableJob,
  id: "job-2",
  embedding_similarity: null,
  skill_overlap_score: null,
  location_match_score: null,
  level_match_score: null,
  base_score: null,
  jd_confidence_multiplier: null,
  final_score: null,
  final_score_percent: null,
};

const mockNonScorableJob: Job = {
  ...mockScorableJob,
  id: "job-3",
  should_score_similarity: false,
};

const mockErroredJob: Job = {
  ...mockScorableJob,
  id: "job-4",
  error_reason: "Failed to extract required skills from JD.",
};

describe("JobCard and ScoreBreakdown components", () => {
  it("should render job details correctly on the card", () => {
    render(<JobCard job={mockScorableJob} />);

    expect(screen.getByText("React Developer")).toBeInTheDocument();
    expect(screen.getByText("Tech Corp")).toBeInTheDocument();
    expect(screen.getByText("San Francisco, CA")).toBeInTheDocument();
    expect(screen.getByText("Remote")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("Source: Manual Text")).toBeInTheDocument();
    expect(screen.getByText("JD: Full Jd")).toBeInTheDocument();
    expect(screen.getByText("Status: Pending Review")).toBeInTheDocument();
  });

  it("should handle null score fields and show Not Scored", () => {
    render(<JobCard job={mockNullScoreJob} />);

    // Match Score badge should show "Not scored"
    expect(screen.getByText("Not scored")).toBeInTheDocument();

    // Open score breakdown
    const toggleBtn = screen.getByRole("button", { name: /breakdown/i });
    fireEvent.click(toggleBtn);

    // Score factors in breakdown should show "Not scored"
    expect(screen.getByText("Semantic Similarity")).toBeInTheDocument();
    const notScoredElements = screen.getAllByText("Not scored");
    // 1 for main badge, 6 inside breakdown factors (Similarity, Overlap, Location, Level, Confidence, Final)
    expect(notScoredElements.length).toBe(7);
  });

  it("should show Not Scored for all components if should_score_similarity is false", () => {
    render(<JobCard job={mockNonScorableJob} />);

    // Main badge shows Not scored
    expect(screen.getByText("Not scored")).toBeInTheDocument();

    // Open breakdown
    const toggleBtn = screen.getByRole("button", { name: /breakdown/i });
    fireEvent.click(toggleBtn);

    // Even though backend matches have values (e.g. 0.85),
    // they must be displayed as "Not scored" because should_score_similarity is false
    const notScoredElements = screen.getAllByText("Not scored");
    expect(notScoredElements.length).toBe(7);
  });

  it("should display the job error_reason when present", () => {
    const { rerender } = render(<JobCard job={mockScorableJob} />);
    
    // No error reason should be rendered initially
    expect(screen.queryByText(/Failed to extract required skills/i)).not.toBeInTheDocument();

    // Render job with error
    rerender(<JobCard job={mockErroredJob} />);
    expect(screen.getByText("Failed to extract required skills from JD.")).toBeInTheDocument();
  });

  it("should toggle the score breakdown when clicking the breakdown button", () => {
    render(<JobCard job={mockScorableJob} />);

    // Breakdown is hidden initially
    expect(screen.queryByText("Semantic Similarity")).not.toBeInTheDocument();

    // Click to open
    const toggleBtn = screen.getByRole("button", { name: /breakdown/i });
    fireEvent.click(toggleBtn);
    expect(screen.getByText("Semantic Similarity")).toBeInTheDocument();
    expect(screen.getAllByText("85%").length).toBe(3); // main score, semantic similarity, and final score in breakdown are all 85%
    expect(screen.getByText("90%")).toBeInTheDocument(); // skill overlap is 90%
    expect(screen.getAllByText("100%").length).toBe(2); // location & jd confidence are 100%
    expect(screen.getByText("75%")).toBeInTheDocument(); // level match is 75%

    // Click to close
    fireEvent.click(toggleBtn);
    expect(screen.queryByText("Semantic Similarity")).not.toBeInTheDocument();
  });

  it("should render action buttons when status is pending_review and handlers are provided", () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <JobCard 
        job={mockScorableJob} 
        onApprove={onApprove} 
        onReject={onReject} 
      />
    );

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    const rejectBtn = screen.getByRole("button", { name: /reject/i });

    expect(approveBtn).toBeInTheDocument();
    expect(rejectBtn).toBeInTheDocument();

    fireEvent.click(approveBtn);
    expect(onApprove).toHaveBeenCalledWith("job-1");

    fireEvent.click(rejectBtn);
    expect(onReject).toHaveBeenCalledWith("job-1");
  });

  it("omits absent job fields instead of rendering placeholder values", () => {
    render(<JobCard job={{ ...mockScorableJob, title: null, company: null, source_platform: null }} />);
    expect(screen.queryByText("Untitled Position")).not.toBeInTheDocument();
    expect(screen.queryByText("Unknown Company")).not.toBeInTheDocument();
    expect(screen.queryByText("Unknown")).not.toBeInTheDocument();
  });

  it("should disable action buttons when isActionLoading is true", () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();

    render(
      <JobCard 
        job={mockScorableJob} 
        onApprove={onApprove} 
        onReject={onReject} 
        isActionLoading={true}
      />
    );

    const approveBtn = screen.getByRole("button", { name: /approve/i });
    const rejectBtn = screen.getByRole("button", { name: /reject/i });

    expect(approveBtn).toBeDisabled();
    expect(rejectBtn).toBeDisabled();
  });
});
