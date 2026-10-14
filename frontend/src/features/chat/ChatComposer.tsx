import { useState } from "react";

export function ChatComposer({ disabled, onSend }: {
  disabled: boolean;
  onSend: (question: string) => Promise<void>;
}) {
  const [question, setQuestion] = useState("");
  return <form onSubmit={async event => {
    event.preventDefault();
    try {
      await onSend(question);
      setQuestion("");
    } catch {
      // Keep the question for another attempt; the parent displays the error.
    }
  }}>
    <label>Ask about this repository
      <textarea aria-label="Ask about this repository" required disabled={disabled}
        value={question} onChange={event => setQuestion(event.target.value)} />
    </label>
    <button disabled={disabled}>Send</button>
  </form>;
}
