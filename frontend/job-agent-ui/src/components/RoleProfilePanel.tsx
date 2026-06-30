import React, { useState, useEffect } from "react";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import { listRoleProfiles, createRoleProfile, ApiClientError } from "../api/client";
import type { RoleProfile, RoleProfileCreateRequest } from "../types/api";

interface RoleProfilePanelProps {
  activeProfile: RoleProfile | null;
  onProfileChange: (profile: RoleProfile) => void;
}

export default function RoleProfilePanel({
  activeProfile,
  onProfileChange,
}: RoleProfilePanelProps) {
  const [profiles, setProfiles] = useState<RoleProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Form State
  const [targetRole, setTargetRole] = useState("");
  const [level, setLevel] = useState("");
  const [location, setLocation] = useState("");
  const [acceptRemote, setAcceptRemote] = useState(false);
  const [skillsInput, setSkillsInput] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Fetch profiles on mount
  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listRoleProfiles();
      setProfiles(response.role_profiles);
      
      // Auto-select first profile if none is active
      if (response.role_profiles.length > 0 && !activeProfile) {
        onProfileChange(response.role_profiles[0]);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to fetch role profiles");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!targetRole.trim()) {
      setFormError("Target role is required");
      return;
    }

    setIsSubmitting(true);

    // Split skills by comma and trim whitespace, filter out empty strings
    const skills = skillsInput
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const payload: RoleProfileCreateRequest = {
      target_role: targetRole.trim(),
      level: level.trim() || null,
      location: location.trim() || null,
      accept_remote: acceptRemote,
      skills: skills.length > 0 ? skills : undefined,
      resume_text: resumeText.trim() || null,
    };

    try {
      const newProfile = await createRoleProfile(payload);
      // Set the returned backend ID as active
      onProfileChange(newProfile);
      // Refresh the profiles list
      await fetchProfiles();
      
      // Reset form and close it
      setTargetRole("");
      setLevel("");
      setLocation("");
      setAcceptRemote(false);
      setSkillsInput("");
      setResumeText("");
      setShowForm(false);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setFormError(err.message);
      } else {
        setFormError("Failed to create role profile");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Active profile selection panel */}
      <div className="glass-panel" style={{ padding: "16px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <span
            style={{
              fontSize: "11px",
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              fontWeight: 600,
            }}
          >
            Role Profile
          </span>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="btn-secondary"
              style={{ padding: "4px 8px", fontSize: "12px" }}
              data-testid="create-profile-btn"
            >
              <Plus size={12} /> New
            </button>
          )}
        </div>

        {error && (
          <div
            style={{
              color: "var(--text-danger)",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginBottom: "8px",
            }}
          >
            <AlertCircle size={14} /> {error}
          </div>
        )}

        {isLoading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              color: "var(--text-muted)",
              fontSize: "13px",
              padding: "8px 0",
            }}
          >
            <Loader2 size={16} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
            Loading profiles...
          </div>
        ) : profiles.length === 0 ? (
          <div
            style={{
              color: "var(--text-muted)",
              fontSize: "13px",
              fontStyle: "italic",
              padding: "8px 0",
            }}
            data-testid="empty-profiles-state"
          >
            No profiles found. Create one to begin.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }} data-testid="profiles-list">
            <select
              value={activeProfile?.id || ""}
              onChange={(e) => {
                const found = profiles.find((p) => p.id === e.target.value);
                if (found) onProfileChange(found);
              }}
              style={{
                width: "100%",
                padding: "8px 12px",
                background: "var(--bg-canvas)",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                fontSize: "14px",
                outline: "none",
              }}
              data-testid="profile-select"
            >
              <option value="" disabled>
                Select a profile...
              </option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.target_role} {p.level ? `(${p.level})` : ""}
                </option>
              ))}
            </select>

            {activeProfile && (
              <div
                style={{
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginTop: "8px",
                  borderTop: "1px solid var(--border-color)",
                  paddingTop: "8px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
                data-testid="active-profile-details"
              >
                <div>
                  <strong>Location:</strong> {activeProfile.location || "Any"}
                  {activeProfile.accept_remote && " (Remote)"}
                </div>
                <div>
                  <strong>Skills:</strong>{" "}
                  {activeProfile.skills.length > 0
                    ? activeProfile.skills.join(", ")
                    : "None specified"}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Creation form panel */}
      {showForm && (
        <div className="glass-panel" style={{ padding: "16px" }} data-testid="create-profile-form">
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
            Create Role Profile
          </div>

          <form onSubmit={handleCreateProfile} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                Target Role *
              </label>
              <input
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Senior Frontend Engineer"
                style={{
                  padding: "8px 12px",
                  background: "var(--bg-canvas)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "14px",
                  outline: "none",
                }}
                required
                disabled={isSubmitting}
                data-testid="input-target-role"
              />
            </div>

            <div style={{ display: "flex", gap: "12px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1 }}>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Level</label>
                <input
                  type="text"
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  placeholder="e.g. Senior"
                  style={{
                    padding: "8px 12px",
                    background: "var(--bg-canvas)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--text-primary)",
                    fontSize: "14px",
                    outline: "none",
                  }}
                  disabled={isSubmitting}
                  data-testid="input-level"
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1 }}>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Location</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. New York, NY"
                  style={{
                    padding: "8px 12px",
                    background: "var(--bg-canvas)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--text-primary)",
                    fontSize: "14px",
                    outline: "none",
                  }}
                  disabled={isSubmitting}
                  data-testid="input-location"
                />
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "4px 0" }}>
              <input
                type="checkbox"
                id="acceptRemote"
                checked={acceptRemote}
                onChange={(e) => setAcceptRemote(e.target.checked)}
                style={{ cursor: "pointer" }}
                disabled={isSubmitting}
                data-testid="input-accept-remote"
              />
              <label
                htmlFor="acceptRemote"
                style={{ fontSize: "13px", color: "var(--text-secondary)", cursor: "pointer" }}
              >
                Accept Remote
              </label>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                Skills (comma-separated)
              </label>
              <input
                type="text"
                value={skillsInput}
                onChange={(e) => setSkillsInput(e.target.value)}
                placeholder="React, TypeScript, CSS"
                style={{
                  padding: "8px 12px",
                  background: "var(--bg-canvas)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "14px",
                  outline: "none",
                }}
                disabled={isSubmitting}
                data-testid="input-skills"
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                Resume / Profile Text
              </label>
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste resume text or candidate bio..."
                style={{
                  padding: "8px 12px",
                  background: "var(--bg-canvas)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-primary)",
                  fontSize: "14px",
                  outline: "none",
                  resize: "vertical",
                  minHeight: "80px",
                  fontFamily: "var(--font-sans)",
                }}
                disabled={isSubmitting}
                data-testid="input-resume"
              />
            </div>

            {formError && (
              <div
                style={{
                  color: "var(--text-danger)",
                  fontSize: "13px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <AlertCircle size={14} /> {formError}
              </div>
            )}

            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <button
                type="submit"
                className="btn-primary"
                style={{ flex: 1, justifyContent: "center" }}
                disabled={isSubmitting}
                data-testid="submit-profile-btn"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                    Creating...
                  </>
                ) : (
                  "Create"
                )}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setTargetRole("");
                  setLevel("");
                  setLocation("");
                  setAcceptRemote(false);
                  setSkillsInput("");
                  setResumeText("");
                  setFormError(null);
                  setShowForm(false);
                }}
                disabled={isSubmitting}
                data-testid="cancel-profile-btn"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
