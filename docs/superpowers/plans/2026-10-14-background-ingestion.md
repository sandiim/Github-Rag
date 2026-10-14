# Durable Background Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make GitHub repository imports and rebuilds durable, observable background jobs so the web request returns promptly and real repositories do not appear frozen.

**Architecture:** FastAPI enqueues a PostgreSQL job and returns HTTP 202. A separate single-concurrency Python worker claims jobs, reports progress through short transactions, and atomically activates a complete replacement index; React polls the repository library for progress. The existing GitHub and Ollama adapters remain behind services.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Alembic, PostgreSQL/pgvector, httpx, pytest, React/TypeScript, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-14-background-ingestion-design.md`

**Implementation status (2026-10-14):** Tasks 1–7 were implemented in the current checkout. Deterministic SQLite/API/frontend tests and the configured PostgreSQL migration passed. Two verification items remain: exercise `SELECT ... FOR UPDATE SKIP LOCKED` with competing workers in an isolated PostgreSQL test database, and retry the user's larger GitHub repositories with the live worker after GitHub/Ollama connectivity and quota are available. The frontend has add/poll/chat-ready tests, but no browser-level Playwright test yet. See `PROJECT_STATE.md` for current counts and limitations.

## Global Constraints

- Single-user local app; one separate `python -m app.worker` process and no Redis, Celery, or WebSockets.
- Never expose, log, commit, or return `.env` secrets; source content is untrusted.
- Keep FastAPI routes thin, GitHub code in `app/github`, indexing orchestration in `app/services`, and database state in `app/persistence`.
- Preserve the previous active index and commit-pinned citations on failed rebuilds.
- Continue fetching one GitHub REST blob per selected file in this milestone; archive/partial clone is outside scope.
- Use test-first red/green cycles, run the complete backend/frontend suites and build before completion, and make scoped commits.

---

## File map

- `backend/app/persistence/models.py`, `backend/alembic/versions/0004_background_ingestion.py`: durable job and policy-version schema.
- `backend/app/persistence/jobs.py`: claim, heartbeat, progress, terminal-state and lease-recovery queries; no GitHub/Ollama calls.
- `backend/app/services/repositories.py`: URL validation, idempotent enqueue, latest-job summaries and empty-conversation reads.
- `backend/app/services/indexing.py`: one replacement-index transaction, policy-aware skip and progress callback; no HTTP or job ownership.
- `backend/app/services/ingestion.py`: worker orchestration and safe error classification.
- `backend/app/worker.py`: one-process polling entry point and dependency construction.
- `backend/app/github/client.py`, `backend/app/github/models.py`: expose selected tree metadata and individual blob download for accurate progress.
- `backend/app/api/{schemas,repositories,dependencies}.py`: 202 contracts and service wiring.
- `frontend/src/{App.tsx,types/api.ts,api-client/client.ts}` and `frontend/src/features/repositories/`: polling, progress and Retry display.
- `README.md`, `docs/architecture.md`, `docs/decisions/`, `PROJECT_STATE.md`: startup and durable design handoff.

### Task 1: Finish the scoped conversation and dataset-filter fixes

**Files:** Modify `backend/app/rag/file_filter.py`, `backend/app/services/repositories.py`, `backend/tests/rag/test_file_filter.py`; create `backend/tests/services/test_repositories.py` (these are already uncommitted in the worktree).

**Interfaces:** `RepositoryService.conversation(repository_id: str) -> ConversationSummary` returns an empty summary when the repository exists but no conversation row exists. `should_index(path, content)` excludes `data/` and `datasets/`.

- [ ] Re-run the existing red/green regression tests, especially `test_repository_without_messages_has_an_empty_conversation` and `test_generated_or_dependency_files_are_excluded`. Preserve all four uncommitted files; do not reset them.
- [ ] Run `cd backend; python -m pytest -q`; expected: all tests pass, with only the existing upstream Starlette warning.
- [ ] Commit only these four files: `git add backend/app/rag/file_filter.py backend/app/services/repositories.py backend/tests/rag/test_file_filter.py backend/tests/services/test_repositories.py; git commit -m "fix: open empty conversations and skip dataset files"`.

### Task 2: Add durable job schema and preserve history

**Files:** Modify `backend/app/persistence/models.py`; create `backend/alembic/versions/0004_background_ingestion.py`, `backend/tests/persistence/test_ingestion_schema.py`.

**Interfaces:** `IngestionJob` maps to `ingestion_jobs` and has `id`, `repository_id`, `index_version`, `kind`, `state`, `stage`, `completed_files`, `total_files`, `error_message`, `attempt_count`, `lease_expires_at`, `created_at`, and `updated_at`. `Repository.active_index_policy_version: int | None`; `Repository.default_branch: str | None`. `INDEX_POLICY_VERSION = 2` lives in `app/rag/file_filter.py`.

- [ ] Add a failing metadata test that asserts `IngestionJob.__table__.name == "ingestion_jobs"`, the active-job partial unique index exists, and `Repository.default_branch.nullable is True`.

  ```python
  def test_ingestion_model_preserves_job_history_shape():
      assert IngestionJob.__table__.name == "ingestion_jobs"
      assert Repository.__table__.c.default_branch.nullable
      assert "uq_ingestion_jobs_active_repository" in {
          index.name for index in IngestionJob.__table__.indexes
      }
  ```
- [ ] Run `cd backend; python -m pytest tests/persistence/test_ingestion_schema.py -q`; expected: import/metadata assertion failure.
- [ ] Add the model fields and Alembic `0004` migration: rename `rebuild_records` to `ingestion_jobs`, rename `status` to `state`, add the listed fields, backfill historical kind as `rebuild` and attempt count as `0`, mark historical `running` rows `failed`, and create `uq_ingestion_jobs_active_repository` with predicate `state IN ('queued','running')`. Alter `repositories.default_branch` nullable and add nullable `active_index_policy_version`. The model's partial index must define both `postgresql_where` and `sqlite_where` so SQLite unit tests enforce the same rule. Until Task 4 removes the old indexing-side record creation, keep `RebuildRecord = IngestionJob` and a mapped `status` synonym for `state` so each intermediate commit remains testable.

  ```python
  op.rename_table("rebuild_records", "ingestion_jobs")
  op.alter_column("ingestion_jobs", "status", new_column_name="state")
  op.add_column("ingestion_jobs", sa.Column("kind", sa.String(16), nullable=True))
  op.add_column("ingestion_jobs", sa.Column("stage", sa.String(32), nullable=True))
  op.add_column("ingestion_jobs", sa.Column("completed_files", sa.Integer(), nullable=False, server_default="0"))
  op.add_column("ingestion_jobs", sa.Column("total_files", sa.Integer(), nullable=True))
  op.add_column("ingestion_jobs", sa.Column("error_message", sa.Text(), nullable=True))
  op.add_column("ingestion_jobs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
  op.add_column("ingestion_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
  op.add_column("ingestion_jobs", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
  op.add_column("ingestion_jobs", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
  op.add_column("repositories", sa.Column("active_index_policy_version", sa.Integer(), nullable=True))
  op.alter_column("repositories", "default_branch", nullable=True)
  op.execute("UPDATE ingestion_jobs SET kind = 'rebuild'")
  op.alter_column("ingestion_jobs", "kind", nullable=False)
  op.execute("UPDATE ingestion_jobs SET state = 'failed' WHERE state = 'running'")
  op.create_index(
      "uq_ingestion_jobs_active_repository", "ingestion_jobs", ["repository_id"],
      unique=True, postgresql_where=sa.text("state IN ('queued', 'running')"),
  )
  ```
- [ ] Run `cd backend; python -m pytest tests/persistence -q; alembic upgrade head`; expected: tests and migration pass without removing saved repositories or old job rows. Verify the migration's live table/column shape with a read-only SQLAlchemy inspection query.
- [ ] Commit schema, migration and tests: `git commit -m "feat: persist durable ingestion jobs"`.

### Task 3: Enqueue imports and rebuilds without external calls

**Files:** Modify `backend/app/services/repositories.py`, `backend/app/api/{schemas,repositories,dependencies}.py`, `backend/tests/services/test_repositories.py`, `backend/tests/api/test_repositories.py`; create `backend/app/persistence/jobs.py`.

**Interfaces:** `RepositoryService.create(url: str) -> RepositorySummary` and `.rebuild(repository_id: str) -> RepositorySummary` commit a `queued` `IngestionJob` but never invoke GitHub or Ollama. `RepositorySummary` includes nullable `latest_job: IngestionJobSummary`; the API serializes it as `ingestion`. `POST /repositories` and `POST /repositories/{id}/rebuild` return 202. `POST` duplicate of an active job returns the same job; duplicate ready/failed returns the saved repository.

- [ ] Add failing SQLite service tests: `create()` returns a `pending` repository with one queued job while a GitHub stub raises if called; duplicate `create()` keeps job count at one; `rebuild()` on a failed repository creates one new job and keeps the repository ID. Add an API test that checks 202 and `ingestion.state == "queued"`.

  ```python
  created = RepositoryService(session).create("https://github.com/acme/widgets")
  again = RepositoryService(session).create("https://github.com/acme/widgets")
  assert created.id == again.id
  assert session.scalar(select(func.count()).select_from(IngestionJob)) == 1
  assert created.latest_job.state == "queued"
  ```
- [ ] Run `cd backend; python -m pytest tests/services/test_repositories.py tests/api/test_repositories.py -q`; expected: new assertions fail against synchronous indexing/201 responses.
- [ ] Implement URL-only enqueue with `parse_repository_url`, normalized owner/repo identity, transaction commit, latest-job lookup ordered by `created_at, id`, and a race-safe active-job uniqueness path. Map only `InvalidRepositoryUrl` to 422; do not require `Settings()` or instantiate GitHub/Ollama in `get_repository_service`. Keep conversations readable for queued and failed entries.

  ```python
  reference = parse_repository_url(url)
  full_name = f"{reference.owner}/{reference.name}"
  repository = Repository(url=url, full_name=full_name, default_branch=None, status="pending")
  session.add(repository)
  session.flush()
  session.add(IngestionJob(repository_id=repository.id, kind="import", state="queued"))
  session.commit()
  return self._summary(repository)
  ```
- [ ] Run the targeted tests and `cd backend; python -m pytest -q`; expected: all pass with the API now returning 202.
- [ ] Commit: `git commit -m "feat: enqueue repository imports and rebuilds"`.

### Task 4: Split GitHub selection from download and make indexing policy-aware

**Files:** Modify `backend/app/github/{models,client}.py`, `backend/app/services/indexing.py`, `backend/app/rag/file_filter.py`, `backend/tests/github/test_client.py`, `backend/tests/services/test_indexing.py`.

**Interfaces:** `GitHubBlobCandidate(path: str, sha: str, size: int)` is a frozen dataclass in `app/github/models.py`. `GitHubClient.list_candidates(repository: GitHubRepository) -> list[GitHubBlobCandidate]` filters tree metadata; `GitHubClient.download_blob(repository: GitHubRepository, candidate: GitHubBlobCandidate) -> GitHubFile | None` fetches one blob. `IndexingService.rebuild(repository_id: UUID, progress: Callable[[str, int, int | None], None]) -> RebuildResult` does no `commit()` and creates no job row; caller commits or rolls back. `IndexingService._persist_file(repository: Repository, resolved: GitHubRepository, index_version: UUID, github_file: GitHubFile) -> None` persists one filtered file and its chunks. Skip only when both active SHA and `active_index_policy_version == INDEX_POLICY_VERSION` match.

- [ ] Add failing tests: a tree containing `data/round.json` and `src/app.py` yields only the source candidate; an unchanged SHA with old policy version still rebuilds; a failed embedding leaves the previous active version intact after caller rollback. Include a callback test observing `("embedding", 1, 1)` for one file.

  ```python
  events = []
  result = IndexingService(session, github, embeddings).rebuild(
      repository.id, progress=lambda stage, done, total: events.append((stage, done, total))
  )
  assert result.changed
  assert ("embedding", 1, 1) in events
  assert repository.active_index_policy_version == INDEX_POLICY_VERSION
  ```
- [ ] Run `cd backend; python -m pytest tests/github/test_client.py tests/services/test_indexing.py -q`; expected: new interface/policy tests fail.
- [ ] Extract metadata selection and one-blob download from existing `list_files` without changing token handling or size/binary filtering. Refactor indexing so it reports selected total, processed count and stages through the callback, sets active policy version only at successful activation, and leaves transaction control to the caller. Update old tests that asserted `RebuildRecord` creation to assert rollback and active-index preservation instead.

  ```python
  candidates = self._github.list_candidates(resolved)
  progress("downloading", 0, len(candidates))
  for number, candidate in enumerate(candidates, 1):
      github_file = self._github.download_blob(resolved, candidate)
      if github_file is not None and should_index(github_file.path, github_file.content):
          self._persist_file(repository, resolved, index_version, github_file)
      progress("embedding", number, len(candidates))
  repository.active_index_policy_version = INDEX_POLICY_VERSION
  ```
- [ ] Run targeted and complete backend suites; expected: all pass.
- [ ] Commit: `git commit -m "refactor: separate file selection and index activation"`.

### Task 5: Claim, recover and execute jobs in the worker

**Files:** Modify `backend/app/persistence/jobs.py`; create `backend/app/services/ingestion.py`, `backend/app/worker.py`, `backend/tests/persistence/test_job_claims.py`, `backend/tests/services/test_ingestion.py`.

**Interfaces:** `JobStore(session_factory: sessionmaker[Session])` exposes `.claim_next(now: datetime) -> UUID | None`, `.heartbeat(job_id: UUID, now: datetime)`, `.progress(job_id: UUID, stage: str, done: int, total: int | None)`, `.fail(job_id: UUID, safe_message: str)`, and `.recover_expired(now: datetime)` through short transactions. `IngestionRunner(session_factory, github, embeddings, job_store)` exposes `.run_once() -> bool`, claims at most one job and returns whether one was found. `python -m app.worker` repeatedly invokes `run_once()` with a short idle wait and clean KeyboardInterrupt shutdown.

- [ ] Add failing tests against a real test database for `SELECT ... FOR UPDATE SKIP LOCKED` claim exclusivity and the partial unique index; use SQLite only for pure runner tests. Add runner tests: successful job activates index and completes; GitHub/Ollama failure stores a safe failed state and keeps old index; stale lease retries once and then fails; a job with an unchanged SHA and policy version becomes `skipped`.

  ```python
  assert runner.run_once() is True
  with session_factory() as session:
      job = session.get(IngestionJob, job_id)
      repository = session.get(Repository, repository_id)
      assert job.state == "completed"
      assert repository.active_commit_sha == "commit-123"
  assert runner.run_once() is False
  ```
- [ ] Run `cd backend; python -m pytest tests/persistence/test_job_claims.py tests/services/test_ingestion.py -q`; expected: new worker behavior fails before implementation.
- [ ] Implement claim/lease recovery in `JobStore`. The runner constructs GitHub/embedding/indexing dependencies outside the API, renews the lease independently of blocking calls, records progress in a second session, commits index activation and job completion together, and rolls back the index session before storing a sanitized failure. Classify rate-limit, authorization, network timeout and Ollama errors; never store tokens, request headers or raw source content in job errors. An idle worker must not busy-spin.

  ```python
  job = session.scalar(
      select(IngestionJob).where(IngestionJob.state == "queued")
      .order_by(IngestionJob.created_at, IngestionJob.id)
      .with_for_update(skip_locked=True).limit(1)
  )
  if job is not None:
      job.state = "running"
      job.attempt_count += 1
      job.lease_expires_at = now + timedelta(minutes=5)
      session.commit()
  ```
- [ ] Run targeted, full backend, and `alembic upgrade head` verification. Use a stub GitHub/Ollama integration fixture to verify progress survives a new session and page refresh semantics.
- [ ] Commit: `git commit -m "feat: run durable ingestion worker"`.

### Task 6: Show progress and retry in the web application

**Files:** Modify `frontend/src/types/api.ts`, `frontend/src/api-client/client.ts`, `frontend/src/App.tsx`, `frontend/src/features/repositories/{AddRepositoryForm,RebuildButton,RepositorySidebar}.tsx`, `frontend/src/styles.css`; create `frontend/src/features/repositories/IngestionStatus.tsx` and tests; update affected frontend tests.

**Interfaces:** `Repository.ingestion` is nullable and has `id`, `state`, `stage`, `completed_files`, `total_files`, and `error_message`. `ApiClient.addRepository` receives the immediate 202 repository response; `ApiClient.rebuild` returns the updated repository. `App` polls `api.repositories()` every two seconds only while at least one job is queued/running; it clears the timer on unmount. `IngestionStatus` renders queued/running counts, safe failure, and Retry. Existing chat remains enabled whenever `repository.status === "ready"`.

- [ ] Add failing Vitest tests for immediate add/select, polling from `queued` to `completed`, visible progress `3 / 10 files`, failed-job Retry, and chat remaining enabled during a ready repository's rebuild.

  ```tsx
  render(<IngestionStatus repository={repositoryWithRunningJob} onRetry={retry} />);
  expect(screen.getByText("3 / 10 files")).toBeInTheDocument();
  ```
- [ ] Run `cd frontend; npm test -- --run`; expected: new UI assertions fail against the synchronous shape.
- [ ] Update typed API contracts and components. Keep timers in `App` and API calls in `ApiClient`; do not call `fetch` from components. Show “Waiting for worker” if a queued/running job has no recent progress, without declaring it failed.

  ```tsx
  useEffect(() => {
    if (!repositories.some(repo => ["queued", "running"].includes(repo.ingestion?.state ?? ""))) return;
    const timer = window.setInterval(() => void refresh().catch(showError), 2000);
    return () => window.clearInterval(timer);
  }, [repositories]);
  ```
- [ ] Run `cd frontend; npm test -- --run; npm run build`; expected: all tests and TypeScript/build pass.
- [ ] Commit: `git commit -m "feat: display ingestion progress and retry"`.

### Task 7: Document startup and verify the complete flow

**Files:** Modify `README.md`, `docs/architecture.md`, `docs/decisions/0002-full-versioned-rebuilds.md` or add a new decision record, `PROJECT_STATE.md`; add or update an API/worker integration test under `backend/tests/`.

**Interfaces:** Startup sequence is PostgreSQL, Alembic, `uvicorn app.main:app --reload`, `python -m app.worker`, and `npm run dev`. A missing worker leaves imports visibly queued.

- [ ] Add a deterministic integration test with fake GitHub/Ollama showing `POST /repositories` returns 202 before indexing, the worker processes the queued row, GET reports ready, and an empty conversation is readable. Run it red, then make only necessary wiring corrections.

  ```python
  created = client.post("/repositories", json={"url": "https://github.com/acme/widgets"})
  assert created.status_code == 202
  assert created.json()["ingestion"]["state"] == "queued"
  runner.run_once()
  assert client.get(f"/repositories/{created.json()['id']}").json()["status"] == "ready"
  assert client.get(f"/repositories/{created.json()['id']}/conversation").json()["messages"] == []
  ```
- [ ] Run `cd backend; alembic upgrade head; python -m pytest -q` and `cd frontend; npm test -- --run; npm run build`; record exact counts and warnings, not assumed results.
- [ ] Update README commands, architecture data flow, a durable-job decision record, and `PROJECT_STATE.md` with implemented behavior, known GitHub quota/per-blob limits, and whether live real-repository verification was possible. Verify the `.env` is absent from `git status --short` and `git diff --check` is clean.
- [ ] Commit documentation/integration verification: `git commit -m "docs: explain durable repository ingestion"`.
