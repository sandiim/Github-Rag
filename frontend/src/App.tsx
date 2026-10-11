import { useEffect, useState } from "react";
import { ApiClient } from "./api-client/client";
import { ChatPanel } from "./features/chat/ChatPanel";
import { AddRepositoryForm } from "./features/repositories/AddRepositoryForm";
import { RebuildButton } from "./features/repositories/RebuildButton";
import { RepositorySidebar } from "./features/repositories/RepositorySidebar";
import type { Message, Repository } from "./types/api";

const api = new ApiClient();
export default function App() { const [repositories, setRepositories] = useState<Repository[]>([]); const [selectedId, setSelectedId] = useState<string | null>(null); const [messages, setMessages] = useState<Message[]>([]); const [error, setError] = useState(""); const selected = repositories.find(repository => repository.id === selectedId) ?? null;
  const refresh = async () => setRepositories(await api.repositories());
  useEffect(() => { refresh().catch(error => setError(error.message)); }, []);
  const select = async (id: string) => { setSelectedId(id); try { setMessages((await api.conversation(id)).messages); } catch (error) { setMessages([]); setError((error as Error).message); } };
  return <div className="app"><aside><RepositorySidebar repositories={repositories} selectedRepositoryId={selectedId} onSelect={select} /><AddRepositoryForm onAdd={async url => { const repository = await api.addRepository(url); await refresh(); await select(repository.id); }} />{selected && <RebuildButton onRebuild={async () => { await api.rebuild(selected.id); await refresh(); }} />}</aside><ChatPanel repository={selected} messages={messages} onSend={async question => { if (!selected) return; setMessages(current => [...current, { role: "user", content: question, citations: [] }]); const answer = await api.ask(selected.id, question); setMessages(current => [...current, { role: "assistant", content: answer.text, citations: answer.citations }]); }} />{error && <p role="alert">{error}</p>}</div>; }
