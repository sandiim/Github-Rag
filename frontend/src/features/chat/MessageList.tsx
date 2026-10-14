import type { ReactNode } from "react";

import type { Citation, Message } from "../../types/api";
import { CitationList } from "./CitationList";

const sourceMarker = /\[([^\[\]\r\n]+):(\d+)-(\d+)\]/g;

function answerParts(content: string, citations: Citation[]): { parts: ReactNode[]; hasLinks: boolean } {
  const parts: ReactNode[] = [];
  let start = 0;
  let hasLinks = false;

  for (const match of content.matchAll(sourceMarker)) {
    const citation = citations.find(source =>
      source.path === match[1] &&
      source.startLine === Number(match[2]) &&
      source.endLine === Number(match[3])
    );
    if (!citation) continue;

    parts.push(content.slice(start, match.index));
    parts.push(<a key={match.index} href={citation.url} target="_blank" rel="noreferrer">
      {citation.path}:{citation.startLine}-{citation.endLine}
    </a>);
    start = match.index + match[0].length;
    hasLinks = true;
  }

  parts.push(content.slice(start));
  return { parts, hasLinks };
}

export function MessageList({ messages }: { messages: Message[] }) {
  return <section className="messages" aria-live="polite">
    {messages.map((message, index) => {
      const { parts, hasLinks } = answerParts(message.content, message.citations);
      return <article className={message.role} key={`${message.role}-${index}`}>
        <strong>{message.role === "user" ? "You" : "Repository"}</strong>
        <p>{message.role === "assistant" ? parts : message.content}</p>
        {message.role === "assistant" && !hasLinks && <CitationList citations={message.citations} />}
      </article>;
    })}
  </section>;
}
