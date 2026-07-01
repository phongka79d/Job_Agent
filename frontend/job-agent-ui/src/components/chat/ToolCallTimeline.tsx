import type { AgentToolCall } from "../../types/chat";
import ToolCallCard from "./ToolCallCard";

interface ToolCallTimelineProps {
  toolCalls: AgentToolCall[];
}

export default function ToolCallTimeline({ toolCalls }: ToolCallTimelineProps) {
  return (
    <aside className="tool-call-timeline" aria-label="Agent tool calls">
      {toolCalls.map((toolCall) => (
        <ToolCallCard key={toolCall.id} toolCall={toolCall} />
      ))}
    </aside>
  );
}
