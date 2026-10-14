import type { Citation, Conversation, Repository } from "../types/api";

type ApiCitation = { path: string; start_line: number; end_line: number; url: string };
type ApiMessage = { role: "user" | "assistant"; content: string; citations: ApiCitation[] };

function errorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map(item => typeof item?.msg === "string" ? item.msg : "Invalid request").join("; ");
  }
  return "Request failed";
}

const toCitation = (citation: ApiCitation): Citation => ({
  path: citation.path, startLine: citation.start_line, endLine: citation.end_line, url: citation.url
});

export type ChatStreamEvent =
  | { type: "status"; stage: "retrieving" | "generating" }
  | { type: "delta"; text: string }
  | { type: "checkpoint" | "complete"; text: string; citations: Citation[] }
  | { type: "error"; message: string };

function parseChatEvent(line: string): ChatStreamEvent {
  const value: unknown = JSON.parse(line);
  if (!value || typeof value !== "object" || !("type" in value)) throw new Error("Invalid answer stream event");
  const event = value as Record<string, unknown>;
  if (event.type === "status" && (event.stage === "retrieving" || event.stage === "generating")) {
    return { type: "status", stage: event.stage };
  }
  if (event.type === "delta" && typeof event.text === "string") {
    return { type: "delta", text: event.text };
  }
  if ((event.type === "checkpoint" || event.type === "complete") &&
      typeof event.text === "string" && Array.isArray(event.citations)) {
    const citations = event.citations.map(item => {
      if (!item || typeof item !== "object") throw new Error("Invalid answer citation");
      const citation = item as Record<string, unknown>;
      if (typeof citation.path !== "string" || typeof citation.start_line !== "number" ||
          typeof citation.end_line !== "number" || typeof citation.url !== "string") {
        throw new Error("Invalid answer citation");
      }
      return toCitation(citation as ApiCitation);
    });
    return { type: event.type, text: event.text, citations };
  }
  if (event.type === "error" && typeof event.message === "string") {
    return { type: "error", message: event.message };
  }
  throw new Error("Invalid answer stream event");
}

export class ApiClient {
  constructor(private readonly baseUrl = "") {}

  async repositories(): Promise<Repository[]> {
    return this.request<Repository[]>("/repositories");
  }

  async addRepository(url: string): Promise<Repository> {
    return this.request<Repository>("/repositories", { method: "POST", body: JSON.stringify({ url }) });
  }

  async rebuild(repositoryId: string): Promise<Repository> {
    return this.request<Repository>(`/repositories/${repositoryId}/rebuild`, { method: "POST" });
  }

  async conversation(repositoryId: string): Promise<Conversation> {
    const response = await this.request<{ title: string; messages: ApiMessage[] }>(`/repositories/${repositoryId}/conversation`);
    return { title: response.title, messages: response.messages.map(message => ({ ...message, citations: message.citations.map(toCitation) })) };
  }

  async ask(repositoryId: string, question: string): Promise<{ text: string; citations: Citation[] }> {
    const response = await this.request<{ text: string; citations: ApiCitation[] }>(`/repositories/${repositoryId}/chat`, { method: "POST", body: JSON.stringify({ question }) });
    return { text: response.text, citations: response.citations.map(toCitation) };
  }

  async askStream(
    repositoryId: string, question: string, onEvent: (event: ChatStreamEvent) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/repositories/${repositoryId}/chat/stream`, {
      method: "POST", body: JSON.stringify({ question }),
      headers: { "Content-Type": "application/json" }, signal
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(errorDetail(body.detail));
    }
    if (!response.body) throw new Error("The answer stream is unavailable");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let completed = false;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let newline = buffer.indexOf("\n");
        while (newline !== -1) {
          const line = buffer.slice(0, newline).trim();
          buffer = buffer.slice(newline + 1);
          if (line) {
            const event = parseChatEvent(line);
            onEvent(event);
            if (event.type === "complete") completed = true;
            if (event.type === "error") throw new Error(event.message);
          }
          newline = buffer.indexOf("\n");
        }
      }
      buffer += decoder.decode();
      if (buffer.trim() || !completed) throw new Error("The answer stream ended early");
    } catch (failure) {
      await reader.cancel().catch(() => {});
      throw failure;
    } finally {
      reader.releaseLock();
    }
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init.headers } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(errorDetail(body.detail));
    }
    return response.json() as Promise<T>;
  }
}
