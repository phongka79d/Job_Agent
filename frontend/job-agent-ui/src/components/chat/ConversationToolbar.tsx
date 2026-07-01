import { Plus, Trash2 } from "lucide-react";
import type { ChatConversation } from "../../types/chat";

interface ConversationToolbarProps {
  conversations: ChatConversation[];
  activeConversationId: string | null;
  disabled: boolean;
  onSelect: (conversation: ChatConversation) => void;
  onCreate: () => void;
  onDelete: (conversation: ChatConversation) => void;
}

export default function ConversationToolbar({
  conversations,
  activeConversationId,
  disabled,
  onSelect,
  onCreate,
  onDelete,
}: ConversationToolbarProps) {
  const activeConversation =
    conversations.find((item) => item.id === activeConversationId) ?? null;

  return (
    <div className="conversation-toolbar">
      <select
        aria-label="Chat history"
        value={activeConversationId ?? ""}
        onChange={(event) => {
          const selected = conversations.find((item) => item.id === event.target.value);
          if (selected) onSelect(selected);
        }}
        disabled={disabled || conversations.length === 0}
      >
        {activeConversationId == null ? <option value="">Chat history</option> : null}
        {conversations.map((conversation) => (
          <option key={conversation.id} value={conversation.id}>
            {conversation.title || new Date(conversation.created_at).toLocaleString()}
          </option>
        ))}
      </select>
      <button type="button" aria-label="New chat" onClick={onCreate} disabled={disabled}>
        <Plus size={16} />
      </button>
      <button
        type="button"
        aria-label="Delete current chat"
        onClick={() => activeConversation && onDelete(activeConversation)}
        disabled={disabled || !activeConversation}
      >
        <Trash2 size={16} />
      </button>
    </div>
  );
}
