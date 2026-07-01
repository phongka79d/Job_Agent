import { useEffect, useRef, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  createConversation,
  listAgentToolCalls,
  listConversationMessages,
  sendChatMessage,
  streamChatResponse,
} from "../api/chatClient";
import ChatComposer from "../components/chat/ChatComposer";
import ChatTranscript from "../components/chat/ChatTranscript";
import type { AgentToolCall, ChatConversation, ChatMessage } from "../types/chat";

interface OutletContext {
  activeProfileId: string | null;
  triggerMetricsRefresh?: () => void;
}

interface ChatWorkspacePageProps {
  contextOverride?: {
    activeConversationId: string | null;
    onConversationCreated: (created: ChatConversation) => Promise<void> | void;
    onMessageSent: () => Promise<void> | void;
    isSendingGlobal: boolean;
    setIsSendingGlobal: (val: boolean) => void;
  };
}

function streamValue(data: unknown, key: string): string | null {
  if (!data || typeof data !== "object" || !(key in data)) {
    return null;
  }
  const value = (data as Record<string, unknown>)[key];
  return typeof value === "string" ? value : null;
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

export default function ChatWorkspacePage({ contextOverride }: ChatWorkspacePageProps = {}) {
  const { activeProfileId, triggerMetricsRefresh } = useOutletContext<OutletContext>();
  const navigate = useNavigate();

  const activeConversationId = contextOverride?.activeConversationId ?? null;
  const onConversationCreated = contextOverride?.onConversationCreated;
  const onMessageSent = contextOverride?.onMessageSent;
  const isSendingGlobal = contextOverride?.isSendingGlobal ?? false;
  const setIsSendingGlobal = contextOverride?.setIsSendingGlobal ?? (() => undefined);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<AgentToolCall[]>([]);
  const [localIsSending, setLocalIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [progressLogs, setProgressLogs] = useState<string[]>([]);

  const updateStreamStatus = (status: string | null) => {
    setStreamStatus(status);
    if (status) {
      setProgressLogs((prev) => {
        if (prev.includes(status)) return prev;
        return [...prev, status];
      });
    }
  };

  const isSending = contextOverride ? isSendingGlobal : localIsSending;
  const setIsSending = contextOverride ? setIsSendingGlobal : setLocalIsSending;

  const sendingRef = useRef(false);
  const activeProfileIdRef = useRef<string | null>(activeProfileId);
  const profileGenerationRef = useRef(0);
  const lastLoadedConversationIdRef = useRef<string | null>(null);
  const pendingRefreshedDataRef = useRef<{ messages: ChatMessage[]; toolCalls: AgentToolCall[] } | null>(null);
  const streamFinishedRef = useRef(false);
  const activeStreamRequestRef = useRef<{ profileId: string; generation: number } | null>(null);

  const handleTypewriterComplete = () => {
    const activeReq = activeStreamRequestRef.current;
    if (!activeReq || !isCurrentRequest(activeReq.profileId, activeReq.generation)) {
      setStreamingText(null);
      setIsSending(false);
      sendingRef.current = false;
      pendingRefreshedDataRef.current = null;
      streamFinishedRef.current = false;
      activeStreamRequestRef.current = null;
      return;
    }

    if (pendingRefreshedDataRef.current) {
      const { messages: refreshedMsgs, toolCalls: refreshedTools } = pendingRefreshedDataRef.current;
      setMessages(refreshedMsgs);
      setToolCalls(refreshedTools);
      if (shouldOpenReviewQueue(refreshedTools)) {
        triggerMetricsRefresh?.();
        navigate("/review");
      }
    }
    setStreamingText(null);
    setIsSending(false);
    sendingRef.current = false;
    pendingRefreshedDataRef.current = null;
    streamFinishedRef.current = false;
    activeStreamRequestRef.current = null;
    setProgressLogs([]);
  };
  if (activeProfileIdRef.current !== activeProfileId) {
    activeProfileIdRef.current = activeProfileId;
    profileGenerationRef.current += 1;
    sendingRef.current = false;
  }

  const isCurrentRequest = (profileId: string, generation: number) =>
    activeProfileIdRef.current === profileId && profileGenerationRef.current === generation;

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      setToolCalls([]);
      setError(null);
      lastLoadedConversationIdRef.current = null;
      setStreamingText(null);
      setStreamStatus(null);
      pendingRefreshedDataRef.current = null;
      streamFinishedRef.current = false;
      activeStreamRequestRef.current = null;
      setProgressLogs([]);
      return;
    }

    if (!activeProfileId) {
      return;
    }

    if (lastLoadedConversationIdRef.current === activeConversationId) {
      return;
    }

    const generation = profileGenerationRef.current;
    const profileId = activeProfileId;

    const loadChatData = async () => {
      setError(null);
      try {
        const loadedMessages = await listConversationMessages(activeConversationId);
        if (isCurrentRequest(profileId, generation)) {
          setMessages(loadedMessages);
        }
        const loadedToolCalls = await listAgentToolCalls(activeConversationId);
        if (isCurrentRequest(profileId, generation)) {
          setToolCalls(loadedToolCalls);
        }
        lastLoadedConversationIdRef.current = activeConversationId;
      } catch (loadError) {
        if (isCurrentRequest(profileId, generation)) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load chat.");
        }
      }
    };

    void loadChatData();
  }, [activeConversationId, activeProfileId]);

  const handleSend = async (content: string) => {
    if (sendingRef.current || isSending) return;
    if (!activeProfileId) throw new Error("Select a role profile before chatting.");

    const sendProfileId = activeProfileId;
    const sendGeneration = profileGenerationRef.current;

    sendingRef.current = true;
    setIsSending(true);
    setError(null);
    updateStreamStatus("Server: Preparing...");
    setStreamingText(null);
    setProgressLogs([]);
    activeStreamRequestRef.current = { profileId: sendProfileId, generation: sendGeneration };

    try {
      let currentConversationId = activeConversationId;
      if (!currentConversationId) {
        updateStreamStatus("Server: Creating conversation...");
        const created = await createConversation({
          role_profile_id: sendProfileId,
        });
        currentConversationId = created.id;
        if (onConversationCreated) {
          await onConversationCreated(created);
        }
      }

      updateStreamStatus("Server: Sending message...");
      const response = await sendChatMessage(currentConversationId, { content });

      updateStreamStatus("LLM: Analyzing...");
      let receivedAssistantText = false;
      await streamChatResponse(response.stream_url, (event) => {
        const toolName = streamValue(event.data, "tool_name") ?? "tool";
        switch (event.event) {
          case "message_started":
            updateStreamStatus("LLM: Starting response...");
            break;
          case "tool_call_started":
            updateStreamStatus(`Tool: Running ${toolName}...`);
            break;
          case "tool_call_completed":
            updateStreamStatus(`Tool: ${toolName} completed.`);
            break;
          case "tool_call_failed":
            updateStreamStatus(`Tool: ${toolName} failed.`);
            break;
          case "tool_call_progress":
            updateStreamStatus(`Tool: ${streamValue(event.data, "message") ?? "Working..."}`);
            break;
          case "assistant_delta":
            updateStreamStatus("LLM: Writing response...");
            {
              const content = streamValue(event.data, "content");
              if (content) {
                receivedAssistantText = true;
                setStreamingText(content);
              }
            }
            break;
          case "message_completed":
            updateStreamStatus(null);
            break;
        }
      });

      updateStreamStatus("Server: Refreshing conversation...");
      const refreshed = await listConversationMessages(currentConversationId);
      const refreshedToolCalls = await listAgentToolCalls(currentConversationId);

      if (onMessageSent) {
        await onMessageSent();
      }

      lastLoadedConversationIdRef.current = currentConversationId;

      pendingRefreshedDataRef.current = { messages: refreshed, toolCalls: refreshedToolCalls };
      streamFinishedRef.current = true;

      if (!receivedAssistantText) {
        handleTypewriterComplete();
      }
    } catch (sendError) {
      if (isCurrentRequest(sendProfileId, sendGeneration)) {
        setError(sendError instanceof Error ? sendError.message : "Failed to send message.");
      }
      throw sendError;
    } finally {
      if (!streamFinishedRef.current && isCurrentRequest(sendProfileId, sendGeneration)) {
        sendingRef.current = false;
        setIsSending(false);
        updateStreamStatus(null);
        setStreamingText(null);
        setProgressLogs([]);
      }
    }
  };

  return (
    <section className="chat-workspace">
      <ChatTranscript
        messages={messages}
        toolCalls={toolCalls}
        streamStatus={streamStatus}
        streamingText={streamingText}
        onTypewriterComplete={handleTypewriterComplete}
        progressLogs={progressLogs}
      />
      {error ? <div className="chat-error" role="alert">{error}</div> : null}
      <ChatComposer disabled={!activeProfileId || isSending} onSend={handleSend} />
    </section>
  );
}
