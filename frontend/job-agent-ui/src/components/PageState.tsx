import { Loader2, AlertCircle } from "lucide-react";

interface PageStateProps {
  kind: "loading" | "empty" | "error";
  children?: React.ReactNode;
}

export default function PageState({ kind, children }: PageStateProps) {
  return (
    <div className={`page-state page-state-${kind}`} role={kind === "error" ? "alert" : undefined}>
      {kind === "loading" ? <Loader2 aria-label="Loading" className="animate-spin" /> : null}
      {kind === "error" ? <AlertCircle aria-hidden="true" /> : null}
      {children}
    </div>
  );
}
