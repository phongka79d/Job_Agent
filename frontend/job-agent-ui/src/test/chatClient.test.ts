import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import {
  createConversation,
  deleteConversation,
  listAgentToolCalls,
  listConversationMessages,
  listConversations,
  sendChatMessage,
  streamChatResponse,
} from "../api/chatClient";

const postSpy = vi.spyOn(apiClient, "post");
const getSpy = vi.spyOn(apiClient, "get");
const deleteSpy = vi.spyOn(apiClient, "delete");

describe("chatClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a conversation", async () => {
    postSpy.mockResolvedValueOnce({ data: { id: "conv-1", role_profile_id: "profile-1" } });

    const result = await createConversation({ role_profile_id: "profile-1", title: "Session" });

    expect(postSpy).toHaveBeenCalledWith("/api/chat/conversations", {
      role_profile_id: "profile-1",
      title: "Session",
    });
    expect(result.id).toBe("conv-1");
  });

  it("sends a user message", async () => {
    postSpy.mockResolvedValueOnce({ data: { message: { id: "msg-1" }, stream_url: "/stream" } });

    const result = await sendChatMessage("conv-1", { content: "Find jobs" });

    expect(postSpy).toHaveBeenCalledWith("/api/chat/conversations/conv-1/messages", {
      content: "Find jobs",
    });
    expect(result.stream_url).toBe("/stream");
  });

  it("lists conversation messages", async () => {
    getSpy.mockResolvedValueOnce({ data: { messages: [{ id: "msg-1", content: "Hello" }] } });

    const result = await listConversationMessages("conv-1");

    expect(getSpy).toHaveBeenCalledWith("/api/chat/conversations/conv-1/messages");
    expect(result).toEqual([{ id: "msg-1", content: "Hello" }]);
  });

  it("lists conversations for a role profile", async () => {
    getSpy.mockResolvedValueOnce({ data: { conversations: [{ id: "conv-1" }] } });

    const result = await listConversations("profile-1");

    expect(getSpy).toHaveBeenCalledWith("/api/chat/conversations", {
      params: { role_profile_id: "profile-1" },
    });
    expect(result).toEqual([{ id: "conv-1" }]);
  });

  it("deletes a conversation", async () => {
    deleteSpy.mockResolvedValueOnce({ data: undefined });

    await deleteConversation("conv-1");

    expect(deleteSpy).toHaveBeenCalledWith("/api/chat/conversations/conv-1");
  });

  it("lists agent tool calls for a conversation", async () => {
    getSpy.mockResolvedValueOnce({
      data: {
        tool_calls: [
          {
            id: "tool-1",
            conversation_id: "conv-1",
            assistant_message_id: null,
            tool_name: "search_jobs",
            status: "success",
            input_summary: "Tìm kiếm việc làm",
            result_summary: "Đã đưa 2 job vào Review Queue.",
            safe_payload_json: "{\"inserted_jobs\":2,\"review_queue_path\":\"/review\"}",
            error_message: null,
            started_at: null,
            completed_at: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
      },
    });

    const result = await listAgentToolCalls("conv-1");

    expect(getSpy).toHaveBeenCalledWith("/api/chat/conversations/conv-1/tool-calls");
    expect(result[0].tool_name).toBe("search_jobs");
  });

  it("resolves chat stream when message_completed arrives", async () => {
    const instances: Array<{
      url: string;
      close: ReturnType<typeof vi.fn>;
      listeners: Record<string, Array<(event: MessageEvent) => void>>;
    }> = [];
    class FakeEventSource {
      url: string;
      close = vi.fn();
      listeners: Record<string, Array<(event: MessageEvent) => void>> = {};

      constructor(url: string) {
        this.url = url;
        instances.push(this);
      }

      addEventListener(eventName: string, listener: (event: MessageEvent) => void) {
        this.listeners[eventName] = [...(this.listeners[eventName] ?? []), listener];
      }
    }
    vi.stubGlobal("EventSource", FakeEventSource);

    const streamed = streamChatResponse("/api/chat/conversations/conv-1/stream");

    expect(instances[0].url).toBe("http://localhost:8000/api/chat/conversations/conv-1/stream");
    instances[0].listeners.message_completed[0](
      new MessageEvent("message_completed", { data: "{}" })
    );
    await expect(streamed).resolves.toBeUndefined();
    expect(instances[0].close).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
