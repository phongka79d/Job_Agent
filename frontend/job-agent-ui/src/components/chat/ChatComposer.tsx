import { Send } from "lucide-react";
import { useState } from "react";

interface ChatComposerProps {
  disabled?: boolean;
  onSend: (content: string) => Promise<void> | void;
}

export default function ChatComposer({ disabled = false, onSend }: ChatComposerProps) {
  const [content, setContent] = useState("");

  const submit = async () => {
    const trimmed = content.trim();
    if (!trimmed || disabled) return;
    setContent("");
    await onSend(trimmed);
  };

  return (
    <form
      className="chat-composer"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <textarea
        value={content}
        disabled={disabled}
        onChange={(event) => setContent(event.target.value)}
        aria-label="Message"
      />
      <button type="submit" disabled={disabled || !content.trim()} aria-label="Send message">
        <Send size={18} />
      </button>
    </form>
  );
}
