import { FileText, Loader2 } from "lucide-react";

interface TextIngestionFormProps {
  value: string;
  disabled: boolean;
  isInFlight: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}

export default function TextIngestionForm(props: TextIngestionFormProps) {
  return (
    <form className="ingestion-form" onSubmit={props.onSubmit} data-testid="form-text">
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <label htmlFor="job-description-text">Job description text</label>
        <textarea
          id="job-description-text"
          value={props.value}
          onChange={(event) => props.onChange(event.target.value)}
          disabled={props.disabled}
          style={{
            padding: "8px 10px",
            background: "var(--bg-canvas)",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-md)",
            color: "var(--text-primary)",
            fontSize: "13px",
            outline: "none",
            resize: "vertical",
            minHeight: "100px",
            fontFamily: "var(--font-sans)",
            opacity: props.disabled ? 0.6 : 1,
          }}
          required
          data-testid="input-text"
        />
      </div>
      <button
        type="submit"
        className="btn-primary"
        style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
        disabled={props.disabled || !props.value.trim()}
        data-testid="btn-text-submit"
      >
        {props.isInFlight ? <Loader2 aria-label="Parsing" size={14} /> : <FileText size={14} />}
        <span>{props.isInFlight ? "Parsing..." : "Parse text"}</span>
      </button>
    </form>
  );
}
