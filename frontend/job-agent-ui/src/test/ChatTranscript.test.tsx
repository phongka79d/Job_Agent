import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChatTranscript from "../components/chat/ChatTranscript";
import type { ChatMessage, AgentToolCall } from "../types/chat";

const mockMessages: ChatMessage[] = [
  {
    id: "msg-1",
    conversation_id: "conv-1",
    role: "user",
    content: "Find some job",
    token_count: null,
    metadata_json: null,
    created_at: "2026-07-01T00:00:00Z",
  },
  {
    id: "msg-2",
    conversation_id: "conv-1",
    role: "assistant",
    content: "Here are the jobs.",
    token_count: null,
    metadata_json: null,
    created_at: "2026-07-01T00:00:02Z",
  },
];

const mockToolCalls: AgentToolCall[] = [
  {
    id: "call-1",
    conversation_id: "conv-1",
    assistant_message_id: null,
    tool_name: "search_jobs",
    status: "success",
    input_summary: "Searching for jobs",
    result_summary: "Found 5 jobs",
    safe_payload_json: null,
    error_message: null,
    started_at: "2026-07-01T00:00:01Z",
    completed_at: "2026-07-01T00:00:02Z",
    created_at: "2026-07-01T00:00:01Z",
    updated_at: "2026-07-01T00:00:02Z",
  },
];

describe("ChatTranscript", () => {
  it("renders messages and tool calls in chronological order", () => {
    const { container } = render(
      <ChatTranscript messages={mockMessages} toolCalls={mockToolCalls} />
    );

    // Verify all items are rendered
    expect(screen.getByText("Find some job")).toBeInTheDocument();
    expect(screen.getByText("Job search completed")).toBeInTheDocument();
    expect(screen.getByText("search_jobs")).toBeInTheDocument();
    expect(screen.getByText("Here are the jobs.")).toBeInTheDocument();

    // Verify ordering by checking the text content sequence of all child elements
    const articles = container.querySelectorAll("article");
    expect(articles).toHaveLength(3);
    expect(articles[0]).toHaveClass("chat-message-user"); // msg-1 at 00:00:00Z
    expect(articles[1]).toHaveClass("tool-call-success"); // call-1 at 00:00:01Z
    expect(articles[2]).toHaveClass("chat-message-assistant"); // msg-2 at 00:00:02Z
  });

  it("renders simple markdown bolding and bullet list points correctly", () => {
    const markdownMessage: ChatMessage = {
      id: "msg-3",
      conversation_id: "conv-1",
      role: "assistant",
      content: "Here is your profile:\n- **Name**: John Doe\n- **Skills**: Java",
      token_count: null,
      metadata_json: null,
      created_at: "2026-07-01T00:00:03Z",
    };

    render(<ChatTranscript messages={[markdownMessage]} toolCalls={[]} />);

    expect(screen.getByText("Here is your profile:")).toBeInTheDocument();

    const strongName = screen.getByText("Name");
    expect(strongName.tagName).toBe("STRONG");

    const strongSkills = screen.getByText("Skills");
    expect(strongSkills.tagName).toBe("STRONG");

    expect(screen.getByText(": John Doe")).toBeInTheDocument();
    expect(screen.getAllByText("•")).toHaveLength(2);
  });

  it("renders collapsible progress logs when streamStatus is active", () => {
    const logs = ["Connecting...", "Searching...", "Extracting..."];
    const { container } = render(
      <ChatTranscript
        messages={[]}
        toolCalls={[]}
        streamStatus="Running tool"
        progressLogs={logs}
      />
    );

    expect(screen.getByText("Running tool")).toBeInTheDocument();
    expect(screen.getByText("Connecting...")).toBeInTheDocument();
    expect(screen.getByText("Searching...")).toBeInTheDocument();
    expect(screen.getByText("Extracting...")).toBeInTheDocument();
    expect(screen.getAllByText("✓")).toHaveLength(2);

    const pulseDot = container.querySelector(".pulse-dot");
    expect(pulseDot).toBeInTheDocument();
  });
});
