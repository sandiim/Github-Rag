# Project State

## Current Milestone

The frontend redesign is underway, transitioning the application to a professional "Dark Developer Tool" aesthetic. The redesign focuses on establishing a focused developer workspace with a clear hierarchy, improved readability, and responsive behavior.

### Completed UI/UX Improvements:
- **Core Palette & Layout:** Implemented a restrained dark theme using CSS custom properties for surfaces, accents, and status colors.
- **Workspace Hierarchy:** 
    - Established a structured sidebar with product headers, section titles, and a dedicated index status area.
    - Constrained the chat workspace width (760px) and implemented a sticky composer for improved reading comfort.
- **Responsive Navigation:**
    - Implemented a mobile-first off-canvas sidebar with a fixed toggle button.
    - Added automatic sidebar closure upon repository selection on narrow screens.
- **Chat Polish:** 
    - Styled "user" vs "assistant" turns with distinct backgrounds and alignment.
    - Refined citation rendering into a "pill" based system with subtle backgrounds and borders.
- **Composer Ergonomics:** 
    - Added auto-expanding textarea that grows with content.
    - Implemented `Cmd/Ctrl+Enter` for sending messages, keeping `Enter` for new lines.
    - Immediate input clearing upon send with a restoration mechanism on failure.
- **Motion & Fluidity:**
    - Added slide-up fade-in animations for new messages.
    - Refined transition curves for sidebar navigation.

## Approved Decisions

- Build a single-user React and TypeScript web application with a Python/FastAPI backend.
- Support public and private GitHub repositories using the configured server-side GitHub token.
- Use PostgreSQL with pgvector in Docker for persistent repository, index, and chat data.
- Use an app-specific Ollama `github-rag-llama3.1:8k` alias for answers and `nomic-embed-text:latest` for embeddings.
- Keep one persistent conversation per repository, titled from the repository name.
- Offer a visible manual rebuild action; compare default-branch commit SHAs and fully rebuild when the commit or file-selection policy version changes.
- Use a curated text-file allowlist and exclude dependencies, generated output, lockfiles, binaries, minified files, and oversized files.
- Link citations to exact GitHub commit, path, and inclusive line range.

## Completed

- Added a streaming chat endpoint and a generator-owned database session; the original JSON chat endpoint remains available.
- Added incremental structured-answer parsing, readable text deltas, paragraph citation checkpoints, and final-only persistence with rollback on failure or interruption.
- Added a streaming frontend reader, optimistic answer display, wait animation with reduced-motion support, abort-on-repository-switch, and retryable error handling that keeps the question in the composer.
- Added PostgreSQL full-text candidates alongside pgvector results, with normalized file paths, path weighting, reciprocal-rank fusion, and per-file diversity before the six-chunk answer context.
- Added deterministic ranking and query-scope tests; no migration or reindex is required for this query-only retrieval change.
- Switched new completion responses from free-form citation-marker instructions to single-call JSON-schema sections with validated source IDs. Answers with no valid cited section no longer receive a trailing list of every retrieved chunk.
- Reproduced the citation issue with the R Markdown repository: a six-chunk free-form answer omitted markers; a structured completion over the same six chunks returned cited sections.
- Added numbered source markers to the answer prompt, resolved valid markers to stable file-line spans before saving, and rendered verified links inline instead of as a trailing list. Older unmarked answers retain their existing source list.
- Allowed R Markdown (`.rmd`/`.Rmd`) source files and raised the selection policy to version 3 so a manual rebuild can reindex an unchanged repository.
- Added `ollama/Modelfile` with `num_ctx 8192`, created the local answer-model alias, and pointed the private `.env` and setup example at it and Ollama's local OpenAI-compatible endpoint.
- Documented the local model setup and the context-window tradeoff in decision 0004.
- Added durable queued/running/completed/failed ingestion jobs, a separate worker with leases and one automatic recovery attempt, and retryable safe errors.
- Changed repository creation/rebuild to HTTP 202 enqueueing; the UI polls progress and keeps an existing active index chat-ready during rebuild.
- Versioned the file-selection policy and excluded `data/` and `datasets/` before blob download.
- Added an API-to-worker deterministic integration test and worker/job regression tests.
- Removed the previous implementation and initialized a new Git repository on `feat/github-rag-mvp`.
- Approved the architecture design and implementation plan.
- Verified local tooling: Python 3.13.12, Node 24.20.0, Docker 29.1.2, Ollama 0.34.4, `llama3.1:latest`, and `nomic-embed-text:latest`.
- Committed project contract and local PostgreSQL/pgvector configuration as `23ab91a`.
- Added typed environment settings and a FastAPI application factory with `GET /health`.
- Added SQLAlchemy models for repositories, conversations, source files, chunks, messages, citations, and rebuild records.
- Added the PostgreSQL session factory and an initial Alembic migration with pgvector support.
- Added authenticated GitHub repository parsing, default-branch/commit resolution, and recursive text-blob discovery.
- Added an allowlist filter that excludes dependencies, generated output, lockfiles, binaries, minified files, and oversized content.
- Added line-preserving chunks with configurable overlap and inclusive source-line ranges.
- Added a local Ollama embedding adapter for `nomic-embed-text: latest`.
- Added replacement index versions with atomic activation only after filtered files, chunks, and embeddings persist successfully.
- Added unchanged-commit skipping and failed-rebuild protection that retains the previous active index.
- Added active-index-only vector retrieval and OpenAI-compatible grounded completion generation.
- Added durable user and assistant messages with a repository's single persistent conversation.
- Added commit-pinned GitHub citation URLs and persisted citation records for retrieved source chunks.
- Added typed repository creation, listing, detail, rebuild, conversation, and chat API endpoints.
- Added dependency injection for database, GitHub, Ollama embedding, retrieval, and completion services.
- Added safe API error mapping for invalid URLs, missing repositories, and repositories without an active index.
- Added deterministic per-conversation message sequence numbers and a migration so chat history always resumes in send order.
- Added a Vite React and TypeScript web application with a typed backend API client.
- Added repository library selection, GitHub URL submission, manual rebuild action, durable chat display, and commit-pinned citation links.
- Added responsive two-pane styling and frontend component tests for repository selection and citation rendering.
- Documented the verified local startup sequence and configured Vite to proxy API requests to FastAPI during development.
- Recorded the PostgreSQL/pgvector and full-versioned-rebuild architecture decisions.
- Excluded committed `venv/` environments and `mlruns/` generated artifacts before GitHub blob downloads and chunking.
- Bounded GitHub blob download scheduling to batches of eight, stopping further batches on rate-limit failure.
- Mapped GitHub primary rate-limit responses to HTTP 429 with the reset time instead of an opaque 500.
- Narrowed HTTP 422 mapping to invalid repository URLs; other indexing `ValueError`s no longer masquerade as URL errors.
- Increased the local Ollama embedding read timeout and displayed import/validation errors in the web form.

## Next

- Upgrade the "Empty State" from a simple text block to a structured "Quick Start" grid with guidance cards.
- Enhance navigation depth with an active-state accent bar for selected repositories and a "Clear Chat" action in the workspace header.
- Implement hover-previews (tooltips) for citations to allow source verification without leaving the chat.
- Verify the final redesign at desktop and narrow viewport sizes, including keyboard focus and reduced-motion behavior; run frontend tests and build and report actual results.
- Add deterministic browser-level end-to-end coverage for streaming, citations, and saved-conversation reload when practical; the user's positive browser report is not a formal test record.
- Profile streamed completion latency and connection behavior for long answers; keep an eye on the 8K context limit.
- Try code-symbol and repository-overview questions in the browser after restarting the API; inspect citation relevance and query latency on larger repositories.
- Add a measured context-token budget before increasing the number of returned chunks.
- Decide whether to replace one-blob-per-file GitHub fetching with an archive-based or partial-clone strategy for repositories with hundreds or thousands of useful source files.

## Known Risks

- Structured JSON starts with non-visible syntax tokens, so streaming improves perceived latency but does not make Ollama generate faster; a malformed or uncited provisional paragraph may be removed at its checkpoint.
- Full-text ranking currently computes across the active repository's chunks and paths without a dedicated combined search index; profile larger repositories before increasing candidate counts.
- Private-repository access depends on the permissions of the configured GitHub token.
- The 8K context reduces GPU memory use but can truncate long prompts; retrieved-context budgeting has not been implemented.
- The configured GitHub token returned `x-ratelimit-remaining: 0` for a blob request from `sandiim/Score_Prediction`; live import cannot succeed until quota resets. A valid `sandiim/Turbo_Fan_RUL_Prediction` URL currently returns HTTP 429 locally.
- The local Ollama endpoint was unreachable during an earlier ingestion diagnosis; it responded during the current answer-model smoke test. End-to-end repository embedding after this change has not been verified.
- The previously reported HTTP 422 for the Turbo_Fan URL was not reproduced from the plain URL in schema/parser tests; the exact browser request body remains unknown.
- Fetching each selected blob via GitHub REST still spends one API request per file; bounded batches limit waste but do not remove this scalability constraint.
- GitHub's truncated recursive tree response is rejected visibly rather than activated as an incomplete index; a different fetch method is needed for repositories that exceed this API limit.
- The worker downloads selected blobs one at a time to expose accurate progress; large repositories may still take some time.
- A stopped worker leaves imports queued; the UI will show “Waiting for worker” until it restarts. An expired running lease gets one automatic retry.
- `.env.example` documents the local database and embedding settings without exposing credentials.

## Verified Commands

Current streamed-chat milestone:
- `cd backend; python -m pytest -q` — 84 passed, one upstream Starlette warning.
- `cd frontend; npm test -- --run` — 16 passed across 8 files.
- `cd frontend; npm run build` — TypeScript and Vite build passed.
- Read-only local Ollama structured stream smoke test: 10 draft deltas, one paragraph checkpoint, one complete event, and a valid source marker; no chat message was persisted.
