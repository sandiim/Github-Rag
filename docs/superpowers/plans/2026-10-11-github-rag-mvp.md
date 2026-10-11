# GitHub Repository RAG MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-user web application that indexes public or private GitHub repositories and answers questions with commit-pinned file-and-line citations.

**Architecture:** React/TypeScript provides the repository library and one durable chat per repository. FastAPI owns repository, rebuild, and chat workflows; dedicated adapters isolate GitHub and Ollama; PostgreSQL/pgvector persists repository versions, source chunks, conversations, messages, and citations.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL with pgvector, Ollama, React, TypeScript, Vite, Vitest, Playwright, Docker Compose, pytest.

**Spec:** `docs/superpowers/specs/2026-10-11-github-rag-webapp-design.md`

## Global Constraints

- Keep GitHub and model credentials in `.env`; never expose or log them.
- Use the installed local Ollama models `llama3.1:latest` and `nomic-embed-text:latest`.
- Keep FastAPI routes thin; API routes call services, and services depend on interfaces rather than framework globals.
- Index only allowlisted text files; exclude generated, dependency, binary, lockfile, minified, and oversized content.
- Every repository citation uses the indexed commit SHA, source path, and inclusive line range.
- Rebuild into a replacement index version and activate it only after success.
- Add tests with every executable behavior change; run the narrowest relevant tests before broader verification.

---

## File Structure

```text
backend/
  app/
    api/                 # routes and Pydantic schemas
    core/                # settings and error mapping
    github/              # authenticated GitHub adapter and file discovery
    persistence/         # SQLAlchemy models, session, repositories, migrations
    rag/                 # filters, chunks, Ollama adapter, retrieval, citations
    services/            # repository, rebuild, and chat orchestration
  tests/
frontend/
  src/
    api-client/          # typed HTTP transport
    features/repositories/
    features/chat/
    components/
    types/
  src/test/
docker-compose.yml       # PostgreSQL + pgvector only
.env.example             # names only; no secrets
AGENT.md                 # durable agent rules
PROJECT_STATE.md         # current handoff state
docs/architecture.md     # concise architecture reference
README.md                # setup and run instructions
```

### Task 1: Establish the Project Contract and Local Infrastructure

**Files:**
- Modify: `AGENT.md`
- Create: `PROJECT_STATE.md`
- Create: `docs/architecture.md`
- Create: `README.md`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Modify: `.gitignore`

**Interfaces:**
- Produces the documented commands and environment-variable contract every later task uses.
- Defines `DATABASE_URL`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`, `OLLAMA_BASE_URL`, and `EMBEDDING_MODEL`.

- [ ] **Step 1: Record the initial handoff state**

Write `PROJECT_STATE.md` with these sections: `Current milestone`, `Approved decisions`, `Completed`, `Next`, `Known risks`, and `Verified commands`. Record the approved stack, the manual full-rebuild rule, the single-conversation-per-repository rule, and the requirement to read this file before continuation work.

- [ ] **Step 2: Write documentation and local service configuration**

Create a Docker Compose service named `postgres` using a pinned `pgvector/pgvector` image, a named volume, port `5432`, a health check using `pg_isready`, and database/user/password values sourced from environment variables. Add `.env`, virtual environments, Node artifacts, test caches, and local database volumes to `.gitignore`. Put only names and safe examples in `.env.example`.

- [ ] **Step 3: Validate the local service configuration**

Run:

```powershell
docker compose config
```

Expected: Compose prints a resolved configuration without secrets.

- [ ] **Step 4: Commit the project contract**

```powershell
git add AGENT.md PROJECT_STATE.md docs/architecture.md README.md .env.example .gitignore docker-compose.yml backend/tests/test_settings_contract.py
git commit -m "chore: establish project contract and local services"
```

### Task 2: Create the Backend Application Shell and Settings

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/settings.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes.py`
- Create: `backend/tests/test_health.py`
- Test: `backend/tests/test_settings_contract.py`

**Interfaces:**
- Produces `Settings` with `database_url: str`, `github_token: str`, `openai_api_key: str`, `openai_base_url: str`, `llm_model: str`, `ollama_base_url: str`, and `embedding_model: str`.
- Produces `create_app() -> FastAPI` and `GET /health` returning `{"status": "ok"}`.

- [ ] **Step 1: Write the failing settings-contract test**

```python
from app.core.settings import Settings


def test_settings_require_expected_environment_names() -> None:
    fields = Settings.model_fields
    expected = {
        "database_url",
        "github_token",
        "openai_api_key",
        "openai_base_url",
        "llm_model",
        "ollama_base_url",
        "embedding_model",
    }
    assert expected <= set(fields)
```

- [ ] **Step 2: Write the failing health-route test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend; python -m pytest tests/test_health.py tests/test_settings_contract.py -q`

Expected: FAIL because `app.main` and `app.core.settings` do not exist.

- [ ] **Step 4: Implement the minimal application shell**

```python
def create_app() -> FastAPI:
    app = FastAPI(title="GitHub Repository RAG")
    app.include_router(router)
    return app


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Use `pydantic-settings` for `Settings`; fail startup with a readable validation error when required environment values are absent.

- [ ] **Step 5: Run backend shell tests**

Run: `cd backend; python -m pytest tests/test_health.py tests/test_settings_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the backend shell**

```powershell
git add backend
git commit -m "feat: add FastAPI application shell"
```

### Task 3: Model Persistent Repository and Conversation Data

**Files:**
- Create: `backend/app/persistence/session.py`
- Create: `backend/app/persistence/models.py`
- Create: `backend/app/persistence/repositories.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/tests/persistence/test_repository_store.py`

**Interfaces:**
- Produces SQLAlchemy models `Repository`, `SourceFile`, `Chunk`, `Conversation`, `Message`, `Citation`, and `RebuildRecord`.
- Produces `RepositoryStore.create(url: str, full_name: str, default_branch: str) -> Repository` and `RepositoryStore.get_or_create_conversation(repository_id: UUID, title: str) -> Conversation`.

- [ ] **Step 1: Write the failing persistence test**

```python
def test_creating_repository_creates_one_durable_conversation(store: RepositoryStore) -> None:
    repository = store.create("https://github.com/acme/widgets", "acme/widgets", "main")
    first = store.get_or_create_conversation(repository.id, "widgets")
    second = store.get_or_create_conversation(repository.id, "widgets")
    assert first.id == second.id
    assert first.title == "widgets"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend; python -m pytest tests/persistence/test_repository_store.py -q`

Expected: FAIL because persistence models and store do not exist.

- [ ] **Step 3: Implement database models and migration**

Give `Chunk` a pgvector embedding column whose dimension matches `nomic-embed-text`; store `start_line`, `end_line`, `commit_sha`, and `path`. Put a unique constraint on `Conversation.repository_id` to enforce one conversation per repository. Add an index-version identifier to source files and chunks so a rebuild can activate a complete replacement set.

- [ ] **Step 4: Run migration and persistence tests**

Run:

```powershell
docker compose up -d postgres
cd backend
alembic upgrade head
python -m pytest tests/persistence/test_repository_store.py -q
```

Expected: migration succeeds and the test passes against PostgreSQL.

- [ ] **Step 5: Commit the persistence foundation**

```powershell
git add backend
git commit -m "feat: persist repositories conversations and source indexes"
```

### Task 4: Implement GitHub Discovery and Safe File Selection

**Files:**
- Create: `backend/app/github/client.py`
- Create: `backend/app/github/models.py`
- Create: `backend/app/rag/file_filter.py`
- Create: `backend/tests/github/test_client.py`
- Create: `backend/tests/rag/test_file_filter.py`

**Interfaces:**
- Produces `GitHubRepository(ref: str, default_branch: str, commit_sha: str)` and `GitHubFile(path: str, content: str, sha: str)`.
- Produces `GitHubClient.resolve(url: str) -> GitHubRepository` and `GitHubClient.list_files(repository: GitHubRepository) -> list[GitHubFile]`.
- Produces `should_index(path: str, content: str) -> bool`.

- [ ] **Step 1: Write failing allowlist tests**

```python
import pytest

from app.rag.file_filter import should_index


@pytest.mark.parametrize("path", ["src/app.py", "README.md", "config/app.yaml", "Dockerfile"])
def test_allowlisted_files_are_indexed(path: str) -> None:
    assert should_index(path, "meaningful text") is True


@pytest.mark.parametrize("path", ["node_modules/a.js", "dist/app.min.js", "package-lock.json", ".git/config"])
def test_excluded_files_are_not_indexed(path: str) -> None:
    assert should_index(path, "meaningful text") is False
```

- [ ] **Step 2: Run the filter test to verify it fails**

Run: `cd backend; python -m pytest tests/rag/test_file_filter.py -q`

Expected: FAIL because `should_index` does not exist.

- [ ] **Step 3: Implement adapter and filter**

Use GitHub's authenticated API through a small client that validates `https://github.com/<owner>/<repo>` URLs, reads the default branch, resolves its commit SHA, and downloads text files. Reject invalid URLs and turn 401/403/404 responses into typed service errors. The filter must apply extension/path/size checks before source text reaches chunking.

- [ ] **Step 4: Run module tests**

Run: `cd backend; python -m pytest tests/github/test_client.py tests/rag/test_file_filter.py -q`

Expected: PASS with HTTP calls mocked.

- [ ] **Step 5: Commit GitHub discovery**

```powershell
git add backend
git commit -m "feat: discover GitHub repositories and filter source files"
```

### Task 5: Build Chunking, Ollama Embeddings, and Versioned Indexing

**Files:**
- Create: `backend/app/rag/chunker.py`
- Create: `backend/app/rag/ollama.py`
- Create: `backend/app/services/indexing.py`
- Create: `backend/tests/rag/test_chunker.py`
- Create: `backend/tests/services/test_indexing.py`

**Interfaces:**
- Produces `ChunkDraft(text: str, start_line: int, end_line: int)` and `chunk_file(content: str, max_lines: int = 80, overlap_lines: int = 10) -> list[ChunkDraft]`.
- Produces `EmbeddingClient.embed(texts: list[str]) -> list[list[float]]` using `nomic-embed-text:latest`.
- Produces `IndexingService.rebuild(repository_id: UUID) -> RebuildResult`.

- [ ] **Step 1: Write failing chunk-line tests**

```python
from app.rag.chunker import chunk_file


def test_chunks_preserve_inclusive_source_line_ranges() -> None:
    content = "\n".join(f"line {number}" for number in range(1, 6))
    chunks = chunk_file(content, max_lines=2, overlap_lines=0)
    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 2), (3, 4), (5, 5)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend; python -m pytest tests/rag/test_chunker.py tests/services/test_indexing.py -q`

Expected: FAIL because chunker and indexing service do not exist.

- [ ] **Step 3: Implement versioned indexing**

Create a new index version, persist all filtered files/chunks/embeddings under it, and activate that version in one transaction only after all embeddings persist. When the resolved SHA equals the active SHA, return `changed=False` and do not create another version. On an exception, mark `RebuildRecord` failed and leave the active version unchanged.

- [ ] **Step 4: Run unit and PostgreSQL integration tests**

Run: `cd backend; python -m pytest tests/rag/test_chunker.py tests/services/test_indexing.py -q`

Expected: PASS; embedding HTTP calls are mocked in tests.

- [ ] **Step 5: Commit indexing**

```powershell
git add backend
git commit -m "feat: build versioned repository indexes"
```

### Task 6: Implement Grounded Retrieval, Answer Generation, and Citations

**Files:**
- Create: `backend/app/rag/retrieval.py`
- Create: `backend/app/rag/citations.py`
- Create: `backend/app/services/chat.py`
- Create: `backend/tests/rag/test_citations.py`
- Create: `backend/tests/services/test_chat.py`

**Interfaces:**
- Produces `RetrievedChunk(path: str, text: str, start_line: int, end_line: int, commit_sha: str, score: float)`.
- Produces `build_github_url(full_name: str, commit_sha: str, path: str, start_line: int, end_line: int) -> str`.
- Produces `ChatService.ask(repository_id: UUID, question: str) -> ChatAnswer`.

- [ ] **Step 1: Write the failing citation test**

```python
from app.rag.citations import build_github_url


def test_citation_url_is_pinned_to_indexed_commit_and_lines() -> None:
    url = build_github_url("acme/widgets", "abc123", "src/app.py", 10, 14)
    assert url == "https://github.com/acme/widgets/blob/abc123/src/app.py#L10-L14"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend; python -m pytest tests/rag/test_citations.py tests/services/test_chat.py -q`

Expected: FAIL because retrieval, citation, and chat modules do not exist.

- [ ] **Step 3: Implement grounded chat**

Embed the question, search only the active repository index by cosine distance, and pass retrieved chunks to the OpenAI-compatible completion endpoint configured in `.env`. Require the model prompt to state insufficient evidence when context cannot support an answer. Persist user and assistant messages; create a citation row for every chunk cited by the answer.

- [ ] **Step 4: Run chat tests**

Run: `cd backend; python -m pytest tests/rag/test_citations.py tests/services/test_chat.py -q`

Expected: PASS with model clients mocked.

- [ ] **Step 5: Commit the RAG chat service**

```powershell
git add backend
git commit -m "feat: answer repository questions with citations"
```

### Task 7: Expose Typed Repository, Rebuild, and Chat APIs

**Files:**
- Create: `backend/app/api/schemas.py`
- Create: `backend/app/api/dependencies.py`
- Create: `backend/app/api/repositories.py`
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/api/routes.py`
- Create: `backend/tests/api/test_repositories.py`
- Create: `backend/tests/api/test_chat.py`

**Interfaces:**
- Produces `POST /repositories`, `GET /repositories`, `GET /repositories/{repository_id}`, and `POST /repositories/{repository_id}/rebuild`.
- Produces `GET /repositories/{repository_id}/conversation` and `POST /repositories/{repository_id}/chat`.
- Uses Pydantic response models that expose no secrets or raw database internals.

- [ ] **Step 1: Write a failing route test**

```python
def test_create_repository_returns_created_repository(client, repository_service) -> None:
    repository_service.create.return_value = {"id": "repo-1", "name": "widgets", "status": "ready"}
    response = client.post("/repositories", json={"url": "https://github.com/acme/widgets"})
    assert response.status_code == 201
    assert response.json()["id"] == "repo-1"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run: `cd backend; python -m pytest tests/api/test_repositories.py tests/api/test_chat.py -q`

Expected: FAIL because routes and schemas do not exist.

- [ ] **Step 3: Implement typed routes and error mapping**

Map invalid URLs to HTTP 422, inaccessible repositories to 403/404 without leaking tokens, no active index to 409, and unavailable local services to 503. Routes must inject services through FastAPI dependencies so API tests can substitute fakes.

- [ ] **Step 4: Run API and backend regression tests**

Run: `cd backend; python -m pytest -q`

Expected: PASS.

- [ ] **Step 5: Commit the API**

```powershell
git add backend
git commit -m "feat: expose repository rebuild and chat APIs"
```

### Task 8: Create the React Repository Library and Persistent Chat UI

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api-client/client.ts`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/features/repositories/RepositorySidebar.tsx`
- Create: `frontend/src/features/repositories/AddRepositoryForm.tsx`
- Create: `frontend/src/features/repositories/RebuildButton.tsx`
- Create: `frontend/src/features/chat/ChatPanel.tsx`
- Create: `frontend/src/features/chat/MessageList.tsx`
- Create: `frontend/src/features/chat/ChatComposer.tsx`
- Create: `frontend/src/features/chat/CitationList.tsx`
- Create: `frontend/src/features/repositories/*.test.tsx`
- Create: `frontend/src/features/chat/*.test.tsx`

**Interfaces:**
- Consumes the typed backend endpoints from Task 7.
- Produces a selected repository ID, a persistent message view, a rebuild action, and citations rendered as external GitHub links.

- [ ] **Step 1: Write the failing sidebar and citation tests**

```tsx
it("selects a repository from the persistent library", async () => {
  render(<RepositorySidebar repositories={[{ id: "a", name: "widgets", status: "ready" }]} onSelect={onSelect} />)
  await userEvent.click(screen.getByRole("button", { name: "widgets" }))
  expect(onSelect).toHaveBeenCalledWith("a")
})

it("renders a citation as a commit-pinned external link", () => {
  render(<CitationList citations={[{ path: "src/app.py", startLine: 10, endLine: 14, url: "https://github.com/acme/widgets/blob/abc/src/app.py#L10-L14" }]} />)
  expect(screen.getByRole("link", { name: "src/app.py:10-14" })).toHaveAttribute("href", expect.stringContaining("/blob/abc/"))
})
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `cd frontend; npm test -- --run`

Expected: FAIL because the app and components do not exist.

- [ ] **Step 3: Implement the minimal functional interface**

Create a two-pane responsive layout: repository library/add form on the left and selected repository chat on the right. Show index/rebuild status, disable chat while there is no active index, preserve all loaded messages, and render citations as descriptive links. Use a typed `ApiClient`; do not call `fetch` directly from components.

- [ ] **Step 4: Run frontend tests and production build**

Run:

```powershell
cd frontend
npm test -- --run
npm run build
```

Expected: tests and TypeScript production build pass.

- [ ] **Step 5: Commit the web interface**

```powershell
git add frontend
git commit -m "feat: add repository library and cited chat UI"
```

### Task 9: Verify the End-to-End MVP and Finalize Handoff Documentation

**Files:**
- Create: `frontend/e2e/repository-chat.spec.ts`
- Modify: `README.md`
- Modify: `PROJECT_STATE.md`
- Modify: `docs/architecture.md`
- Create: `docs/decisions/0001-local-postgres-pgvector.md`
- Create: `docs/decisions/0002-full-versioned-rebuilds.md`

**Interfaces:**
- Verifies URL submission, indexing status, persistent conversation, cited answer, and manual rebuild behavior across the completed system.
- Produces an accurate handoff state for a fresh agent.

- [ ] **Step 1: Write the failing end-to-end workflow test**

```ts
test("indexes a repository, answers with a citation, and retains the chat", async ({ page }) => {
  await page.goto("/")
  await page.getByLabel("GitHub repository URL").fill("https://github.com/acme/widgets")
  await page.getByRole("button", { name: "Add repository" }).click()
  await expect(page.getByText("widgets")).toBeVisible()
  await page.getByLabel("Ask about this repository").fill("Where is the API created?")
  await page.getByRole("button", { name: "Send" }).click()
  await expect(page.getByRole("link", { name: /src\/.*:\d+-\d+/ })).toBeVisible()
  await page.reload()
  await expect(page.getByText("Where is the API created?")).toBeVisible()
})
```

- [ ] **Step 2: Run the end-to-end test to verify current behavior**

Run: `cd frontend; npx playwright test e2e/repository-chat.spec.ts`

Expected: PASS after test fixtures provide a deterministic GitHub and Ollama backend; otherwise report the exact unavailable service.

- [ ] **Step 3: Update handoff documentation**

Document the verified setup sequence: populate `.env`, run `docker compose up -d postgres`, run Alembic migrations, start backend, start frontend, and run tests. Update `PROJECT_STATE.md` with completed work, current command results, and the next highest-value enhancement. Record the PostgreSQL/pgvector and full-versioned-rebuild decisions with their rationale and consequences.

- [ ] **Step 4: Run final verification**

Run:

```powershell
docker compose up -d postgres
cd backend; alembic upgrade head; python -m pytest -q
cd ..\frontend; npm test -- --run; npm run build; npx playwright test
cd ..; git diff --check; git status --short
```

Expected: migrations, backend tests, frontend tests, build, end-to-end tests, and whitespace checks pass; Git status contains only intended project changes.

- [ ] **Step 5: Commit final MVP and handoff state**

```powershell
git add README.md PROJECT_STATE.md docs backend frontend docker-compose.yml .env.example .gitignore AGENT.md
git commit -m "feat: deliver GitHub repository RAG MVP"
```

## Plan Self-Review

- **Spec coverage:** Tasks 1-2 establish durable rules, documented setup, environment configuration, and local services. Tasks 3-7 deliver persistence, GitHub access, safe indexing, full versioned rebuilds, grounded chat, citations, and typed APIs. Task 8 delivers the web application. Task 9 verifies persistent chats, citations, rebuild behavior, and future-agent handoff.
- **Placeholder scan:** No task relies on an unspecified interface; each cross-task interface is named, and each implementation task includes a concrete test, command, and expected result.
- **Type consistency:** `RepositoryStore`, `GitHubClient`, `EmbeddingClient`, `IndexingService`, and `ChatService` are introduced before their consumers. `repository_id` and `commit_sha` are used consistently across persistence, indexing, chat, and API tasks.
