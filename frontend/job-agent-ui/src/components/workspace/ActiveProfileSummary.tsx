import type { RoleProfile } from "../../types/api";

interface ActiveProfileSummaryProps {
  profile: RoleProfile | null;
}

export default function ActiveProfileSummary({ profile }: ActiveProfileSummaryProps) {
  return (
    <section className="rail-section active-profile-summary">
      <h2 className="rail-section-title">Active profile</h2>
      {!profile ? (
        <p className="empty-copy">Select a role profile.</p>
      ) : (
        <>
          <strong>{profile.target_role}</strong>
          <div className="profile-facts">
            {profile.level ? <span>{profile.level}</span> : null}
            {profile.location ? <span>{profile.location}</span> : null}
            {profile.accept_remote ? <span>Remote</span> : null}
          </div>
          {profile.skills.length > 0 ? (
            <div className="skill-list">
              {profile.skills.map((skill) => <span key={skill}>{skill}</span>)}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
