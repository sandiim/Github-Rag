import type { Message, Repository } from "../../types/api";
import { ChatComposer } from "./ChatComposer";
import { MessageList, type StreamingState } from "./MessageList";

export function ChatPanel({ repository, messages, streaming, conversationLoading = false, onSend }: {
  repository: Repository | null;
  messages: Message[];
  streaming?: StreamingState | null;
  conversationLoading?: boolean;
  onSend: (question: string) => Promise<void>;
}) {
  if (!repository) return (
    <main className="empty-state">
      <div className="empty-state-content">
        <h2>Select a repository</h2>
        <p>Add or choose a repository from the sidebar to start chatting with your code.</p>
      </div>
    </main>
  );

  return (
    <main>
      <header className="chat-header">
        <div className="header-info">
          <h2>{repository.name}</h2>
          <span className={`status-badge ${repository.status}`}>{repository.status}</span>
        </div>
      </header>

      <MessageList messages={messages} streaming={streaming} conversationLoading={conversationLoading} />
      
      <ChatComposer 
        disabled={repository.status !== "ready" || Boolean(streaming) || conversationLoading} 
        onSend={onSend} 
      />
    </main>
  );
}
