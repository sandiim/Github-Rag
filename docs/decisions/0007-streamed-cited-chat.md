# Stream structured cited answers as NDJSON

## Decision

Keep the existing synchronous chat endpoint and add a POST stream endpoint that emits newline-delimited `status`, `delta`, `checkpoint`, `complete`, and `error` records. Continue using Ollama's structured JSON-schema answer; decode only paragraph text for provisional display, then validate source IDs and publish citation links at paragraph checkpoints. Persist only the final validated turn.

## Rationale

The application needs to show progress before a full local-model completion arrives without exposing raw JSON or giving up the current inline citation behavior. A `fetch` body reader supports POST requests and cancellation in the existing browser client. A generator-owned database session avoids depending on the installed FastAPI version's early cleanup of request-scoped dependencies for `StreamingResponse`.

## Tradeoffs

Provisional text can be revised or removed if its section lacks valid citations. The first readable text appears after JSON structural tokens, not at the model's first output token. A dropped connection after database commit but before the final event can leave a saved answer that the browser has not seen; reloading the conversation recovers it. The stream holds a local Ollama connection while generating and adds incremental parsing and frontend state handling, but no new service, database migration, or dependency.
