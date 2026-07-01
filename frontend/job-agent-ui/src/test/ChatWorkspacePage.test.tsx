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

  it("keeps the draft and shows an error when sending fails", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(createConversation).mockRejectedValue(new Error("Chat service unavailable"));

    render(<ChatWorkspacePage />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Chat service unavailable");
      expect(screen.getByLabelText("Message")).toHaveValue("Find jobs");
    });
  });

  it("prevents a duplicate send while the first conversation is in flight", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    let resolveConversation: (
      value: Awaited<ReturnType<typeof createConversation>>
    ) => void = () => {};
    vi.mocked(createConversation).mockReturnValue(
      new Promise((resolve) => {
        resolveConversation = resolve;
      })
    );
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
    vi.mocked(listConversationMessages).mockResolvedValue([]);

    render(<ChatWorkspacePage />);

    const messageInput = screen.getByLabelText("Message");
    fireEvent.change(messageInput, { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
    });

    fireEvent.submit(messageInput.closest("form") as HTMLFormElement);

    expect(createConversation).toHaveBeenCalledTimes(1);
    expect(sendChatMessage).not.toHaveBeenCalled();

    resolveConversation({
      id: "conv-1",
      role_profile_id: "profile-1",
      title: "Job agent session",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    await waitFor(() => {
      expect(sendChatMessage).toHaveBeenCalledTimes(1);
      expect(listConversationMessages).toHaveBeenCalledTimes(1);
    });
  });

  it("ignores old-profile async completions after the active profile changes", async () => {
    let activeProfileId = "profile-1";
    vi.mocked(useOutletContext).mockImplementation(() => ({ activeProfileId }));
    let resolveConversation: (
      value: Awaited<ReturnType<typeof createConversation>>
    ) => void = () => {};
    let resolveMessages: (value: ChatMessage[]) => void = () => {};
    vi.mocked(createConversation).mockReturnValue(
      new Promise((resolve) => {
        resolveConversation = resolve;
      })
    );
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
    vi.mocked(listConversationMessages).mockReturnValue(
      new Promise((resolve) => {
        resolveMessages = resolve;
      })
    );

    const { rerender } = render(<ChatWorkspacePage />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(createConversation).toHaveBeenCalledWith({
        role_profile_id: "profile-1",
        title: "Job agent session",
      });
    });

    activeProfileId = "profile-2";
    rerender(<ChatWorkspacePage />);
    activeProfileId = "profile-1";
    rerender(<ChatWorkspacePage />);

    resolveConversation({
      id: "conv-1",
      role_profile_id: "profile-1",
      title: "Old session",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    await waitFor(() => {
      expect(listConversationMessages).toHaveBeenCalledWith("conv-1");
    });

    resolveMessages([
      {
        id: "msg-old",
        conversation_id: "conv-1",
        role: "assistant",
        content: "Old profile result",
        token_count: null,
        metadata_json: null,
        created_at: "2026-01-01T00:00:00Z",
      },
    ]);

    await waitFor(() => {
      expect(screen.getByLabelText("Message")).not.toBeDisabled();
    });
    expect(screen.queryByText("Old profile result")).not.toBeInTheDocument();
  });
});
