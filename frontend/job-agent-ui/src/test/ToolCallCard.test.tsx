import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import ToolCallCard from "../components/chat/ToolCallCard";
import type { AgentToolCall } from "../types/chat";

const completedToolCall: AgentToolCall = {
  id: "tool-cv-1",
  conversation_id: "conv-1",
  assistant_message_id: null,
  tool_name: "retrieve_profile_cv_chunks",
  status: "success",
  input_summary: "Relevant CV sections only",
  result_summary: "Found three relevant CV sections",
  safe_payload_json: '{"private":"not rendered"}',
  error_message: null,
  started_at: "2026-07-01T10:00:00Z",
  completed_at: "2026-07-01T10:00:02Z",
  created_at: "2026-07-01T09:59:59Z",
  updated_at: "2026-07-01T10:00:02Z",
};

describe("ToolCallCard", () => {
  it("renders a readable closed summary and exposes sanitized details when opened", () => {
    render(<ToolCallCard toolCall={completedToolCall} />);

    const friendlyLabel = screen.getByText("CV reading completed");
    const summary = friendlyLabel.closest("summary") as HTMLElement;
    const details = summary.closest("details") as HTMLDetailsElement;

    expect(details).not.toHaveAttribute("open");
    expect(summary).not.toHaveAttribute("aria-label");
    expect(summary).toHaveAccessibleName(/CV reading completed.*Completed/);
    expect(within(summary).getByText("Completed")).toBeInTheDocument();
    expect(within(summary).queryByText("retrieve_profile_cv_chunks")).not.toBeInTheDocument();

    fireEvent.click(summary);

    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Request")).toBeInTheDocument();
    expect(screen.getByText("Relevant CV sections only")).toBeInTheDocument();
    expect(screen.getByText("Result")).toBeInTheDocument();
    expect(screen.getByText("Found three relevant CV sections")).toBeInTheDocument();
    expect(screen.getByText("2s")).toBeInTheDocument();
    expect(screen.getByText("Technical name")).toBeInTheDocument();
    expect(screen.getByText("retrieve_profile_cv_chunks")).toBeInTheDocument();
    expect(screen.queryByText('{"private":"not rendered"}')).not.toBeInTheDocument();
  });

  it("animates the running status icon with the app spin class", () => {
    const { container } = render(
      <ToolCallCard
        toolCall={{
          ...completedToolCall,
          status: "running",
          result_summary: null,
          completed_at: null,
        }}
      />,
    );

    expect(container.querySelector(".tool-call-status-icon svg")).toHaveClass("spin");
  });

  it("focuses the native summary by keyboard and opens and closes details", async () => {
    const user = userEvent.setup();
    const { container } = render(<ToolCallCard toolCall={completedToolCall} />);
    const summary = container.querySelector("summary") as HTMLElement;
    const details = container.querySelector("details") as HTMLDetailsElement;

    await user.tab();
    expect(summary).toHaveFocus();

    await user.click(summary);
    expect(details).toHaveAttribute("open");

    await user.click(summary);
    expect(details).not.toHaveAttribute("open");
  });

  it("shows a readable failed state and the safe error after expansion", () => {
    render(
      <ToolCallCard
        toolCall={{
          ...completedToolCall,
          status: "failed",
          result_summary: null,
          error_message: "The CV service could not read this document.",
        }}
      />,
    );

    const friendlyLabel = screen.getByText("CV reading failed");
    const summary = friendlyLabel.closest("summary") as HTMLElement;
    expect(within(summary).getByText("Needs attention")).toBeInTheDocument();

    fireEvent.click(summary);

    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.getByText("The CV service could not read this document.")).toBeInTheDocument();
  });

  it("shows a readable pending state", () => {
    render(
      <ToolCallCard
        toolCall={{
          ...completedToolCall,
          status: "pending",
          completed_at: null,
        }}
      />,
    );

    const friendlyLabel = screen.getByText("Reading your CV");
    const summary = friendlyLabel.closest("summary") as HTMLElement;
    expect(within(summary).getByText("In progress")).toBeInTheDocument();
  });

  it("omits empty request and result sections", () => {
    const { container } = render(
      <ToolCallCard
        toolCall={{
          ...completedToolCall,
          input_summary: "",
          result_summary: null,
        }}
      />,
    );

    expect(container.querySelector("details")).toBeInTheDocument();
    expect(screen.queryByText("Request")).not.toBeInTheDocument();
    expect(screen.queryByText("Result")).not.toBeInTheDocument();
  });

  it("omits time and duration when timestamps are invalid", () => {
    const { container } = render(
      <ToolCallCard
        toolCall={{
          ...completedToolCall,
          started_at: "not-a-date",
          completed_at: "also-not-a-date",
          created_at: "invalid",
        }}
      />,
    );

    expect(container.querySelector("details")).toBeInTheDocument();
    expect(container.querySelector("time")).not.toBeInTheDocument();
    expect(container.querySelector(".tool-call-duration")).not.toBeInTheDocument();
  });
});
