import { Search, Loader2 } from "lucide-react";

interface SearchIngestionFormProps {
  value: string;
  disabled: boolean;
  isInFlight: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}

export default function SearchIngestionForm(props: SearchIngestionFormProps) {
  return (
    <form className="ingestion-form" onSubmit={props.onSubmit} data-testid="form-search">
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <label htmlFor="public-job-query">Public job search query</label>
        <input
          id="public-job-query"
          type="text"
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
          data-testid="input-search-query"
        />
      </div>
      <button
        type="submit"
        className="btn-primary"
        style={{ width: "100%", justifyContent: "center", fontSize: "13px" }}
        disabled={props.disabled || !props.value.trim()}
        data-testid="btn-search-submit"
      >
        {props.isInFlight ? <Loader2 aria-label="Searching" size={14} /> : <Search size={14} />}
        <span>{props.isInFlight ? "Searching" : "Search jobs"}</span>
      </button>
    </form>
  );
}
