import { AlertCircle, FileText, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  listProfileDocuments,
  uploadProfileDocument,
} from "../../api/profileDocumentsClient";
import type { ProfileDocument } from "../../types/profileDocuments";
import ProfileDocumentUpload from "./ProfileDocumentUpload";

interface ProfileDocumentPanelProps {
  activeProfileId: string | null;
}

export default function ProfileDocumentPanel({ activeProfileId }: ProfileDocumentPanelProps) {
  const [documents, setDocuments] = useState<ProfileDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleUpload = async (file: File) => {
    if (!activeProfileId) return;
    setIsUploading(true);
    setError(null);
    try {
      await uploadProfileDocument(activeProfileId, file);
      setDocuments(await listProfileDocuments(activeProfileId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload PDF");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: "16px" }} data-testid="profile-document-panel">
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
          Profile PDFs
        </span>
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
          {documents.map((document) => (
            <div
              key={document.id}
              style={{
                display: "grid",
                gridTemplateColumns: "18px 1fr auto",
                alignItems: "center",
                gap: "8px",
                color: "var(--text-secondary)",
                fontSize: "12px",
              }}
            >
              <FileText size={16} />
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {document.original_filename}
              </span>
              <span style={{ color: document.status === "failed" ? "var(--text-danger)" : "var(--text-muted)" }}>
                {document.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
