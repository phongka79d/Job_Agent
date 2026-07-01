import { User, Bot } from "lucide-react";
import type { ChatMessage } from "../../types/chat";

interface ChatMessageListProps {
  messages: ChatMessage[];
}

export default function ChatMessageList({ messages }: ChatMessageListProps) {
  return (
    <div className="chat-message-list" aria-label="Chat messages">
      {messages.map((message) => (
        <article key={message.id} className={`chat-message chat-message-${message.role}`}>
          <div className="chat-message-icon">
            {message.role === "user" ? <User size={16} /> : <Bot size={16} />}
          </div>
          <div className="chat-message-content">{message.content}</div>
          <time dateTime={message.created_at} className="chat-message-time">
            {new Intl.DateTimeFormat(undefined, {
              hour: "2-digit",
              minute: "2-digit",
            }).format(new Date(message.created_at))}
          </time>
        </article>
      ))}
    </div>
  );
}
