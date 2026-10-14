import { useEffect, useState } from "react";
import { ApiClient } from "./api-client/client";
import { ChatPanel } from "./features/chat/ChatPanel";
import { AddRepositoryForm } from "./features/repositories/AddRepositoryForm";
import { IngestionStatus } from "./features/repositories/IngestionStatus";
import { RebuildButton } from "./features/repositories/RebuildButton";
import { RepositorySidebar } from "./features/repositories/RepositorySidebar";
import type { Message, Repository } from "./types/api";

const api = new ApiClient();

export default function App() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState("");
  const selected = repositories.find(repository => repository.id === selectedId) ?? null;
  const hasActiveJob = repositories.some(repository =>
    repository.ingestion?.state === "queued" || repository.ingestion?.state === "running"
  );

  const refresh = async () => setRepositories(await api.repositories());

  useEffect(() => {
    void refresh().catch(failure => setError((failure as Error).message));
  }, []);

  useEffect(() => {
    if (!hasActiveJob) return;
    const timer = window.setInterval(() => {
      void refresh().catch(failure => setError((failure as Error).message));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [hasActiveJob]);

  const select = async (id: string) => {
    setSelectedId(id);
    try {
      setMessages((await api.conversation(id)).messages);
    } catch (failure) {
      setMessages([]);
      setError((failure as Error).message);
    }
  };

  const rebuild = async (id: string) => {
    const updated = await api.rebuild(id);
    setRepositories(current => current.map(repository => repository.id === id ? updated : repository));
  };

  return <div className="app">
    <aside>
      <RepositorySidebar repositories={repositories} selectedRepositoryId={selectedId} onSelect={select} />
      <AddRepositoryForm onAdd={async url => {
        const repository = await api.addRepository(url);
        setRepositories(current => current.some(item => item.id === repository.id)
          ? current.map(item => item.id === repository.id ? repository : item)
          : [...current, repository]);
        await select(repository.id);
      }} />
      {selected && <>
        <IngestionStatus repository={selected} onRetry={() => rebuild(selected.id)} />
        {selected.ingestion?.state !== "queued" && selected.ingestion?.state !== "running" &&
          <RebuildButton onRebuild={() => rebuild(selected.id)} />}
      </>}
    </aside>
    <ChatPanel repository={selected} messages={messages} onSend={async question => {
      if (!selected) return;
      setMessages(current => [...current, { role: "user", content: question, citations: [] }]);
      const answer = await api.ask(selected.id, question);
      setMessages(current => [...current, { role: "assistant", content: answer.text, citations: answer.citations }]);
    }} />
    {error && <p role="alert">{error}</p>}
  </div>;
}
