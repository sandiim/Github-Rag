import type { Message, Repository } from "../../types/api";
import { ChatComposer } from "./ChatComposer";
import { MessageList } from "./MessageList";
export function ChatPanel({ repository, messages, onSend }: { repository: Repository | null; messages: Message[]; onSend: (question: string) => Promise<void> }) { if (!repository) return <main><h2>Select a repository</h2><p>Add or choose a repository to see its saved conversation.</p></main>; return <main><header><h2>{repository.name}</h2><p>{repository.status}</p></header><MessageList messages={messages} /><ChatComposer disabled={repository.status !== "ready"} onSend={onSend} /></main>; }
