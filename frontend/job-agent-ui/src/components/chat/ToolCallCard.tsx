import { CheckCircle, ChevronDown, Clock, Loader2, XCircle } from "lucide-react";
import type { AgentToolCall } from "../../types/chat";
import { getToolCallPresentation } from "../../utils/toolCallPresentation";

interface ToolCallCardProps {
  toolCall: AgentToolCall;
}

function statusIcon(status: AgentToolCall["status"]) {
  switch (status) {
    case "running":
      return <Loader2 size={14} className="animate-spin" />;
    case "success":
      return <CheckCircle size={14} />;
    case "failed":
      return <XCircle size={14} />;
    default:
      return <Clock size={14} />;
  }
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const { label, statusLabel } = getToolCallPresentation(
    toolCall.tool_name,
    toolCall.status,
  );
  const relevantTimestamp =
    toolCall.completed_at ?? toolCall.started_at ?? toolCall.created_at;
  const relevantDate = new Date(relevantTimestamp);
  const hasValidTimestamp = !Number.isNaN(relevantDate.getTime());
  const startedAt = toolCall.started_at ? new Date(toolCall.started_at) : null;
  const completedAt = toolCall.completed_at ? new Date(toolCall.completed_at) : null;
  const durationMs =
    startedAt && completedAt ? completedAt.getTime() - startedAt.getTime() : null;
  const duration =
    durationMs !== null && Number.isFinite(durationMs) && durationMs >= 0
      ? durationMs < 1000
        ? "<1s"
        : `${Math.round(durationMs / 1000)}s`
      : null;
  const inputSummary = toolCall.input_summary.trim();

  return (
    <article className={`tool-call-card tool-call-${toolCall.status}`}>
      <details className="tool-call-details">
        <summary
          className="tool-call-summary"
          aria-label={`${label}. ${statusLabel}. Show details`}
        >
          <span className="tool-call-primary">
            <span className="tool-call-status-icon" aria-hidden="true">
              {statusIcon(toolCall.status)}
            </span>
            <strong className="tool-call-label">{label}</strong>
          </span>
          <span className="tool-call-meta">
            <span className="tool-call-status">{statusLabel}</span>
            {hasValidTimestamp ? (
              <time className="tool-call-time" dateTime={relevantTimestamp}>
                {new Intl.DateTimeFormat(undefined, {
                  hour: "2-digit",
                  minute: "2-digit",
                }).format(relevantDate)}
              </time>
            ) : null}
            <ChevronDown
              className="tool-call-chevron"
              size={16}
              aria-hidden="true"
            />
          </span>
        </summary>
        <div className="tool-call-details-body">
          {inputSummary ? (
            <>
              <span className="tool-call-detail-label">Request</span>
              <span className="tool-call-detail-value">{inputSummary}</span>
            </>
          ) : null}
          {toolCall.result_summary ? (
            <>
              <span className="tool-call-detail-label">Result</span>
              <span className="tool-call-detail-value">{toolCall.result_summary}</span>
            </>
          ) : null}
          {toolCall.error_message ? (
            <>
              <span className="tool-call-detail-label">Error</span>
              <span className="tool-call-detail-value error-text">
                {toolCall.error_message}
              </span>
            </>
          ) : null}
          {duration ? (
            <>
              <span className="tool-call-detail-label">Duration</span>
              <span className="tool-call-detail-value tool-call-duration">{duration}</span>
            </>
          ) : null}
          <span className="tool-call-detail-label">Technical name</span>
          <code className="tool-call-detail-value">{toolCall.tool_name}</code>
        </div>
      </details>
    </article>
  );
}
