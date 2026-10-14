# Project State

## Current Milestone

Hybrid active-index retrieval now combines vector and keyword candidates, with file-path weighting and result diversity. R Markdown selection, background ingestion, and structured inline-citation answers remain in place. The user reports the citation display looks better; a fresh browser end-to-end run of hybrid retrieval has not been verified here.

## Approved Decisions

- Build a single-user React and TypeScript web application with a Python/FastAPI backend.
- Support public and private GitHub repositories using the configured server-side GitHub token.
- Use PostgreSQL with pgvector in Docker for persistent repository, index, and chat data.
- Use an app-specific Ollama `github-rag-llama3.1:8k` alias for answers and `nomic-embed-text:latest` for embeddings.
- Keep one persistent conversation per repository, titled from the repository name.
- Offer a visible manual rebuild action; compare default-branch commit SHAs and fully rebuild only when changed.
- Use a curated text-file allowlist and exclude dependencies, generated output, lockfiles, binaries, minified files, and oversized files.
- Link citations to exact GitHub commit, path, and inclusive line range.

## Completed

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

- Try code-symbol and repository-overview questions in the browser after restarting the API; inspect citation relevance and query latency on larger repositories.
- Add a measured context-token budget before increasing the number of returned chunks.
- Restart the API and ask a new question about an indexed repository; verify links appear beside the new answer sections. Existing saved answers without inline markers retain their historical trailing lists.
- Restart the API to load the changed `.env`, then click Rebuild for any existing repository whose `.Rmd` file was previously omitted; verify file/chunk counts and a cited answer.
- Start the separate worker (`cd backend; python -m app.worker`) alongside API, Vite, and PostgreSQL; retry a real-repository import and verify indexed file count and chat citations.
- Decide whether to replace one-blob-per-file GitHub fetching with an archive-based or partial-clone strategy for repositories with hundreds or thousands of useful source files.
- Add deterministic Playwright fixtures for a browser-level end-to-end workflow without requiring live GitHub or Ollama.

## Known Risks

- Full-text ranking currently computes across the active repository's chunks and paths without a dedicated combined search index; profile larger repositories before increasing candidate counts.
- Private-repository access depends on the permissions of the configured GitHub token.
- The 8K context reduces GPU memory use but can truncate long prompts; retrieved-context budgeting has not been implemented.
- The configured GitHub token returned `x-ratelimit-remaining: 0` for a blob request from `sandiim/Score_Prediction`; live import cannot succeed until quota resets. A valid `sandiim/Turbo_Fan_RUL_Prediction` URL currently returns HTTP 429 locally.
- The local Ollama endpoint was unreachable during an earlier ingestion diagnosis; it responded during the current answer-model smoke test. End-to-end repository embedding after this change has not been verified.
- The previously reported HTTP 422 for the Turbo_Fan URL was not reproduced from the plain URL in schema/parser tests; the exact browser request body remains unknown.
- Fetching each selected blob via GitHub REST still spends one API request per file; bounded batches limit waste but do not remove this scalability constraint.
- GitHub's truncated recursive tree response is rejected visibly rather than activated as an incomplete index; a different fetch method is needed for repositories that exceed this API limit.
- The worker downloads selected blobs one at a time to expose accurate progress; large repositories may still take substantial time.
- A stopped worker leaves imports queued; the UI will show “Waiting for worker” until it restarts. An expired running lease gets one automatic retry.
- `.env.example` documents the local database and embedding settings without exposing credentials.

## Verified Commands

Current hybrid-retrieval milestone:

- `cd backend; python -m pytest tests/rag/test_retrieval.py -q` — 5 passed after the query/path-weighting change.
- Read-only PostgreSQL retrieval with real Ollama embeddings over three questions: expected file ranks were 4, 1, and 1 (all within the six returned chunks); before path normalization and weighting, the same questions ranked 6, absent, and 1.
- `cd backend; python -m pytest -q` — 70 passed, one upstream Starlette warning after the final SQL-path adjustment.

Current structured-citation fix:

- A read-only retrieval/completion run for `sandiim/R_analyse_multivari-e` with six chunks produced six paragraphs and valid source markers; no chat message was persisted.
- `cd backend; python -m pytest -q` — 65 passed, one upstream Starlette warning.
- `cd frontend; npm test -- --run` — 7 test files / 10 tests passed.
- `cd frontend; npm run build` — TypeScript and Vite build passed.

Current inline-citation milestone:

- `cd backend; python -m pytest -q` — 62 passed, one upstream Starlette warning.
- `cd frontend; npm test -- --run` — 7 test files / 10 tests passed.
- `cd frontend; npm run build` — TypeScript and Vite build passed.
- A direct local Ollama request with one synthetic README chunk returned an inline `[1]` marker, which resolved to `[README.md:1-2]` without persisting a chat message.
- A real repository chat answer after restarting the API has not yet been checked.

Current R Markdown/context milestone:

- `cd backend; python -m pytest -q` — 59 passed, one upstream Starlette warning.
- `cd frontend; npm test -- --run` — 6 test files / 8 tests passed.
- `cd frontend; npm run build` — TypeScript and Vite build passed.
- `ollama create github-rag-llama3.1:8k -f ollama/Modelfile` — local alias created successfully.
- A local OpenAI-compatible chat-completion request to `github-rag-llama3.1:8k` returned `OK`; `ollama ps` reported context 8192 and 100% GPU placement.
- A live repository rebuild and cited chat answer have not yet been tested after the selection-policy change.

Current background-ingestion milestone:

- `cd backend; alembic upgrade head` — migration applied to the configured local database; `ingestion_jobs` table and new columns inspected.
- `cd backend; alembic upgrade head; python -m pytest -q` — 58 passed, one upstream Starlette warning.
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
