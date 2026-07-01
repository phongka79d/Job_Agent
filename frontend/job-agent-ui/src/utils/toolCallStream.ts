import type { StreamEventName } from "../api/chatClient";
import type { AgentToolCall, ToolCallStatus } from "../types/chat";

function readString(data: unknown, key: string): string | null {
  if (!data || typeof data !== "object" || !(key in data)) return null;
  const value = (data as Record<string, unknown>)[key];
  return typeof value === "string" ? value : null;
}

function readPayloadJson(data: unknown): string | null {
  if (!data || typeof data !== "object" || !("safe_payload" in data)) return null;
  const payload = (data as Record<string, unknown>).safe_payload;
  if (payload === null || payload === undefined) return null;
  try {
    return JSON.stringify(payload);
  } catch {
    return null;
  }
}

function statusFromEvent(eventName: StreamEventName): ToolCallStatus | null {
  switch (eventName) {
    case "tool_call_started":
      return "running";
    case "tool_call_completed":
      return "success";
    case "tool_call_failed":
      return "failed";
    default:
      return null;
  }
}

export function applyToolCallStreamEvent(
  toolCalls: AgentToolCall[],
  eventName: StreamEventName,
  data: unknown,
  conversationId: string
): AgentToolCall[] {
  const eventStatus = statusFromEvent(eventName);
  if (!eventStatus) return toolCalls;

  const toolCallId = readString(data, "tool_call_id");
  const toolName = readString(data, "tool_name");
  if (!toolCallId || !toolName) return toolCalls;

  const now = new Date().toISOString();
  const existing = toolCalls.find((toolCall) => toolCall.id === toolCallId);
  const status = (readString(data, "status") as ToolCallStatus | null) ?? eventStatus;
  const nextToolCall: AgentToolCall = {
    id: toolCallId,
    conversation_id: existing?.conversation_id ?? conversationId,
    assistant_message_id: existing?.assistant_message_id ?? null,
    tool_name: toolName,
    status,
    input_summary: readString(data, "input_summary") ?? existing?.input_summary ?? "Tool call",
    result_summary: readString(data, "result_summary") ?? existing?.result_summary ?? null,
    safe_payload_json: readPayloadJson(data) ?? existing?.safe_payload_json ?? null,
    error_message: readString(data, "error_message") ?? existing?.error_message ?? null,
    started_at:
      eventName === "tool_call_started" ? now : existing?.started_at ?? null,
    completed_at:
      eventName === "tool_call_completed" || eventName === "tool_call_failed"
        ? now
        : existing?.completed_at ?? null,
    created_at: existing?.created_at ?? now,
    updated_at: now,
  };

  if (existing) {
    return toolCalls.map((toolCall) =>
      toolCall.id === toolCallId ? nextToolCall : toolCall
    );
  }
  return [...toolCalls, nextToolCall];
}
