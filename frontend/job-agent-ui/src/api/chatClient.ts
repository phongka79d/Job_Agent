import { apiClient, normalizeError } from "./client";
import type {
  ChatConversation,
  ChatMessage,
  CreateConversationRequest,
  SendChatMessageRequest,
  SendChatMessageResponse,
} from "../types/chat";

export async function createConversation(request: CreateConversationRequest): Promise<ChatConversation> {
  try {
    const response = await apiClient.post<ChatConversation>("/api/chat/conversations", request);
    return response.data;
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
