export type Ingestion = {
  id: string;
  state: "queued" | "running" | "completed" | "skipped" | "failed";
  stage: string | null;
  completed_files: number;
  total_files: number | null;
  error_message: string | null;
};
export type Repository = { id: string; name: string; status: string; ingestion?: Ingestion | null };
export type Citation = { path: string; startLine: number; endLine: number; url: string };
export type Message = { role: "user" | "assistant"; content: string; citations: Citation[] };
export type Conversation = { title: string; messages: Message[] };
