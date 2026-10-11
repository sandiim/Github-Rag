export type Repository = { id: string; name: string; status: string };
export type Citation = { path: string; startLine: number; endLine: number; url: string };
export type Message = { role: "user" | "assistant"; content: string; citations: Citation[] };
export type Conversation = { title: string; messages: Message[] };
