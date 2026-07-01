import { useEffect, useRef, useState, type ReactNode } from "react";
import { Bot, ChevronDown, Loader2, User } from "lucide-react";
import type { AgentToolCall, ChatMessage } from "../../types/chat";
import ToolCallCard from "./ToolCallCard";

interface ChatTranscriptProps {
  messages: ChatMessage[];
  toolCalls: AgentToolCall[];
  streamStatus?: string | null;
  streamingText?: string | null;
  onTypewriterComplete?: () => void;
  progressLogs?: string[];
}

type TimelineItem =
  | { type: "message"; id: string; timestamp: string; data: ChatMessage }
  | { type: "tool_call"; id: string; timestamp: string; data: AgentToolCall }
  | { type: "streaming"; id: string; timestamp: string; content: string };

function renderInlineMarkdown(content: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const boldRegex = /\*\*(.*?)\*\*/g;
  let lastIndex = 0;
  let match;

  while ((match = boldRegex.exec(content)) !== null) {
    const before = content.substring(lastIndex, match.index);
    if (before) parts.push(before);
    parts.push(<strong key={match.index}>{match[1]}</strong>);
    lastIndex = boldRegex.lastIndex;
  }

  const after = content.substring(lastIndex);
  if (after) parts.push(after);
  return parts.length > 0 ? parts : [content];
}

function SimpleMarkdown({ content }: { content: string }) {
  return (
    <>
      {content.split("\n").map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} className="markdown-space" />;
        }

        const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("* ");
        const cleanLine = isBullet ? trimmed.substring(2) : line;
        const parts = renderInlineMarkdown(cleanLine);

        if (isBullet) {
          return (
            <div key={index} className="markdown-bullet">
              <span aria-hidden="true">•</span>
              <div>{parts}</div>
            </div>
          );
        }

        return (
          <p key={index} className="markdown-para">
            {parts}
          </p>
        );
      })}
    </>
  );
}

function Typewriter({
  text,
  speed = 10,
  onComplete,
}: {
  text: string;
  speed?: number;
  onComplete?: () => void;
}) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    setDisplayedText("");
    if (!text) {
      onComplete?.();
      return;
    }

    let index = 0;
    const words = text.split(" ");
    const interval = window.setInterval(() => {
      if (index < words.length) {
        setDisplayedText((prev) => (prev ? `${prev} ${words[index]}` : words[index]));
        index += 1;
        return;
      }

      window.clearInterval(interval);
      onComplete?.();
    }, speed);

    return () => window.clearInterval(interval);
  }, [text, speed, onComplete]);

  return <SimpleMarkdown content={displayedText} />;
}

export default function ChatTranscript({
  messages,
  toolCalls,
  streamStatus = null,
  streamingText = null,
  onTypewriterComplete,
  progressLogs = [],
}: ChatTranscriptProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isLogsExpanded, setIsLogsExpanded] = useState(true);

  const timeline: TimelineItem[] = [
    ...messages.map((message) => ({
      type: "message" as const,
      id: message.id,
      timestamp: message.created_at,
      data: message,
    })),
    ...toolCalls.map((toolCall) => ({
      type: "tool_call" as const,
      id: toolCall.id,
      timestamp: toolCall.created_at || toolCall.started_at || "",
      data: toolCall,
    })),
  ].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  if (streamingText) {
    timeline.push({
      type: "streaming",
      id: "streaming-response",
      timestamp: "",
      content: streamingText,
    });
  }

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages, toolCalls, streamStatus, streamingText]);

  return (
    <div ref={containerRef} className="chat-transcript" aria-label="Chat transcript">
      {timeline.map((item) => {
        if (item.type === "message") {
          const message = item.data;
          return (
            <article key={item.id} className={`chat-message chat-message-${message.role}`}>
              <div className="chat-message-icon">
                {message.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div className="chat-message-content">
                <SimpleMarkdown content={message.content} />
              </div>
              <time dateTime={message.created_at} className="chat-message-time">
                {new Intl.DateTimeFormat(undefined, {
                  hour: "2-digit",
                  minute: "2-digit",
                }).format(new Date(message.created_at))}
              </time>
            </article>
          );
        }

        if (item.type === "streaming") {
          return (
            <article key={item.id} className="chat-message chat-message-assistant">
              <div className="chat-message-icon">
                <Bot size={16} />
              </div>
              <div className="chat-message-content">
                <Typewriter text={item.content} onComplete={onTypewriterComplete} />
              </div>
            </article>
          );
        }

        return <ToolCallCard key={item.id} toolCall={item.data} />;
      })}

      {streamStatus ? (
        <div className="stream-status-container">
          <button
            type="button"
            className="stream-status-header"
            aria-expanded={isLogsExpanded}
            onClick={() => setIsLogsExpanded((expanded) => !expanded)}
          >
            <Loader2 size={14} className="spin stream-status-loader" />
            <span>{streamStatus}</span>
            <span
              className={`stream-status-chevron${
                isLogsExpanded ? " stream-status-chevron-open" : ""
              }`}
            >
              <ChevronDown size={14} />
            </span>
          </button>

          {isLogsExpanded && progressLogs.length > 0 ? (
            <div className="stream-status-logs">
              {progressLogs.map((log, index) => {
                const isLast = index === progressLogs.length - 1;
                return (
                  <div
                    key={`${log}-${index}`}
                    className={`stream-status-log${
                      isLast ? " stream-status-log-active" : ""
                    }`}
                  >
                    {isLast ? (
                      <span className="pulse-dot" />
                    ) : (
                      <span className="stream-status-check">✓</span>
                    )}
                    <span>{log}</span>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
