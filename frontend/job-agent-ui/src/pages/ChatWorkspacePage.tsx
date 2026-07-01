import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { createConversation, listConversationMessages, sendChatMessage } from "../api/chatClient";
import ChatComposer from "../components/chat/ChatComposer";
import ChatMessageList from "../components/chat/ChatMessageList";
import type { ChatConversation, ChatMessage } from "../types/chat";

interface OutletContext {
  activeProfileId: string | null;
}

export default function ChatWorkspacePage() {
  const { activeProfileId } = useOutletContext<OutletContext>();
  const [conversation, setConversation] = useState<ChatConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    setConversation(null);
    setMessages([]);
  }, [activeProfileId]);

  const ensureConversation = async () => {
    if (conversation) return conversation;
    if (!activeProfileId) throw new Error("Select a role profile before chatting.");
    const created = await createConversation({
      role_profile_id: activeProfileId,
      title: "Job agent session",
    });
    setConversation(created);
    return created;
  };

  const handleSend = async (content: string) => {
    const activeConversation = await ensureConversation();
    await sendChatMessage(activeConversation.id, { content });
    const refreshed = await listConversationMessages(activeConversation.id);
    setMessages(refreshed);
  };

  return (
    <section className="chat-workspace">
      <ChatMessageList messages={messages} />
      <ChatComposer disabled={!activeProfileId} onSend={handleSend} />
    </section>
  );
}
