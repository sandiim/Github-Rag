# Stream cited repository answers

## Goal

Show readable answer text as Ollama produces it, with a calm waiting indicator during retrieval and pauses. Keep the existing grounded-section validation, commit-pinned citations, and durable conversation semantics.

## Transport and ownership

Keep the existing `POST /repositories/{id}/chat` JSON endpoint for compatibility. Add `POST /repositories/{id}/chat/stream`, returning newline-delimited JSON (`application/x-ndjson`) over a normal `fetch` response. Events are `status` (`retrieving` or `generating`), `delta` (new provisional readable text), `checkpoint` (complete validated paragraphs with citation records), `complete` (committed final answer and citations), and `error` (safe failure message). Every record ends in one newline and is independently parseable. Do not stream raw model JSON or repository source text.

The streaming service opens a database session inside its response generator rather than relying on the request-scoped session dependency. It checks repository/index readiness before headers are sent, retrieves active-index chunks, streams Ollama's existing OpenAI-compatible JSON-schema answer, and commits the same validated final answer and citations as the non-streaming endpoint. If generation, parsing, persistence, or transport fails, roll back; never persist an incomplete assistant answer. On a client disconnect, close the model stream and database session.

## Provisional text and citations

The completion adapter continues to request structured `sections` with `text` and `source_ids`. An incremental parser extracts only decoded `text` string fragments for `delta` events. When a section object closes, validate its source IDs against the retrieved chunks, format its marker references, and emit a `checkpoint` so links can appear after that paragraph. At the end, validate the complete JSON, persist its canonical answer, and emit `complete`; the final event replaces any provisional UI text. Invalid or uncited sections are dropped at checkpoints and from the saved answer. An empty validated answer uses the existing insufficient-evidence sentence.

## Frontend behavior

The typed API client reads and validates NDJSON records from `response.body` while tolerating network chunk boundaries and UTF-8 splits. The chat panel shows an optimistic question and a provisional assistant message. A steady, reduced-motion-aware indicator shows retrieval/generation state and reappears after a short gap between fragments. Each `delta` extends the provisional text; each `checkpoint` replaces it with validated paragraphs plus links; `complete` replaces it with the durable answer. Disable duplicate sends during one stream; abort an in-flight stream when switching repositories. On an error or truncated stream, remove the provisional assistant draft, show a retryable error, and refresh the saved conversation so UI and database agree.

## Verification

Test fragmented and escaped model JSON, section validation, full-answer parity with the existing non-streaming path, stream errors and rollback, NDJSON parsing across arbitrary byte boundaries, inline citation checkpoints, waiting/reduced-motion UI states, and repository switching. Run backend tests, frontend tests, and frontend build. Smoke-test the local Ollama stream without printing secrets.

## Tradeoffs

Provisional text has not yet passed citation validation and may be revised or removed at a checkpoint. Structured JSON means the first visible text begins when the model reaches a section's `text` field, not at its initial `{` token. The existing synchronous endpoint remains available; the new path adds no dependency or schema migration.
