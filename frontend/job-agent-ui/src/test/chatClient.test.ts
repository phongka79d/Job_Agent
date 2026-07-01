import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import { createConversation, listConversationMessages, sendChatMessage } from "../api/chatClient";

const postSpy = vi.spyOn(apiClient, "post");
const getSpy = vi.spyOn(apiClient, "get");

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
});
