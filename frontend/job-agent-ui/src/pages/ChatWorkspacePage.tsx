import { useEffect, useRef, useState } from "react";
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
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const conversationRef = useRef<ChatConversation | null>(null);
  const conversationRequestRef = useRef<Promise<ChatConversation> | null>(null);
  const sendingRef = useRef(false);

  useEffect(() => {
    setConversation(null);
    setMessages([]);
    setError(null);
    conversationRef.current = null;
    conversationRequestRef.current = null;
  }, [activeProfileId]);

  const ensureConversation = async () => {
    if (conversationRef.current) return conversationRef.current;
    if (conversation) {
      conversationRef.current = conversation;
      return conversation;
    }
    if (conversationRequestRef.current) return conversationRequestRef.current;
    if (!activeProfileId) throw new Error("Select a role profile before chatting.");
    const request = createConversation({
      role_profile_id: activeProfileId,
      title: "Job agent session",
    })
      .then((created) => {
        conversationRef.current = created;
        setConversation(created);
        return created;
      })
      .finally(() => {
        conversationRequestRef.current = null;
      });
    conversationRequestRef.current = request;
    return request;
  };

  const handleSend = async (content: string) => {
    if (sendingRef.current) return;

    sendingRef.current = true;
    setIsSending(true);
    setError(null);

    try {
      const activeConversation = await ensureConversation();
      await sendChatMessage(activeConversation.id, { content });
      const refreshed = await listConversationMessages(activeConversation.id);
      setMessages(refreshed);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Failed to send message.");
      throw sendError;
    } finally {
      sendingRef.current = false;
      setIsSending(false);
    }
  };

  return (
    <section className="chat-workspace">
      <ChatMessageList messages={messages} />
      {error ? (
        <div className="chat-error" role="alert">
          {error}
        </div>
      ) : null}
      <ChatComposer disabled={!activeProfileId || isSending} onSend={handleSend} />
    </section>
  );
}
