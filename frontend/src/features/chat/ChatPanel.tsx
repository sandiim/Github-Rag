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
  if (!repository) return <main><h2>Select a repository</h2><p>Add or choose a repository to see its saved conversation.</p></main>;
  return <main>
    <header><h2>{repository.name}</h2><p>{repository.status}</p></header>
    <MessageList messages={messages} streaming={streaming} />
    <ChatComposer disabled={repository.status !== "ready" || Boolean(streaming) || conversationLoading} onSend={onSend} />
  </main>;
}
