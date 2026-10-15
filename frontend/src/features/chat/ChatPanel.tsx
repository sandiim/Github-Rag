import { useState, useRef } from "react";
import type { Message, Repository } from "../../types/api";
import { ChatComposer } from "./ChatComposer";
import { MessageList, type StreamingState } from "./MessageList";

export function ChatPanel({ repository, messages, streaming, conversationLoading = false, onSend, onClear, onRebuild, onCitationClick }: {
  repository: Repository | null;
  messages: Message[];
  streaming?: StreamingState | null;
  conversationLoading?: boolean;
  onSend: (question: string) => Promise<void>;
  onClear: () => void;
  onRebuild: () => Promise<void>;
  onCitationClick: (citation: Citation) => void;
}) {
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);

  const jumpToBottom = () => {
    const viewport = document.querySelector(".messages-viewport");
    viewport?.scrollTo({ top: viewport.scrollHeight, behavior: "smooth" });
    setShowJumpToBottom(false);
  };

  if (!repository) return (
    <main className="empty-state">
      <div className="empty-state-content">
        <h2>Select a repository</h2>
        <div className="empty-state-grid">
          <div className="empty-state-card">
            <div className="card-icon">📂</div>
            <h3>Add Repository</h3>
            <p>Connect a GitHub repository to begin indexing your codebase.</p>
          </div>
          <div className="empty-state-card">
            <div className="card-icon">💬</div>
            <h3>Ask Questions</h3>
            <p>Ask about architecture, logic, or specific implementation details.</p>
          </div>
          <div className="empty-state-card">
            <div className="card-icon">🔍</div>
            <h3>Verify Sources</h3>
            <p>Every answer includes pinned citations to the exact lines of code.</p>
          </div>
        </div>
      </div>
    </main>
  );

  const job = repository.ingestion;
  const isBusy = job?.state === "queued" || job?.state === "running";
  const rebuildLabel = job?.state === "queued" 
    ? "Queued · Waiting..." 
    : job?.state === "running" 
    ? `${job.stage ?? "Indexing"}...` 
    : "Rebuild Index";

  return (
    <main className="chat-panel-wrapper">
      <header className="chat-header">
        <div className="header-info">
          <h2>{repository.name}</h2>
          <span className={`status-badge ${repository.status}`}>{repository.status}</span>
        </div>
        <div className="header-actions">
          <button 
            className="rebuild-chat-btn" 
            onClick={onRebuild} 
            disabled={isBusy}
          >
            {rebuildLabel}
          </button>
          <button className="clear-chat-btn" onClick={onClear} title="Clear conversation">
            Clear Chat
          </button>
        </div>
      </header>

      <div className="chat-body">
        <MessageList 
          messages={messages} 
          streaming={streaming} 
          conversationLoading={conversationLoading} 
          onScrollToBottom={setShowJumpToBottom}
          onCitationClick={onCitationClick}
        />
        {showJumpToBottom && (
          <button className="jump-to-bottom-floating" onClick={jumpToBottom}>
            <span className="jump-icon">↓</span> Jump to latest
          </button>
        )}
      </div>
      
      <ChatComposer 
        disabled={repository.status !== "ready" || Boolean(streaming) || conversationLoading} 
        onSend={onSend} 
      />
    </main>
  );
}
