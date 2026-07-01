import { apiClient, normalizeError } from "./client";
import type {
  AgentToolCall,
  ChatConversation,
  ChatMessage,
  CreateConversationRequest,
  SendChatMessageRequest,
  SendChatMessageResponse,
} from "../types/chat";

function resolveApiUrl(path: string): string {
  return new URL(path, apiClient.defaults.baseURL).toString();
}

export async function createConversation(request: CreateConversationRequest): Promise<ChatConversation> {
  try {
    const response = await apiClient.post<ChatConversation>("/api/chat/conversations", request);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function listConversations(roleProfileId: string): Promise<ChatConversation[]> {
  try {
    const response = await apiClient.get<{ conversations: ChatConversation[] }>(
      "/api/chat/conversations",
      {
        params: { role_profile_id: roleProfileId },
      }
    );
    return response.data.conversations;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function listConversationMessages(conversationId: string): Promise<ChatMessage[]> {
  try {
    const response = await apiClient.get<{ messages: ChatMessage[] }>(
      `/api/chat/conversations/${conversationId}/messages`
    );
    return response.data.messages;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function listAgentToolCalls(conversationId: string): Promise<AgentToolCall[]> {
  try {
    const response = await apiClient.get<{ tool_calls: AgentToolCall[] }>(
      `/api/chat/conversations/${conversationId}/tool-calls`
    );
    return response.data.tool_calls;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function deleteConversation(conversationId: string): Promise<void> {
  try {
    await apiClient.delete(`/api/chat/conversations/${conversationId}`);
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function sendChatMessage(
  conversationId: string,
  request: SendChatMessageRequest
): Promise<SendChatMessageResponse> {
  try {
    const response = await apiClient.post<SendChatMessageResponse>(
      `/api/chat/conversations/${conversationId}/messages`,
      request
    );
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

const streamEventNames = [
  "message_started",
  "tool_call_started",
  "tool_call_completed",
  "tool_call_failed",
  "tool_call_progress",
  "assistant_delta",
  "message_completed",
] as const;

export type StreamEventName = (typeof streamEventNames)[number];

export interface StreamEvent {
  event: StreamEventName;
  data: unknown;
}

function parseStreamPayload(data: string): unknown {
  try {
    return data ? JSON.parse(data) : null;
  } catch {
    return data;
  }
}

export async function streamChatResponse(
  streamUrl: string,
  onEvent?: (event: StreamEvent) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(resolveApiUrl(streamUrl));
    let settled = false;

    const finish = () => {
      if (settled) return;
      settled = true;
      eventSource.close();
      resolve();
    };

    const fail = () => {
      if (settled) return;
      settled = true;
      eventSource.close();
      reject(new Error("Chat response stream failed"));
    };

    streamEventNames.forEach((eventName) => {
      eventSource.addEventListener(eventName, (e) => {
        const payload = parseStreamPayload(e.data);

        if (onEvent) {
          onEvent({ event: eventName, data: payload });
        }

        if (eventName === "message_completed") {
          finish();
        }
      });
    });

    eventSource.addEventListener("error", fail);
  });
}
