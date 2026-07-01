import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ToolCallTimeline from "../components/chat/ToolCallTimeline";

describe("ToolCallTimeline", () => {
  it("shows visible sanitized tool call state", () => {
    render(
      <ToolCallTimeline
        toolCalls={[
          {
            id: "call-1",
            conversation_id: "conv-1",
            assistant_message_id: null,
            tool_name: "search_jobs",
            status: "running",
            input_summary: "Searching AI Engineer jobs in Hanoi",
            result_summary: null,
            safe_payload_json: null,
            error_message: null,
            started_at: null,
            completed_at: null,
            created_at: "2026-07-01T00:00:00Z",
            updated_at: "2026-07-01T00:00:00Z",
          },
        ]}
      />
    );

    expect(screen.getByText("search_jobs")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("Searching AI Engineer jobs in Hanoi")).toBeInTheDocument();
  });
});
