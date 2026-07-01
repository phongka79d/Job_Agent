import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react";
import type { AgentToolCall } from "../../types/chat";

interface ToolCallCardProps {
  toolCall: AgentToolCall;
}

function statusIcon(status: string) {
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
  return (
    <article className={`tool-call-card tool-call-${toolCall.status}`}>
      <div className="tool-call-header">
        {statusIcon(toolCall.status)}
        <strong>{toolCall.tool_name}</strong>
        <span>{toolCall.status}</span>
      </div>
      <p>{toolCall.input_summary}</p>
      {toolCall.result_summary ? <p>{toolCall.result_summary}</p> : null}
      {toolCall.error_message ? <p className="error-text">{toolCall.error_message}</p> : null}
    </article>
  );
}
