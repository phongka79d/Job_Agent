import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useOutletContext } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createConversation,
  listConversationMessages,
  sendChatMessage,
} from "../api/chatClient";
import ChatWorkspacePage from "../pages/ChatWorkspacePage";
import type { ChatMessage } from "../types/chat";

vi.mock("../api/chatClient", () => ({
  createConversation: vi.fn(),
  listConversationMessages: vi.fn(),
  sendChatMessage: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useOutletContext: vi.fn(),
}));

const assistantMessage: ChatMessage = {
  id: "msg-2",
  conversation_id: "conv-1",
  role: "assistant",
  content: "I found several roles to review.",
  token_count: null,
  metadata_json: null,
  created_at: "2026-01-01T00:00:00Z",
};

describe("ChatWorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("disables message sending until a role profile is active", () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: null });

    render(<ChatWorkspacePage />);

    expect(screen.getByLabelText("Message")).toBeDisabled();
    expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
  });

  it("creates a conversation, sends the message, and renders refreshed messages", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(createConversation).mockResolvedValue({
      id: "conv-1",
      role_profile_id: "profile-1",
      title: "Job agent session",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    vi.mocked(sendChatMessage).mockResolvedValue({
      message: {
        id: "msg-1",
        conversation_id: "conv-1",
        role: "user",
        content: "Find jobs",
        token_count: null,
        metadata_json: null,
        created_at: "2026-01-01T00:00:00Z",
      },
      stream_url: "/stream",
    });
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);

    render(<ChatWorkspacePage />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(createConversation).toHaveBeenCalledWith({
        role_profile_id: "profile-1",
        title: "Job agent session",
      });
      expect(sendChatMessage).toHaveBeenCalledWith("conv-1", { content: "Find jobs" });
      expect(listConversationMessages).toHaveBeenCalledWith("conv-1");
      expect(screen.getByText("I found several roles to review.")).toBeInTheDocument();
    });
  });
});
