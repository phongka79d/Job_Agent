import React, { useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { createRoleProfile, ApiClientError } from "../../api/client";
import type { RoleProfile, RoleProfileCreateRequest } from "../../types/api";

interface RoleProfileFormProps {
  onCreated: (profile: RoleProfile) => Promise<void> | void;
  onCancel: () => void;
}

export default function RoleProfileForm({ onCreated, onCancel }: RoleProfileFormProps) {
  const [targetRole, setTargetRole] = useState("");
  const [level, setLevel] = useState("");
  const [location, setLocation] = useState("");
  const [acceptRemote, setAcceptRemote] = useState(false);
  const [skillsInput, setSkillsInput] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!targetRole.trim()) {
      setFormError("Target role is required");
      return;
    }

    setIsSubmitting(true);

    const skills = skillsInput
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);

    const payload: RoleProfileCreateRequest = {
      target_role: targetRole.trim(),
      level: level.trim() || null,
      location: location.trim() || null,
      accept_remote: acceptRemote,
      skills: skills.length > 0 ? skills : undefined,
      resume_text: resumeText.trim() || null,
    };

    try {
      const created = await createRoleProfile(payload);
      await onCreated(created);
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

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
            Target Role *
          </label>
          <input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
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
            onClick={onCancel}
            disabled={isSubmitting}
            data-testid="cancel-profile-btn"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
