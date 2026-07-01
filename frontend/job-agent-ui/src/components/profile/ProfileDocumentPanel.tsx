import { AlertCircle, Download, Eye, FileText, Loader2, Star, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import {
  activateProfileDocumentVersion,
  deleteProfileDocument,
  exportCvDraftToPdf,
  getProfileDocumentDownloadUrl,
  getProfileDocumentFileUrl,
  getProfileDocumentVersionDownloadUrl,
  getProfileDocumentVersionFileUrl,
  listCvDrafts,
  listCvSuggestions,
  listProfileDocumentVersions,
  listProfileDocuments,
  previewCvDraft,
  uploadProfileDocument,
} from "../../api/profileDocumentsClient";
import type { CvDraft, CvDraftPreview, CvImprovementSuggestion, ProfileDocument, ProfileDocumentVersion } from "../../types/profileDocuments";
import ProfileDocumentUpload from "./ProfileDocumentUpload";

interface ProfileDocumentPanelProps {
  activeProfileId: string | null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export default function ProfileDocumentPanel({ activeProfileId }: ProfileDocumentPanelProps) {
  const [documents, setDocuments] = useState<ProfileDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestionsByDocument, setSuggestionsByDocument] = useState<Record<string, CvImprovementSuggestion[]>>({});
  const [draftsByDocument, setDraftsByDocument] = useState<Record<string, CvDraft[]>>({});
  const [draftPreview, setDraftPreview] = useState<CvDraftPreview | null>(null);
  const [versionsByDocument, setVersionsByDocument] = useState<Record<string, ProfileDocumentVersion[]>>({});

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      if (!activeProfileId) {
        setDocuments([]);
        setError(null);
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const nextDocuments = await listProfileDocuments(activeProfileId);
        if (!cancelled) {
          setDocuments(nextDocuments);
          const suggestionEntries = await Promise.all(
            nextDocuments.map(async (document) => [document.id, await listCvSuggestions(activeProfileId, document.id)] as const)
          );
          const draftEntries = await Promise.all(
            nextDocuments.map(async (document) => [document.id, await listCvDrafts(activeProfileId, document.id)] as const)
          );
          const versionEntries = await Promise.all(
            nextDocuments.map(async (document) => [document.id, await listProfileDocumentVersions(activeProfileId, document.id)] as const)
          );
          setSuggestionsByDocument(Object.fromEntries(suggestionEntries));
          setDraftsByDocument(Object.fromEntries(draftEntries));
          setVersionsByDocument(Object.fromEntries(versionEntries));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load profile PDFs");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void refresh();
    return () => {
      cancelled = true;
    };
  }, [activeProfileId]);

  const refreshDocuments = async () => {
    if (!activeProfileId) return;
    const nextDocuments = await listProfileDocuments(activeProfileId);
    setDocuments(nextDocuments);
    const suggestionEntries = await Promise.all(
      nextDocuments.map(async (document) => [document.id, await listCvSuggestions(activeProfileId, document.id)] as const)
    );
    const draftEntries = await Promise.all(
      nextDocuments.map(async (document) => [document.id, await listCvDrafts(activeProfileId, document.id)] as const)
    );
    const versionEntries = await Promise.all(
      nextDocuments.map(async (document) => [document.id, await listProfileDocumentVersions(activeProfileId, document.id)] as const)
    );
    setSuggestionsByDocument(Object.fromEntries(suggestionEntries));
    setDraftsByDocument(Object.fromEntries(draftEntries));
    setVersionsByDocument(Object.fromEntries(versionEntries));
  };

  const handleUpload = async (file: File) => {
    if (!activeProfileId) return;
    setIsUploading(true);
    setError(null);
    try {
      await uploadProfileDocument(activeProfileId, file);
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload PDF");
    } finally {
      setIsUploading(false);
    }
  };

  const handleActivateVersion = async (document: ProfileDocument, versionId: string) => {
    if (!activeProfileId) return;
    setError(null);
    try {
      await activateProfileDocumentVersion(activeProfileId, document.id, versionId);
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set active CV");
    }
  };

  const handleActivate = async (document: ProfileDocument) => {
    if (!document.active_version_id) return;
    await handleActivateVersion(document, document.active_version_id);
  };

  const handleDelete = async (document: ProfileDocument) => {
    if (!activeProfileId) return;
    const clearActive = document.is_active;
    const confirmed = window.confirm(
      clearActive
        ? "Delete the active CV and clear active selection?"
        : "Delete this CV PDF?"
    );
    if (!confirmed) return;
    setError(null);
    try {
      await deleteProfileDocument(activeProfileId, document.id, { clearActive });
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete CV");
    }
  };

  const handleExportDraft = async (document: ProfileDocument, draft: CvDraft) => {
    if (!activeProfileId) return;
    const confirmed = window.confirm("Export this CV draft as a new PDF version? The active CV will not change.");
    if (!confirmed) return;
    setError(null);
    try {
      await exportCvDraftToPdf(activeProfileId, document.id, draft.id, { confirmed: true });
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export CV draft");
    }
  };

  return (
    <section className="rail-section profile-document-panel" data-testid="profile-document-panel">
      <div className="rail-section-heading">
        <span>Profile documents</span>
        <ProfileDocumentUpload
          disabled={!activeProfileId || isUploading}
          isUploading={isUploading}
          onUpload={(file) => void handleUpload(file)}
        />
      </div>

      {error && (
        <div
          role="alert"
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

      {!activeProfileId ? (
        <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          Select a role profile to manage PDFs.
        </div>
      ) : isLoading ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "var(--text-muted)",
            fontSize: "13px",
          }}
        >
          <Loader2 size={16} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
          Loading PDFs...
        </div>
      ) : documents.length === 0 ? (
        <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
          No PDFs uploaded.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {documents.map((document) => {
            const updatedAt = new Intl.DateTimeFormat(undefined, {
              dateStyle: "medium",
              timeStyle: "short",
            }).format(new Date(document.updated_at));

            return (
              <div
                key={document.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "18px 1fr",
                  alignItems: "center",
                  gap: "8px",
                  color: "var(--text-secondary)",
                  fontSize: "12px",
                }}
              >
                <FileText size={16} />
                <div>
                  <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {document.original_filename}
                  </div>
                  <div style={{ display: "flex", gap: "8px", color: "var(--text-muted)", fontSize: "11px" }}>
                    <span style={{ color: document.status === "failed" ? "var(--text-danger)" : undefined }}>
                      {document.status}
                    </span>
                    <span>{formatFileSize(document.file_size_bytes)}</span>
                    <span>{document.chunk_count} chunks</span>
                    <span>{updatedAt}</span>
                  </div>
                  {document.is_active ? (
                    <span className="document-active-badge">Active CV</span>
                  ) : null}
                  <div className="profile-document-actions">
                    <a
                      href={getProfileDocumentFileUrl(activeProfileId!, document.id)}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`View ${document.original_filename}`}
                    >
                      <Eye size={14} /> View
                    </a>
                    <a
                      href={getProfileDocumentDownloadUrl(activeProfileId!, document.id)}
                      aria-label={`Download ${document.original_filename}`}
                    >
                      <Download size={14} /> Download
                    </a>
                    {!document.is_active && document.active_version_id ? (
                      <button
                        type="button"
                        onClick={() => void handleActivate(document)}
                        aria-label={`Set ${document.original_filename} active`}
                      >
                        <Star size={14} /> Set active
                      </button>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => void handleDelete(document)}
                      aria-label={`Delete ${document.original_filename}`}
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                  {(suggestionsByDocument[document.id] ?? []).length > 0 ? (
                    <div className="profile-document-subpanel">
                      <div className="profile-document-subpanel-title">CV suggestions</div>
                      {(suggestionsByDocument[document.id] ?? []).map((suggestion) => (
                        <div key={suggestion.id} className="profile-document-suggestion">
                          <strong>{suggestion.requirement}</strong>
                          <span>{suggestion.proposed_edit}</span>
                          <small>{suggestion.edit_kind} - {suggestion.risk_level}</small>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {(draftsByDocument[document.id] ?? []).length > 0 ? (
                    <div className="profile-document-subpanel">
                      <div className="profile-document-subpanel-title">Draft preview</div>
                      {(draftsByDocument[document.id] ?? []).map((draft) => (
                        <div key={draft.id} style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                          <button
                            type="button"
                            onClick={() => {
                              void previewCvDraft(activeProfileId!, document.id, draft.id).then(setDraftPreview);
                            }}
                          >
                            {draft.title}
                          </button>
                          {draft.status === "draft" ? (
                            <button
                              type="button"
                              onClick={() => void handleExportDraft(document, draft)}
                              aria-label={`Export ${draft.title} PDF`}
                            >
                              <Upload size={14} /> Export PDF
                            </button>
                          ) : null}
                        </div>
                      ))}
                      {draftPreview?.draft_id && (
                        <div className="profile-document-preview">
                          <strong>{draftPreview.title}</strong>
                          {draftPreview.recommendation ? <p>{draftPreview.recommendation}</p> : null}
                          {draftPreview.edits.map((edit) => (
                            <p key={`${draftPreview.draft_id}-${edit.requirement}`}>{edit.proposed_edit}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}
                  <div className="profile-document-subpanel">
                    <div className="profile-document-subpanel-title">Version history</div>
                    {(versionsByDocument[document.id] ?? []).length === 0 ? (
                      <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>No versions yet.</div>
                    ) : (
                      (versionsByDocument[document.id] ?? []).map((version) => (
                        <div key={version.id} className="profile-document-version-row">
                          <div>
                            <strong>{version.display_name}</strong>
                            <small>v{version.version_number} - {version.source_type} - {version.extraction_status}</small>
                          </div>
                          <div className="profile-document-actions">
                            <a
                              href={getProfileDocumentVersionFileUrl(activeProfileId!, document.id, version.id)}
                              target="_blank"
                              rel="noreferrer"
                              aria-label={`View ${version.display_name}`}
                            >
                              <Eye size={14} /> View
                            </a>
                            <a
                              href={getProfileDocumentVersionDownloadUrl(activeProfileId!, document.id, version.id)}
                              aria-label={`Download ${version.display_name}`}
                            >
                              <Download size={14} /> Download
                            </a>
                            {document.active_version_id !== version.id ? (
                              <button
                                type="button"
                                onClick={() => void handleActivateVersion(document, version.id)}
                                aria-label={`Set ${version.display_name} active`}
                              >
                                <Star size={14} /> Set active
                              </button>
                            ) : (
                              <span className="document-active-badge">Active version</span>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
