import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ActiveProfileSummary from "../components/workspace/ActiveProfileSummary";
import type { RoleProfile } from "../types/api";

const profile: RoleProfile = {
  id: "profile-api",
  target_role: "Platform Engineer",
  level: "Senior",
  location: "Da Nang",
  accept_remote: true,
  skills: ["Go", "Kubernetes"],
  resume_text: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

describe("ActiveProfileSummary", () => {
  it("renders only fields supplied by the active profile", () => {
    render(<ActiveProfileSummary profile={profile} />);
    expect(screen.getByText("Platform Engineer")).toBeInTheDocument();
    expect(screen.getByText("Senior")).toBeInTheDocument();
    expect(screen.getByText("Da Nang")).toBeInTheDocument();
    expect(screen.getByText("Go")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
  });

  it("renders a truthful empty state without sample profile data", () => {
    render(<ActiveProfileSummary profile={null} />);
    expect(screen.getByText("Select a role profile.")).toBeInTheDocument();
    expect(screen.queryByText("AI Engineer Intern")).not.toBeInTheDocument();
  });
});
