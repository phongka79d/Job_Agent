import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RoleProfilePanel from "../components/RoleProfilePanel";
import { listRoleProfiles, createRoleProfile } from "../api/client";
import type { RoleProfile } from "../types/api";

// Mock the API client
vi.mock("../api/client", () => {
  return {
    listRoleProfiles: vi.fn(),
    createRoleProfile: vi.fn(),
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

describe("RoleProfilePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch and render existing profiles on startup and auto-select the first one if none is active", async () => {
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });
    const onProfileChange = vi.fn();

    render(
      <RoleProfilePanel activeProfile={null} onProfileChange={onProfileChange} />
    );

    // Should show loading state first
    expect(screen.getByText(/loading profiles/i)).toBeInTheDocument();

    // Wait for the select dropdown to render
    await waitFor(() => {
      expect(screen.queryByText(/loading profiles/i)).not.toBeInTheDocument();
    });

    const select = screen.getByTestId("profile-select") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.options.length).toBe(3); // placeholder + 2 profiles
    expect(select.options[1].text).toBe("Software Engineer (Mid)");
    expect(select.options[2].text).toBe("Data Scientist (Senior)");

    // Verification of automatic selection behavior on startup when activeProfile is null
    expect(onProfileChange).toHaveBeenCalledWith(mockProfiles[0]);
  });

  it("should render an empty state when no profiles exist", async () => {
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: [] });
    const onProfileChange = vi.fn();

    render(
      <RoleProfilePanel activeProfile={null} onProfileChange={onProfileChange} />
    );

    await waitFor(() => {
      expect(screen.getByTestId("empty-profiles-state")).toBeInTheDocument();
    });
    expect(screen.getByText(/no profiles found/i)).toBeInTheDocument();
  });

  it("should toggle the creation form when clicking New and Cancel buttons", async () => {
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });

    render(
      <RoleProfilePanel activeProfile={mockProfiles[0]} onProfileChange={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByTestId("profile-select")).toBeInTheDocument();
    });

    // Form should not be visible initially
    expect(screen.queryByTestId("create-profile-form")).not.toBeInTheDocument();

    // Click "New"
    const newBtn = screen.getByTestId("create-profile-btn");
    fireEvent.click(newBtn);

    // Form should be visible
    expect(screen.getByTestId("create-profile-form")).toBeInTheDocument();

    // Click "Cancel"
    const cancelBtn = screen.getByTestId("cancel-profile-btn");
    fireEvent.click(cancelBtn);

    // Form should be hidden again
    expect(screen.queryByTestId("create-profile-form")).not.toBeInTheDocument();
  });

  it("should call onProfileChange when selecting a different profile", async () => {
    vi.mocked(listRoleProfiles).mockResolvedValue({ role_profiles: mockProfiles });
    const onProfileChange = vi.fn();

    render(
      <RoleProfilePanel activeProfile={mockProfiles[0]} onProfileChange={onProfileChange} />
    );

    await waitFor(() => {
      expect(screen.getByTestId("profile-select")).toBeInTheDocument();
    });

    const select = screen.getByTestId("profile-select");
    fireEvent.change(select, { target: { value: "prof-2" } });

    expect(onProfileChange).toHaveBeenCalledWith(mockProfiles[1]);
  });

  it("should validate and submit the form successfully, trimming inputs and splitting skills", async () => {
    const user = userEvent.setup();
    const onProfileChange = vi.fn();
    const newProfile: RoleProfile = {
      id: "prof-3",
      target_role: "DevOps Engineer",
      level: "Lead",
      location: "Remote",
      accept_remote: true,
      skills: ["Docker", "Kubernetes", "AWS"],
      resume_text: "My resume details",
      created_at: "2026-06-30T12:00:00Z",
      updated_at: "2026-06-30T12:00:00Z",
    };

    vi.mocked(listRoleProfiles)
      .mockResolvedValueOnce({ role_profiles: mockProfiles }) // first fetch
      .mockResolvedValueOnce({ role_profiles: [...mockProfiles, newProfile] }); // after creation fetch

    vi.mocked(createRoleProfile).mockResolvedValue(newProfile);

    render(
      <RoleProfilePanel activeProfile={mockProfiles[0]} onProfileChange={onProfileChange} />
    );

    await waitFor(() => {
      expect(screen.getByTestId("profile-select")).toBeInTheDocument();
    });

    // Open form
    fireEvent.click(screen.getByTestId("create-profile-btn"));

    // Fill the fields
    const targetRoleInput = screen.getByTestId("input-target-role");
    const levelInput = screen.getByTestId("input-level");
    const locationInput = screen.getByTestId("input-location");
    const acceptRemoteCheckbox = screen.getByTestId("input-accept-remote");
    const skillsInput = screen.getByTestId("input-skills");
    const resumeInput = screen.getByTestId("input-resume");

    await user.type(targetRoleInput, " DevOps Engineer ");
    await user.type(levelInput, " Lead ");
    await user.type(locationInput, " Remote ");
    fireEvent.click(acceptRemoteCheckbox);
    await user.type(skillsInput, "Docker , Kubernetes, AWS, ");
    await user.type(resumeInput, "My resume details");

    // Submit
    const submitBtn = screen.getByTestId("submit-profile-btn");
    fireEvent.click(submitBtn);

    // Verify loading and mutation
    await waitFor(() => {
      expect(createRoleProfile).toHaveBeenCalledWith({
        target_role: "DevOps Engineer",
        level: "Lead",
        location: "Remote",
        accept_remote: true,
        skills: ["Docker", "Kubernetes", "AWS"],
        resume_text: "My resume details",
      });
    });

    // Verify it notifies with the new active backend ID and refreshes list
    await waitFor(() => {
      expect(onProfileChange).toHaveBeenCalledWith(newProfile);
      expect(listRoleProfiles).toHaveBeenCalledTimes(2);
    });

    // Form should close after success
    expect(screen.queryByTestId("create-profile-form")).not.toBeInTheDocument();
  });
});
