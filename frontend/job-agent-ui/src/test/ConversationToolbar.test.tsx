import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ConversationToolbar from "../components/chat/ConversationToolbar";
import type { ChatConversation } from "../types/chat";

const existingConversation: ChatConversation = {
  id: "conv-existing",
  role_profile_id: "profile-1",
  title: "Existing chat",
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("ConversationToolbar", () => {
  it("renders only persisted conversations and exposes icon commands", () => {
    render(
      <ConversationToolbar
        conversations={[existingConversation]}
        activeConversationId={existingConversation.id}
        disabled={false}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByRole("option", { name: "Existing chat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New chat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete current chat" })).toBeInTheDocument();
    expect(screen.queryByText("New session started")).not.toBeInTheDocument();
  });
});
