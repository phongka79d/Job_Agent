import { Search, Link, FileText } from "lucide-react";

export type IngestionMode = "search" | "url" | "text";

interface IngestionModeTabsProps {
  activeMode: IngestionMode;
  disabled: boolean;
  onChange: (mode: IngestionMode) => void;
}

const modes = [
  { id: "search" as const, label: "Search", icon: Search },
  { id: "url" as const, label: "URL", icon: Link },
  { id: "text" as const, label: "Text", icon: FileText },
];

export default function IngestionModeTabs({ activeMode, disabled, onChange }: IngestionModeTabsProps) {
  return (
    <div
      role="tablist"
      style={{
        display: "flex",
        flexWrap: "wrap",
        borderBottom: "1px solid var(--border-color)",
        marginBottom: "12px",
        gap: "4px",
      }}
    >
      {modes.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          role="tab"
          aria-selected={activeMode === id}
          onClick={() => onChange(id)}
          disabled={disabled}
          style={{
            background: "transparent",
            border: "none",
            borderBottom: activeMode === id ? "2px solid var(--accent)" : "2px solid transparent",
            color: activeMode === id ? "var(--accent)" : "var(--text-muted)",
            padding: "6px 8px",
            cursor: disabled ? "not-allowed" : "pointer",
            fontSize: "12px",
            fontWeight: activeMode === id ? 600 : 400,
            display: "flex",
            alignItems: "center",
            gap: "4px",
            opacity: disabled && activeMode !== id ? 0.5 : 1,
          }}
          data-testid={`tab-${id}`}
        >
          <Icon size={12} /> {label}
        </button>
      ))}
    </div>
  );
}
