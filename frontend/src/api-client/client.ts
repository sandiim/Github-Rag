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

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init.headers } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(errorDetail(body.detail));
    }
    return response.json() as Promise<T>;
  }
}
