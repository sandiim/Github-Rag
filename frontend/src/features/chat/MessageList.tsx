import type { Message } from "../../types/api";
import { CitationList } from "./CitationList";
export function MessageList({ messages }: { messages: Message[] }) { return <section className="messages" aria-live="polite">{messages.map((message, index) => <article className={message.role} key={`${message.role}-${index}`}><strong>{message.role === "user" ? "You" : "Repository"}</strong><p>{message.content}</p><CitationList citations={message.citations} /></article>)}</section>; }
