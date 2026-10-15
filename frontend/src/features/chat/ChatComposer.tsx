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
        <div className="input-container">
          <textarea 
            ref={textareaRef}
            aria-label="Ask about this repository" 
            required 
            disabled={disabled}
            value={question} 
            onChange={event => setQuestion(event.target.value)} 
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Ask about this repository..."
          />
          <button 
            className="send-button" 
            disabled={disabled || !question.trim()}
            type="submit"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 11L12 6L17 11M12 18V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
