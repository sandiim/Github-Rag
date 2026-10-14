# Use structured sections for new cited answers

The local `llama3.1` model sometimes omitted citation markers from free-form answers despite an explicit prompt. Use Ollama's OpenAI-compatible JSON-schema response format in one completion call instead. Each returned section has paragraph text and numeric source IDs; the backend validates IDs against retrieved chunks and places file-line references beside the section before saving it.

This avoids attaching retrieved sources to unrelated paragraphs by position and avoids a second model call. It does not prove that a cited source semantically supports every claim; that remains an evaluation concern. Answers saved before this change keep their separate citation lists.
