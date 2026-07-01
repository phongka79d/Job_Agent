import type { ChatMessage } from "../../types/chat";

interface ChatMessageListProps {
  messages: ChatMessage[];
}

export default function ChatMessageList({ messages }: ChatMessageListProps) {
  return (
    <div className="chat-message-list" aria-label="Chat messages">
      {messages.map((message) => (
        <article key={message.id} className={`chat-message chat-message-${message.role}`}>
          <div className="chat-message-role">{message.role}</div>
          <div className="chat-message-content">{message.content}</div>
        </article>
      ))}
    </div>
  );
}
