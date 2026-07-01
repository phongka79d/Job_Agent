import { Loader2, Upload } from "lucide-react";

interface ProfileDocumentUploadProps {
  disabled: boolean;
  isUploading: boolean;
  onUpload: (file: File) => void;
}

export default function ProfileDocumentUpload({
  disabled,
  isUploading,
  onUpload,
}: ProfileDocumentUploadProps) {
  return (
    <label
      className="btn-secondary"
      aria-label="Upload PDF"
      title="Upload PDF"
      style={{
        padding: "4px 8px",
        fontSize: "12px",
        opacity: disabled ? 0.6 : 1,
        pointerEvents: disabled ? "none" : "auto",
      }}
    >
      {isUploading ? (
        <Loader2 size={14} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
      ) : (
        <Upload size={14} />
      )}
      <input
        type="file"
        accept="application/pdf"
        hidden
        disabled={disabled}
        data-testid="profile-document-file-input"
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) {
            onUpload(file);
          }
        }}
      />
    </label>
  );
}
