import { apiClient, normalizeError } from "./client";
import type {
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

export async function streamChatResponse(streamUrl: string): Promise<void> {
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

    eventSource.addEventListener("message_completed", finish);
    eventSource.addEventListener("error", fail);
  });
}
