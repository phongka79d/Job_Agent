import { Link, Loader2 } from "lucide-react";

interface UrlIngestionFormProps {
  value: string;
  disabled: boolean;
  isInFlight: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}

export default function UrlIngestionForm(props: UrlIngestionFormProps) {
  return (
    <form className="ingestion-form" onSubmit={props.onSubmit} data-testid="form-url">
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <label htmlFor="job-source-url">Job posting URL</label>
        <input
          id="job-source-url"
          type="url"
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
            opacity: props.disabled ? 0.6 : 1,
          }}
          required
          data-testid="input-url"
        />
      </div>
      <button
        type="submit"
        className="btn-primary"
        style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
        disabled={props.disabled || !props.value.trim()}
        data-testid="btn-url-submit"
      >
        {props.isInFlight ? <Loader2 aria-label="Parsing" size={14} /> : <Link size={14} />}
        <span>{props.isInFlight ? "Parsing..." : "Parse URL"}</span>
      </button>
    </form>
  );
}
