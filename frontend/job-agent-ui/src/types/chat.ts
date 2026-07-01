export interface ChatConversation {
  id: string;
  role_profile_id: string;
  title: string | null;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  token_count: number | null;
  metadata_json: string | null;
  created_at: string;
}

export interface CreateConversationRequest {
  role_profile_id: string;
  title?: string | null;
}

export interface SendChatMessageRequest {
  content: string;
}

export interface SendChatMessageResponse {
  message: ChatMessage;
  stream_url: string;
}
