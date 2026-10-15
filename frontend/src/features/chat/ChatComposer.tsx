import { useState, useRef, useEffect } from "react";

export function ChatComposer({ disabled, onSend }: {
  disabled: boolean;
  onSend: (question: string) => Promise<void>;
}) {
  const [question, setQuestion] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [question]);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      const form = event.currentTarget.closest("form");
      form?.requestSubmit();
    }
  };

  return (
    <div className="composer">
      <form onSubmit={async event => {
        event.preventDefault();
        if (!question.trim()) return;
        const currentQuestion = question;
        setQuestion("");
        try {
          await onSend(currentQuestion);
        } catch {
          setQuestion(currentQuestion);
        }
      }}>
        <label>Ask about this repository
          <textarea 
            ref={textareaRef}
            aria-label="Ask about this repository" 
            required 
            disabled={disabled}
            value={question} 
            onChange={event => setQuestion(event.target.value)} 
            onKeyDown={handleKeyDown}
            rows={1}
          />
        </label>
        <button disabled={disabled || !question.trim()}>Send</button>
      </form>
    </div>
  );
}
