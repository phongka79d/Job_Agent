import { Plus, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  createConversation,
  deleteConversation,
  listAgentToolCalls,
  listConversationMessages,
  listConversations,
  sendChatMessage,
  streamChatResponse,
} from "../api/chatClient";
import ChatComposer from "../components/chat/ChatComposer";
import ChatMessageList from "../components/chat/ChatMessageList";
import ToolCallTimeline from "../components/chat/ToolCallTimeline";
import type { AgentToolCall, ChatConversation, ChatMessage } from "../types/chat";

interface OutletContext {
  activeProfileId: string | null;
  triggerMetricsRefresh?: () => void;
}

interface ConversationState {
  profileId: string;
  generation: number;
  conversation: ChatConversation;
}

function conversationLabel(conversation: ChatConversation): string {
  return conversation.title || new Date(conversation.created_at).toLocaleString();
}

function shouldOpenReviewQueue(toolCalls: AgentToolCall[]): boolean {
  return toolCalls.some((toolCall) => {
    if (toolCall.tool_name !== "search_jobs" || toolCall.status !== "success") {
      return false;
    }
    if (!toolCall.safe_payload_json) return false;
    try {
      const payload = JSON.parse(toolCall.safe_payload_json) as {
        inserted_jobs?: unknown;
        review_queue_path?: unknown;
      };
      return payload.review_queue_path === "/review" && Number(payload.inserted_jobs) > 0;
    } catch {
      return false;
    }
  });
}

export default function ChatWorkspacePage() {
  const { activeProfileId, triggerMetricsRefresh } = useOutletContext<OutletContext>();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState<ConversationState | null>(null);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<AgentToolCall[]>([]);
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

  const isCurrentRequest = (profileId: string, generation: number) =>
    activeProfileIdRef.current === profileId && profileGenerationRef.current === generation;

  const refreshConversations = async (profileId: string, generation: number) => {
    const history = await listConversations(profileId);
    if (isCurrentRequest(profileId, generation)) {
      setConversations(history);
    }
    return history;
  };

  useEffect(() => {
    const profileId = activeProfileId;
    const generation = profileGenerationRef.current;
    setConversation(null);
    setConversations([]);
    setMessages([]);
    setToolCalls([]);
    setError(null);
    setIsSending(false);
    conversationRef.current = null;
    conversationRequestRef.current = null;
    sendingRef.current = false;

    if (!profileId) return;

    void refreshConversations(profileId, generation).catch((historyError) => {
      if (isCurrentRequest(profileId, generation)) {
        setError(historyError instanceof Error ? historyError.message : "Failed to load chat history.");
      }
    });
  }, [activeProfileId]);

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

  const handleSelectConversation = async (selected: ChatConversation) => {
    if (!activeProfileId || selected.role_profile_id !== activeProfileId) return;
    const generation = profileGenerationRef.current;
    const nextConversation = {
      profileId: activeProfileId,
      generation,
      conversation: selected,
    };
    conversationRef.current = nextConversation;
    setConversation(nextConversation);
    setError(null);
    try {
      const loadedMessages = await listConversationMessages(selected.id);
      if (isCurrentRequest(activeProfileId, generation)) {
        setMessages(loadedMessages);
      }
      const loadedToolCalls = await listAgentToolCalls(selected.id);
      if (isCurrentRequest(activeProfileId, generation)) {
        setToolCalls(loadedToolCalls);
      }
    } catch (loadError) {
      if (isCurrentRequest(activeProfileId, generation)) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load chat.");
      }
    }
  };

  const handleNewConversation = () => {
    conversationRef.current = null;
    conversationRequestRef.current = null;
    setConversation(null);
    setMessages([]);
    setToolCalls([]);
    setError(null);
  };

  const handleDeleteConversation = async (target: ChatConversation) => {
    if (!activeProfileId) return;
    const generation = profileGenerationRef.current;
    setError(null);
    try {
      await deleteConversation(target.id);
      if (conversationRef.current?.conversation.id === target.id) {
        conversationRef.current = null;
        setConversation(null);
        setMessages([]);
        setToolCalls([]);
      }
      await refreshConversations(activeProfileId, generation);
    } catch (deleteError) {
      if (isCurrentRequest(activeProfileId, generation)) {
        setError(deleteError instanceof Error ? deleteError.message : "Failed to delete chat.");
      }
    }
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
      const response = await sendChatMessage(activeConversation.id, { content });
      await streamChatResponse(response.stream_url);
      const refreshed = await listConversationMessages(activeConversation.id);
      const refreshedToolCalls = await listAgentToolCalls(activeConversation.id);
      await refreshConversations(sendProfileId, sendGeneration);
      if (isCurrentRequest(sendProfileId, sendGeneration)) {
        setMessages(refreshed);
        setToolCalls(refreshedToolCalls);
        if (shouldOpenReviewQueue(refreshedToolCalls)) {
          triggerMetricsRefresh?.();
          navigate("/review");
        }
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
      <div className="chat-history" aria-label="Chat history">
        <button
          type="button"
          className="btn-secondary chat-history-new"
          onClick={handleNewConversation}
          disabled={!activeProfileId || isSending}
        >
          <Plus size={14} /> New chat
        </button>
        <div className="chat-history-list">
          {conversations.map((historyConversation) => {
            const active = conversation?.conversation.id === historyConversation.id;
            const label = conversationLabel(historyConversation);
            return (
              <div
                key={historyConversation.id}
                className={`chat-history-item${active ? " chat-history-item-active" : ""}`}
              >
                <button
                  type="button"
                  className="chat-history-select"
                  onClick={() => void handleSelectConversation(historyConversation)}
                  disabled={isSending}
                >
                  {label}
                </button>
                <button
                  type="button"
                  className="chat-history-delete"
                  aria-label={`Delete ${label}`}
                  onClick={() => void handleDeleteConversation(historyConversation)}
                  disabled={isSending}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        </div>
      </div>
      <ToolCallTimeline toolCalls={toolCalls} />
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
