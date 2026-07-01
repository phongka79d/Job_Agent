import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useOutletContext } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createConversation,
  listAgentToolCalls,
  listConversationMessages,
  sendChatMessage,
  streamChatResponse,
} from "../api/chatClient";
import ChatWorkspacePage from "../pages/ChatWorkspacePage";
import type { AgentToolCall, ChatMessage } from "../types/chat";

vi.mock("../api/chatClient", () => ({
  createConversation: vi.fn(),
  listAgentToolCalls: vi.fn(),
  listConversationMessages: vi.fn(),
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

const searchToolCall: AgentToolCall = {
  id: "tool-1",
  conversation_id: "conv-1",
  assistant_message_id: null,
  tool_name: "search_jobs",
  status: "success",
  input_summary: "Job search: AI Engineer Intern",
  result_summary: "Added 2 jobs to Review Queue.",
  safe_payload_json: "{\"inserted_jobs\":2,\"review_queue_path\":\"/review\"}",
  error_message: null,
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:01Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:01Z",
};

const textExtractionToolCall: AgentToolCall = {
  id: "tool-text-1",
  conversation_id: "conv-1",
  assistant_message_id: null,
  tool_name: "extract_job_from_text",
  status: "success",
  input_summary: "Pasted job text, 280 characters",
  result_summary: "Added 1 job to Review Queue.",
  safe_payload_json: "{\"inserted_jobs\":1,\"review_queue_path\":\"/review\"}",
  error_message: null,
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:01Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:01Z",
};

describe("ChatWorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listAgentToolCalls).mockResolvedValue([]);
    vi.mocked(streamChatResponse).mockResolvedValue();
  });

  const defaultContextOverride = {
    activeConversationId: null,
    onConversationCreated: vi.fn(),
    onMessageSent: vi.fn(),
    isSendingGlobal: false,
    setIsSendingGlobal: vi.fn(),
  };

  it("disables message sending until a role profile is active", () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: null });

    render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

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

    render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(createConversation).toHaveBeenCalledWith({
        role_profile_id: "profile-1",
      });
      expect(sendChatMessage).toHaveBeenCalledWith("conv-1", { content: "Find jobs" });
      expect(streamChatResponse).toHaveBeenCalledWith("/stream", expect.any(Function));
      expect(listConversationMessages).toHaveBeenCalledWith("conv-1");
      expect(screen.getByText("I found several roles to review.")).toBeInTheDocument();
    });
  });

  it("keeps the draft and shows an error when sending fails", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(createConversation).mockRejectedValue(new Error("Chat service unavailable"));

    render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

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

    let isSendingGlobal = false;
    const setIsSendingGlobal = vi.fn((val) => {
      isSendingGlobal = val;
    });

    const { rerender } = render(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          isSendingGlobal,
          setIsSendingGlobal,
        }}
      />
    );

    const messageInput = screen.getByLabelText("Message");
    fireEvent.change(messageInput, { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    // Rerender with isSendingGlobal: true to simulate state updates
    rerender(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          isSendingGlobal: true,
          setIsSendingGlobal,
        }}
      />
    );

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

    // Rerender back to normal state
    rerender(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          isSendingGlobal: false,
          setIsSendingGlobal,
        }}
      />
    );

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
        content: "Start searching for AI Engineer Intern jobs",
        token_count: null,
        metadata_json: null,
        created_at: "2026-01-01T00:00:00Z",
      },
      stream_url: "/stream",
    });
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);
    vi.mocked(listAgentToolCalls).mockResolvedValue([searchToolCall]);

    render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Start searching for AI Engineer Intern jobs" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(listAgentToolCalls).toHaveBeenCalledWith("conv-1");
      expect(screen.getByText("search_jobs")).toBeInTheDocument();
      expect(screen.getByText("Added 2 jobs to Review Queue.")).toBeInTheDocument();
      expect(navigate).toHaveBeenCalledWith("/review");
    });
  });

  it("navigates to review queue after pasted job text extraction succeeds", async () => {
    vi.mocked(useOutletContext).mockReturnValue({
      activeProfileId: "profile-1",
      triggerMetricsRefresh: vi.fn(),
    });
    vi.mocked(createConversation).mockResolvedValue({
      id: "conv-1",
      role_profile_id: "profile-1",
      title: "Job paste session",
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    vi.mocked(sendChatMessage).mockResolvedValue({
      message: {
        id: "msg-1",
        conversation_id: "conv-1",
        role: "user",
        content: "Senior AI Engineer\nResponsibilities: build AI systems.",
        token_count: null,
        metadata_json: null,
        created_at: "2026-01-01T00:00:00Z",
      },
      stream_url: "/stream",
    });
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);
    vi.mocked(listAgentToolCalls).mockResolvedValue([textExtractionToolCall]);

    render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "Senior AI Engineer\nResponsibilities: build AI systems." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(screen.getByText("extract_job_from_text")).toBeInTheDocument();
      expect(screen.getByText("Added 1 job to Review Queue.")).toBeInTheDocument();
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

    const { rerender } = render(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Find jobs" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(createConversation).toHaveBeenCalledWith({
        role_profile_id: "profile-1",
      });
    });

    activeProfileId = "profile-2";
    rerender(<ChatWorkspacePage contextOverride={defaultContextOverride} />);
    activeProfileId = "profile-1";
    rerender(<ChatWorkspacePage contextOverride={defaultContextOverride} />);

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

  it("loads messages when activeConversationId is provided", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);

    const { rerender } = render(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          activeConversationId: null,
        }}
      />
    );

    expect(screen.queryByText("I found several roles to review.")).not.toBeInTheDocument();

    // Rerender with activeConversationId
    rerender(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          activeConversationId: "conv-existing",
        }}
      />
    );

    await waitFor(() => {
      expect(listConversationMessages).toHaveBeenCalledWith("conv-existing");
      expect(screen.getByText("I found several roles to review.")).toBeInTheDocument();
    });
  });

  it("clears messages when activeConversationId becomes null", async () => {
    vi.mocked(useOutletContext).mockReturnValue({ activeProfileId: "profile-1" });
    vi.mocked(listConversationMessages).mockResolvedValue([assistantMessage]);

    const { rerender } = render(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          activeConversationId: "conv-existing",
        }}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("I found several roles to review.")).toBeInTheDocument();
    });

    // Rerender with null activeConversationId
    rerender(
      <ChatWorkspacePage
        contextOverride={{
          ...defaultContextOverride,
          activeConversationId: null,
        }}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText("I found several roles to review.")).not.toBeInTheDocument();
    });
  });
});
