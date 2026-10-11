# Project State

## Current Milestone

Milestone 8 complete — React repository library and cited chat UI.

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

## Next

- Verify the end-to-end workflow and finalize setup, decision, and handoff documentation.

## Known Risks

- Private-repository access depends on the permissions of the configured GitHub token.
- The selected pgvector Docker image must be pulled before PostgreSQL integration tests can run.
- The current `.env` does not yet contain the optional local database and embedding settings; `.env.example` documents them.

## Verified Commands

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
- `cd frontend; npm test -- --run; npm run build` — 2 tests passed; production build passed
