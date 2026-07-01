import { Send } from "lucide-react";
import { useRef, useState } from "react";

interface ChatComposerProps {
  disabled?: boolean;
  onSend: (content: string) => Promise<void> | void;
}

export default function ChatComposer({ disabled = false, onSend }: ChatComposerProps) {
  const [content, setContent] = useState("");
  const isSubmittingRef = useRef(false);

  const submit = async () => {
    const trimmed = content.trim();
    if (!trimmed || disabled || isSubmittingRef.current) return;

    isSubmittingRef.current = true;
    try {
      await onSend(trimmed);
      setContent("");
    } catch {
      // Keep the draft in place; the page owns the visible error message.
    } finally {
      isSubmittingRef.current = false;
    }
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
