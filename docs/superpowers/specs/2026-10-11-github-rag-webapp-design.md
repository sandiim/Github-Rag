# GitHub Repository RAG Web Application — Design

## Scope

Build a single-user web application that accepts public or private GitHub repository URLs, indexes supported repository files, and answers questions with citations to exact files and line ranges at the indexed commit.

The first release keeps one persistent conversation per repository, presents repositories in a sidebar, and offers a manual rebuild action. Multi-user accounts, incremental reindexing, and automatic polling are out of scope.

## Technology Decisions

- Frontend: React and TypeScript.
- Backend: Python and FastAPI, with Pydantic schemas.
- Database: PostgreSQL with pgvector, run locally in Docker.
- Local models: Ollama `llama3.1` for generation and `nomic-embed-text` for embeddings.
- Credentials: GitHub token and OpenAI-compatible LLM settings remain in `.env`; the frontend never receives them.

## Architecture

```text
React web app
    -> FastAPI API
        -> GitHub adapter -> repository files and commit metadata
        -> RAG services -> Ollama embeddings / answer generation
        -> persistence -> PostgreSQL + pgvector
```

Backend boundaries:

- `api/`: routes and Pydantic schemas only.
- `services/`: repository creation, rebuild orchestration, chat orchestration, and persistence coordination.
- `github/`: URL validation, authenticated repository access, commit lookup, and file discovery.
- `rag/`: file filtering, chunking, embeddings, retrieval, and citation construction.
- `persistence/`: SQLAlchemy models, migrations, repositories, and vector queries.

Frontend boundaries:

- `features/repositories`: repository URL input, sidebar, status, and rebuild controls.
- `features/chat`: messages, composer, loading/error states, and citations.
- `components`: reusable presentational components.
- `api-client`: typed HTTP calls only.
- `types`: shared frontend types.

No API route accesses GitHub, Ollama, or database code directly; routes call services. No frontend feature accesses credentials or database code.

## Indexing and Retrieval

1. Validate and register a GitHub URL.
2. Resolve its default branch and current commit SHA using the configured GitHub token.
3. Fetch supported text files through the GitHub adapter.
4. Include source code, Markdown, JSON, YAML, TOML, Dockerfiles, and common configuration files.
5. Exclude binaries, dependencies, generated/build output, `.git`, lockfiles, minified files, and oversized files.
6. Chunk files with start and end line numbers, generate embeddings, and persist chunks and vectors with the commit SHA.
7. Embed a question, retrieve relevant chunks, and instruct Llama to answer only from retrieved context.
8. Return citations containing path, line range, and a GitHub URL pinned to the indexed commit.

## Persistence Model

- `Repository`: URL, owner/name, default branch, active indexed commit SHA, status, last rebuild time, and error state.
- `SourceFile`: repository, commit SHA, path, source text/checksum, and metadata.
- `Chunk`: source file, text, start/end lines, embedding vector, and retrieval metadata.
- `Conversation`: one durable conversation per repository, titled from the repository name.
- `Message`: user or assistant content and timestamp.
- `Citation`: message, source file path, line range, and commit-pinned URL.
- `RebuildRecord`: prior/current commit SHA, lifecycle timestamps, outcome, and readable failure detail.

## Rebuild Behavior

The user triggers rebuild from the interface. The backend compares the remote default-branch commit SHA with the active indexed SHA. If unchanged, it reports that no rebuild is needed. If changed, it fully indexes the new commit into a new index version and only activates it after success. Existing data remains usable on a failed rebuild, and old messages retain their original commit-pinned citations.

## API Shape

- Create, list, and fetch repositories.
- Fetch a repository's persistent conversation and messages.
- Send a chat message to a repository conversation.
- Trigger and inspect repository rebuild status.

Exact endpoint and schema names are implementation details, but each response uses typed Pydantic models.

## Reliability and Security

- Report invalid URLs, access failures, unsupported files, missing local models, and database failures with actionable messages.
- When retrieval has insufficient evidence, say so rather than inventing repository facts.
- Never send `.env` values to the browser or store tokens in the database, logs, messages, or Git.
- Build a replacement index before switching the active version.

## Verification

- Unit-test each module boundary.
- Run backend integration tests against PostgreSQL/pgvector.
- Run frontend end-to-end tests for repository creation, indexing, chat, citations, and rebuild.
- Verify citations resolve to the indexed commit and stated file lines.

## Project Memory and Handoff

Future work maintains:

- `AGENT.md`: agent rules, architecture boundaries, security rules, and workflow.
- `PROJECT_STATE.md`: completed work, current work, next tasks, decisions, risks, and verified commands.
- `docs/architecture.md`: a concise current architecture reference derived from this design.
- `docs/decisions/`: short decision records for major future changes.
- `README.md`: human setup and run instructions.

Every future agent begins by reading `AGENT.md`, `PROJECT_STATE.md`, and the relevant architecture or decision documentation.
