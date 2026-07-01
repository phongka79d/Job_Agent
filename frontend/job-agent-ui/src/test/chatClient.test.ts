import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import { createConversation, sendChatMessage } from "../api/chatClient";

const postSpy = vi.spyOn(apiClient, "post");

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
});
