import React, { useState, useEffect } from "react";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import { listRoleProfiles, ApiClientError } from "../api/client";
import type { RoleProfile } from "../types/api";
import RoleProfileForm from "./profile/RoleProfileForm";

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
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

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

  const handleSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const found = profiles.find((p) => p.id === e.target.value);
    if (found) onProfileChange(found);
  };

  const handleCreated = async (profile: RoleProfile) => {
    onProfileChange(profile);
    await fetchProfiles();
    setShowForm(false);
  };

  return (
    <section className="rail-section role-profile-panel">
      <div className="rail-section-heading">
        <span>Role profiles</span>
        {!showForm && (
          <button
            type="button"
            className="icon-command"
            aria-label="Create profile"
            onClick={() => setShowForm(true)}
            data-testid="create-profile-btn"
          >
            <Plus size={14} />
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
      ) : profiles.length > 0 ? (
        <>
          <select
            value={activeProfile?.id ?? profiles[0].id}
            onChange={handleSelect}
            data-testid="profile-select"
          >
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {[profile.target_role, profile.level].filter(Boolean).join(" - ")}
              </option>
            ))}
          </select>
          {activeProfile ? (
            <div className="active-profile-meta">
              {activeProfile.location ? <span>{activeProfile.location}</span> : null}
              {activeProfile.accept_remote ? <span>Remote</span> : null}
            </div>
          ) : null}
        </>
      ) : (
        <p data-testid="empty-profiles-state">No profiles found.</p>
      )}

      {showForm ? (
        <RoleProfileForm
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      ) : null}
    </section>
  );
}
