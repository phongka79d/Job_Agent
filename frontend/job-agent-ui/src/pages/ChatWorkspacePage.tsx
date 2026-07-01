import { useEffect, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { createConversation, listConversationMessages, sendChatMessage } from "../api/chatClient";
import ChatComposer from "../components/chat/ChatComposer";
import ChatMessageList from "../components/chat/ChatMessageList";
import type { ChatConversation, ChatMessage } from "../types/chat";

interface OutletContext {
  activeProfileId: string | null;
}

interface ConversationState {
  profileId: string;
  generation: number;
  conversation: ChatConversation;
}

export default function ChatWorkspacePage() {
  const { activeProfileId } = useOutletContext<OutletContext>();
  const [conversation, setConversation] = useState<ConversationState | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const conversationRef = useRef<ConversationState | null>(null);
  const conversationRequestRef = useRef<{
    profileId: string;
    generation: number;
    promise: Promise<ChatConversation>;
  } | null>(null);
  const sendingRef = useRef(false);
  const activeProfileIdRef = useRef<string | null>(activeProfileId);
  const profileGenerationRef = useRef(0);

  if (activeProfileIdRef.current !== activeProfileId) {
    activeProfileIdRef.current = activeProfileId;
    profileGenerationRef.current += 1;
    conversationRef.current = null;
    conversationRequestRef.current = null;
    sendingRef.current = false;
  }

  useEffect(() => {
    setConversation(null);
    setMessages([]);
    setError(null);
    setIsSending(false);
    conversationRef.current = null;
    conversationRequestRef.current = null;
    sendingRef.current = false;
  }, [activeProfileId]);

  const isCurrentRequest = (profileId: string, generation: number) =>
    activeProfileIdRef.current === profileId && profileGenerationRef.current === generation;

  const ensureConversation = async (profileId: string, generation: number) => {
    if (
      conversationRef.current?.profileId === profileId &&
      conversationRef.current.generation === generation
    ) {
      return conversationRef.current.conversation;
    }
    if (conversation?.profileId === profileId && conversation.generation === generation) {
      conversationRef.current = conversation;
      return conversation.conversation;
    }
    if (
      conversationRequestRef.current?.profileId === profileId &&
      conversationRequestRef.current.generation === generation
    ) {
      return conversationRequestRef.current.promise;
    }
    const request = createConversation({
      role_profile_id: profileId,
      title: "Job agent session",
    })
      .then((created) => {
        if (isCurrentRequest(profileId, generation)) {
          const nextConversation = { profileId, generation, conversation: created };
          conversationRef.current = nextConversation;
          setConversation(nextConversation);
        }
        return created;
      })
      .finally(() => {
        if (conversationRequestRef.current?.promise === request) {
          conversationRequestRef.current = null;
        }
      });
    conversationRequestRef.current = { profileId, generation, promise: request };
    return request;
  };

  const handleSend = async (content: string) => {
    if (sendingRef.current) return;
    if (!activeProfileId) throw new Error("Select a role profile before chatting.");

    const sendProfileId = activeProfileId;
    const sendGeneration = profileGenerationRef.current;

    sendingRef.current = true;
    setIsSending(true);
    setError(null);

    try {
      const activeConversation = await ensureConversation(sendProfileId, sendGeneration);
      await sendChatMessage(activeConversation.id, { content });
      const refreshed = await listConversationMessages(activeConversation.id);
      if (isCurrentRequest(sendProfileId, sendGeneration)) {
        setMessages(refreshed);
      }
    } catch (sendError) {
      if (isCurrentRequest(sendProfileId, sendGeneration)) {
        setError(sendError instanceof Error ? sendError.message : "Failed to send message.");
      }
      throw sendError;
    } finally {
      if (isCurrentRequest(sendProfileId, sendGeneration)) {
        sendingRef.current = false;
        setIsSending(false);
      }
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
