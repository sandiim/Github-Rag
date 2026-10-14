# Streamed Cited Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display repository answers incrementally with validated inline citations and a waiting indicator.

**Architecture:** The existing structured Ollama response streams through an incremental section parser, then a streaming chat service emits NDJSON events and persists only the validated final answer. The React API client decodes the stream; the chat UI renders provisional text, citation checkpoints, and a reduced-motion-aware waiting indicator.

**Tech Stack:** Python 3.13, FastAPI 0.115, httpx, SQLAlchemy, React, TypeScript, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-14-streamed-cited-chat-design.md`

## Global Constraints

- Keep the existing non-streaming chat endpoint and saved-conversation format.
- Preserve the user's pre-existing timeout edit in `backend/app/rag/completion.py`.
- Do not add dependencies or database migrations.
- Do not expose `.env` values or raw model JSON to the browser.
- Persist only the final validated answer; aborts and errors must not leave partial chat rows.

---

### Task 1: Structured model streaming

**Files:** Modify `backend/app/rag/completion.py`; create `backend/app/rag/section_stream.py`; test `backend/tests/rag/test_section_stream.py` and `backend/tests/rag/test_completion.py`.

**Interfaces:** `SectionStream.feed(fragment: str) -> list[SectionEvent]`; `CompletionClient.stream_answer(question, context) -> Iterator[AnswerStreamEvent]`. A section event carries a decoded text delta or a validated paragraph checkpoint. The final event carries the same canonical marker-formatted text as `answer()`.

- [x] Write tests first: fragments such as `'{"sections":[{"text":"Hel'`, `'lo\\nworld","source_ids":[1]}]}'` must produce readable deltas, a cited checkpoint, and a canonical final answer; malformed/uncited sections must not survive validation.
- [x] Run `cd backend; python -m pytest tests/rag/test_section_stream.py tests/rag/test_completion.py -q` and confirm the new tests fail for missing streaming behavior.
- [x] Implement a small incremental JSON string/object scanner in `section_stream.py`; reuse the existing schema and final section renderer in `completion.py`, and consume `data:` lines from `httpx.Client.stream(..., json={**payload, "stream": True})`.
- [x] Rerun focused tests; ensure the existing synchronous `answer()` tests remain green.

### Task 2: HTTP stream and durable chat

**Files:** Modify `backend/app/services/chat.py`, `backend/app/api/dependencies.py`, and `backend/app/api/repositories.py`; create `backend/tests/api/test_chat_stream.py` and extend `backend/tests/services/test_chat.py`.

**Interfaces:** `POST /repositories/{repository_id}/chat/stream` emits newline-delimited JSON records: `status`, `delta`, `checkpoint`, `complete`, `error`. The streaming dependency supplies a session factory, not a request-scoped session. Completion/checkpoint records use the existing citation shape.

- [x] Write failing tests that read a streamed response and assert event order, JSON-line framing, valid citation URLs, committed history on success, and no partial history on model failure.
- [x] Run `cd backend; python -m pytest tests/api/test_chat_stream.py tests/services/test_chat.py -q` and confirm failures are for missing endpoint/stream behavior.
- [x] Add a shared final-answer persistence path in the chat service, a generator-owned session, readiness preflight before response headers, and safe `error` events with rollback. Keep the existing JSON route unchanged.
- [x] Rerun focused and full backend tests.

### Task 3: Browser stream and waiting state

**Files:** Modify `frontend/src/api-client/client.ts`, `frontend/src/App.tsx`, `frontend/src/features/chat/ChatPanel.tsx`, `frontend/src/features/chat/MessageList.tsx`, and `frontend/src/styles.css`; add API-client and chat UI tests.

**Interfaces:** `ApiClient.askStream(repositoryId, question, onEvent, signal)` invokes the NDJSON endpoint. `MessageList` accepts an optional streaming state; the completed message retains the existing `Message` type and citation renderer.

- [x] Write failing Vitest cases for UTF-8/line fragmentation, draft-to-checkpoint-to-complete rendering, waiting indicator, error recovery, and disabled duplicate send.
- [x] Run `cd frontend; npm test -- --run` and confirm the new cases fail for the missing stream behavior.
- [x] Implement fetch-body decoding and event validation, optimistic draft updates, abort-on-repository-switch, and a subtle CSS indicator with `prefers-reduced-motion` handling.
- [x] Run `cd frontend; npm test -- --run` and `npm run build`.

### Task 4: Verify and document

**Files:** Update `docs/architecture.md`, `docs/decisions/`, and `PROJECT_STATE.md`.

- [x] Run `cd backend; python -m pytest -q`, `cd frontend; npm test -- --run`, `cd frontend; npm run build`, and `git diff --check`; record actual outcomes.
- [x] Run a read-only local Ollama streaming smoke test and inspect event ordering without logging credentials or source text.
- [x] Commit only milestone files with `feat: stream cited chat answers`; leave unrelated user edits unstaged.
