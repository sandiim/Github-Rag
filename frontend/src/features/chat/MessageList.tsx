import { useState, useEffect, useRef } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Citation, Message } from "../../types/api";
import { CitationList } from "./CitationList";

export type StreamingState = { stage: "retrieving" | "generating"; waiting: boolean };

const sourceMarker = /\[([^\[\]\r\n]+):(\d+)-(\d+)\]/g;

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button className="code-copy-btn" onClick={handleCopy} title="Copy code">
      {copied ? "✓" : "📋"}
    </button>
  );
}

export function MessageList({ 
  messages, 
  streaming = null,
  onScrollToBottom,
  onCitationClick
}: { 
  messages: Message[]; 
  streaming?: StreamingState | null;
  onScrollToBottom: (visible: boolean) => void;
  onCitationClick: (citation: Citation) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (!scrollRef.current) return;
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      onScrollToBottom(!isAtBottom);
    };

    const container = scrollRef.current;
    container?.addEventListener("scroll", handleScroll);
    return () => container?.removeEventListener("scroll", handleScroll);
  }, [onScrollToBottom]);

  const renderContent = (message: Message) => {
    if (message.role === "user") return <p>{message.content}</p>;

    // Pre-process content to replace [path:start-end] markers with Markdown links [index](url)
    let processedContent = message.content;
    message.citations.forEach((c, i) => {
      const marker = `[${c.path}:${c.startLine}-${c.endLine}]`;
      const link = `[${i + 1}](${c.url})`;
      processedContent = processedContent.replaceAll(marker, link);
    });

    return (
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p>{children}</p>,
          a: ({ href, children }) => (
            <a 
              href={href} 
              onClick={(e) => {
                e.preventDefault();
                const citation = message.citations.find(c => c.url === href);
                if (citation) {
                  onCitationClick(citation);
                } else {
                  window.open(href, "_blank");
                }
              }}
              target="_blank" 
              rel="noreferrer" 
              className="citation-link"
            >
              {children}
            </a>
          ),
          code({ node, inline, className, children, ...props }: any) {
            const match = className?.replace("language-", "");
            const content = String(children).replace(/\\n$/, "");

            if (inline) {
              return <code className="inline-code" {...props}>{children}</code>;
            }

            return (
              <div className="code-block-container">
                <div className="code-header">
                  <span className="code-lang">{match || "text"}</span>
                  <CopyButton text={content} />
                </div>
                <SyntaxHighlighter 
                  style={oneDark} 
                  language={match || "text"} 
                  PreTag="div" 
                  customStyle={{ margin: 0, padding: "1rem", fontSize: "0.875rem" }}
                  {...props}
                >
                  {content}
                </SyntaxHighlighter>
              </div>
            );
          }
        }}
      >
        {processedContent}
      </ReactMarkdown>
    );
  };

  return (
    <section 
      className="messages-viewport" 
      ref={scrollRef} 
      aria-live={streaming ? "off" : "polite"}
    >
      <div className="messages-content">
        {messages.map((message, index) => {
          const active = streaming && index === messages.length - 1 && message.role === "assistant";
          const status = streaming?.stage === "retrieving" ? "Searching repository" :
            message.content ? "Waiting for more" : "Preparing answer";
          
          return (
            <div className={`message-group ${message.role}`} key={`${message.role}-${index}`}>
              <article className="bubble">
                {renderContent(message)}
                {message.role === "assistant" && 
                 !message.content.includes("[") && 
                 message.citations.length > 0 && (
                  <CitationList citations={message.citations} />
                )}
                {active && (
                  <span className={`stream-status${streaming?.waiting ? "" : " is-idle"}`} role="status">
                    <span className="stream-dots" aria-hidden="true"><i /><i /><i /></span>
                    {status}
                  </span>
                )}
              </article>
            </div>
          );
        })}
      </div>
    </section>
  );
}
