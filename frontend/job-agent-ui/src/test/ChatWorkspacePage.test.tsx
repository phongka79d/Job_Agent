import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useOutletContext } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createConversation,
  deleteConversation,
  listAgentToolCalls,
  listConversationMessages,
  listConversations,
  sendChatMessage,
  streamChatResponse,
} from "../api/chatClient";
import ChatWorkspacePage from "../pages/ChatWorkspacePage";
import type { AgentToolCall, ChatConversation, ChatMessage } from "../types/chat";

vi.mock("../api/chatClient", () => ({
  createConversation: vi.fn(),
  deleteConversation: vi.fn(),
  listAgentToolCalls: vi.fn(),
  listConversationMessages: vi.fn(),
  listConversations: vi.fn(),
  sendChatMessage: vi.fn(),
  streamChatResponse: vi.fn(),
}));

const navigate = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
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

const existingConversation: ChatConversation = {
  id: "conv-existing",
  role_profile_id: "profile-1",
  title: "Existing chat",
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const searchToolCall: AgentToolCall = {
  id: "tool-1",
  conversation_id: "conv-1",
  assistant_message_id: null,
  tool_name: "search_jobs",
  status: "success",
  input_summary: "T\u00ecm ki\u1ebfm vi\u1ec7c l\u00e0m: AI Engineer Intern",
  result_summary: "\u0110\u00e3 \u0111\u01b0a 2 job v\u00e0o Review Queue.",
  safe_payload_json: "{\"inserted_jobs\":2,\"review_queue_path\":\"/review\"}",
  error_message: null,
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:01Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:01Z",
};

describe("ChatWorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listConversations).mockResolvedValue([]);
    vi.mocked(listAgentToolCalls).mockResolvedValue([]);
    vi.mocked(streamChatResponse).mockResolvedValue();
    vi.mocked(deleteConversation).mockResolvedValue();
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
      });
      expect(sendChatMessage).toHaveBeenCalledWith("conv-1", { content: "Find jobs" });
      expect(streamChatResponse).toHaveBeenCalledWith("/stream");
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
      expect(streamChatResponse).toHaveBeenCalledTimes(1);
      expect(listConversationMessages).toHaveBeenCalledTimes(1);
    });
  });

  it("renders search tool calls and navigates to review queue after successful search", async () => {
    vi.mocked(useOutletContext).mockReturnValue({
      activeProfileId: "profile-1",
      triggerMetricsRefresh: vi.fn(),
    });
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
        content: "B\u1eaft \u0111\u1ea7u t\u00ecm vi\u1ec7c AI Engineer Intern",
        token_count: null,
        metadata_json: null,
        created_at: "2026-01-01T00:00:00Z",
      },
      stream_url: "/stream",
    });
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);
    vi.mocked(listAgentToolCalls).mockResolvedValue([searchToolCall]);

    render(<ChatWorkspacePage />);

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "B\u1eaft \u0111\u1ea7u t\u00ecm vi\u1ec7c AI Engineer Intern" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(listAgentToolCalls).toHaveBeenCalledWith("conv-1");
      expect(screen.getByText("search_jobs")).toBeInTheDocument();
      expect(screen.getByText("\u0110\u00e3 \u0111\u01b0a 2 job v\u00e0o Review Queue.")).toBeInTheDocument();
      expect(navigate).toHaveBeenCalledWith("/review");
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

  it("loads chat history and selecting a conversation loads its messages", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(listConversations).mockResolvedValue([existingConversation]);
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);

    render(<ChatWorkspacePage />);

    await waitFor(() => {
      expect(listConversations).toHaveBeenCalledWith("profile-1");
      expect(screen.getByRole("option", { name: "Existing chat" })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Chat history"), { target: { value: "conv-existing" } });

    await waitFor(() => {
      expect(listConversationMessages).toHaveBeenCalledWith("conv-existing");
      expect(screen.getByText("I found several roles to review.")).toBeInTheDocument();
    });
  });

  it("deletes the active conversation and clears messages", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(listConversations)
      .mockResolvedValueOnce([existingConversation])
      .mockResolvedValueOnce([]);
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);

    render(<ChatWorkspacePage />);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Existing chat" })).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText("Chat history"), { target: { value: "conv-existing" } });
    await waitFor(() => {
      expect(screen.getByText("I found several roles to review.")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Delete current chat" }));

    await waitFor(() => {
      expect(deleteConversation).toHaveBeenCalledWith("conv-existing");
      expect(screen.queryByText("I found several roles to review.")).not.toBeInTheDocument();
    });
  });
});
