# Project State

## Current Milestone

Durable background ingestion is implemented and covered by deterministic tests. Live imports of the user's larger GitHub repositories have not yet been reverified.

## Approved Decisions

- Build a single-user React and TypeScript web application with a Python/FastAPI backend.
- Support public and private GitHub repositories using the configured server-side GitHub token.
- Use PostgreSQL with pgvector in Docker for persistent repository, index, and chat data.
- Use local Ollama `llama3.1:latest` for answers and `nomic-embed-text:latest` for embeddings.
- Keep one persistent conversation per repository, titled from the repository name.
- Offer a visible manual rebuild action; compare default-branch commit SHAs and fully rebuild only when changed.
- Use a curated text-file allowlist and exclude dependencies, generated output, lockfiles, binaries, minified files, and oversized files.
- Link citations to exact GitHub commit, path, and inclusive line range.

## Completed

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
- Added a local Ollama embedding adapter for `nomic-embed-text:latest`.
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

- Start the separate worker (`cd backend; python -m app.worker`) alongside API, Vite, and PostgreSQL; retry a real-repository import and verify indexed file count and chat citations.
- Decide whether to replace one-blob-per-file GitHub fetching with an archive-based or partial-clone strategy for repositories with hundreds or thousands of useful source files.
- Add deterministic Playwright fixtures for a browser-level end-to-end workflow without requiring live GitHub or Ollama.

## Known Risks

- Private-repository access depends on the permissions of the configured GitHub token.
- The configured GitHub token returned `x-ratelimit-remaining: 0` for a blob request from `sandiim/Score_Prediction`; live import cannot succeed until quota resets. A valid `sandiim/Turbo_Fan_RUL_Prediction` URL currently returns HTTP 429 locally.
- The configured local Ollama endpoint at `localhost:11434` was unreachable during diagnosis, so end-to-end embedding was not verified.
- The previously reported HTTP 422 for the Turbo_Fan URL was not reproduced from the plain URL in schema/parser tests; the exact browser request body remains unknown.
- Fetching each selected blob via GitHub REST still spends one API request per file; bounded batches limit waste but do not remove this scalability constraint.
- The worker downloads selected blobs one at a time to expose accurate progress; large repositories may still take substantial time.
- A stopped worker leaves imports queued; the UI will show “Waiting for worker” until it restarts. An expired running lease gets one automatic retry.
- `.env.example` documents the local database and embedding settings without exposing credentials.

## Verified Commands

Current background-ingestion milestone:

- `cd backend; alembic upgrade head` — migration applied to the configured local database; `ingestion_jobs` table and new columns inspected.
- `cd backend; alembic upgrade head; python -m pytest -q` — 57 passed, one upstream Starlette warning.
- Plain `https://github.com/sandiim/Turbo_Fan_RUL_Prediction` passed the request-schema and URL parser in isolation; browser submission has not been reverified.
- `cd backend; python -m pytest tests/api/test_ingestion_flow.py -q` — 1 passed, one upstream Starlette warning.
- `cd frontend; npm test -- --run` — 6 test files / 8 tests passed, including add/poll/chat-ready behavior.
- `cd frontend; npm run build` — TypeScript and Vite build passed.

Historical earlier milestones:

- `python --version` — Python 3.13.12
- `node --version` — v24.20.0
- `docker --version` — Docker version 29.1.2
- `ollama list` — `llama3.1:latest` and `nomic-embed-text:latest` installed
- `cd backend; python -m pytest tests/test_settings.py tests/test_health.py -q` — 2 passed
- `cd backend; alembic upgrade head; python -m pytest tests/persistence -q` — 3 passed from a fresh PostgreSQL volume
- `cd backend; python -m pytest tests/github/test_client.py tests/rag/test_file_filter.py -q` — 14 passed
- `cd backend; alembic upgrade head; python -m pytest -q` — 25 passed (one upstream Starlette deprecation warning)
- `cd backend; python -m pytest -q` — 29 passed (one upstream Starlette deprecation warning)
- `cd backend; alembic upgrade head; python -m pytest -q` — 33 passed (one upstream Starlette deprecation warning)
- `cd backend; python -m pytest -q` — 44 passed (one upstream Starlette deprecation warning) after ingestion hardening.
- `cd frontend; npm test -- --run` — 4 test files / 4 tests passed after error-display changes.
- `cd frontend; npm run build` — production build passed after error-display changes.
- `cd frontend; npm test -- --run; npm run build` — 2 tests passed; production build passed
- `cd backend; alembic upgrade head; python -m pytest -q` — 33 passed (one upstream Starlette deprecation warning)
