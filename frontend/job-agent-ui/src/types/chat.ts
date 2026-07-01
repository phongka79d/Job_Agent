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

export type ToolCallStatus = "pending" | "running" | "success" | "failed";

export interface AgentToolCall {
  id: string;
  conversation_id: string;
  assistant_message_id: string | null;
  tool_name: string;
  status: ToolCallStatus;
  input_summary: string;
  result_summary: string | null;
  safe_payload_json: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}
