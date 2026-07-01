import type { AgentToolCall } from "../../types/chat";

interface ToolCallCardProps {
  toolCall: AgentToolCall;
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  return (
    <article className={`tool-call-card tool-call-${toolCall.status}`}>
      <div className="tool-call-header">
        <strong>{toolCall.tool_name}</strong>
        <span>{toolCall.status}</span>
      </div>
      <p>{toolCall.input_summary}</p>
      {toolCall.result_summary ? <p>{toolCall.result_summary}</p> : null}
      {toolCall.error_message ? <p className="error-text">{toolCall.error_message}</p> : null}
    </article>
  );
}
