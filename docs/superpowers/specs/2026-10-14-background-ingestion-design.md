# Durable background repository ingestion

## Context and goal

The current `POST /repositories` resolves, downloads, chunks, embeds, and commits an entire repository before responding. Real repositories can keep the browser waiting for minutes. A saved repository may also have no conversation until its first question; reading that conversation currently returns 404. The approved milestone makes imports and rebuilds observable, durable jobs while preserving commit-pinned answers and the last complete index.

This is a single-user local application. PostgreSQL is already required; the design adds one Python worker process, not Redis, Celery, or WebSockets.

## API and user experience

- `POST /repositories` validates a plain `https://github.com/<owner>/<repo>` URL without calling GitHub, creates a `pending` repository and queued job, and returns HTTP 202 with the repository and latest ingestion state. Invalid URLs receive a specific 422 message. The server never returns or logs configured credentials.
- Re-adding a repository with a queued/running job returns that existing repository/job without enqueueing a duplicate. Re-adding a ready or failed repository returns its current state; a failed entry has an explicit Retry action.
- `POST /repositories/{id}/rebuild` enqueues a job and returns HTTP 202. This endpoint also retries a failed first import. Repeated requests while a job is queued/running return that same job. A rebuild checks the default-branch commit and the index-selection policy version; if both are unchanged, the worker marks the job `skipped`.
- `GET /repositories` and `GET /repositories/{id}` expose the latest job summary alongside `id`, `name`, and repository `status`. The job summary contains `id`, `state` (`queued`, `running`, `completed`, `failed`, `skipped`), `stage` (`resolving`, `listing`, `downloading`, `embedding`, `activating` when running), `completed_files`, nullable `total_files`, and a nullable safe error message. The UI polls while any job is active, displays progress, and stops polling at a terminal state.
- A new repository is `pending` until it has an active index, then `ready`; a failed first import becomes `failed`. During a rebuild, an already-ready repository stays `ready`, allowing chat against the old index. A failed job remains listed with Retry and its last safe error. A repository with no messages returns an empty conversation titled from the repository name; missing repositories still return 404.
- Retry creates a new job for the same repository; it does not require retyping the URL or delete conversation history. The UI reports when the worker is not making progress rather than leaving an indefinite “Adding…” state.

## Persistence and worker

Rename the existing `rebuild_records` table/model to `ingestion_jobs` in an Alembic migration, preserving historical rows. Add job kind (`import` or `rebuild`), state, stage, timestamps, progress counts, safe error, attempt count, and a worker lease. Historical terminal rows remain history; historical `running` rows become failed rather than being reclaimed as new jobs. Add a PostgreSQL partial unique index on `repository_id` for queued/running rows so only one active job exists per repository. Store the index-selection policy version with the repository's active index. Make `Repository.default_branch` nullable until the worker resolves it, and derive the initial `full_name` from the validated URL for immediate display.

Run one worker with `cd backend; python -m app.worker` alongside Uvicorn. It claims a queued job in a short transaction using PostgreSQL row locking, then performs network and embedding work outside that claim transaction. The lease is renewed independently of long GitHub/Ollama calls so a restarted worker can reclaim an abandoned job without stealing a live one. One automatic recovery attempt is permitted; subsequent failure waits for an explicit user Retry. The worker processes one repository at a time initially to avoid multiplying GitHub rate-limit pressure.

The worker uses separate database sessions for committed job progress and the replacement index transaction. It resolves the pinned commit, lists tree metadata, applies the existing allowlist and directory exclusions before downloading blobs, then chunks and embeds selected files. `total_files` becomes known after selection; `completed_files` advances after each file is processed. If the worker dies mid-index, its uncommitted replacement rolls back; recovery resets progress before retry. Only after all selected files and vectors are stored does one transaction activate the replacement index and mark the job complete. Failure leaves the prior active version and chat citations intact. If the worker crashes after that final commit, the completed job is not reclaimed.

The selection policy gets an explicit version so a manual rebuild can replace an old index even when GitHub's commit SHA is unchanged. Bulk dataset paths such as `data/` and `datasets/` are excluded by default, while source/configuration JSON elsewhere remains eligible. The currently saved `Score_Prediction` index is not silently rewritten by the migration; a user-triggered rebuild applies the new policy.

## Errors and boundaries

GitHub access, quota, timeouts, Ollama availability, and malformed embedding responses become safe job failures with actionable messages. Internal exceptions are logged without secrets and shown to the UI only as generic errors. A missing worker leaves jobs queued and visible. File contents remain untrusted; existing size and binary checks apply. No changes to chat generation, vector dimensionality, or citation format are planned.

The current GitHub client still uses one REST blob request per selected file. The job system makes that cost and rate-limit failures visible and retryable, but archive or partial-clone retrieval is a separate later milestone.

## Verification and acceptance

- Backend tests cover syntactic URL validation, idempotent enqueue, job claim/recovery, progress, unchanged-commit/policy skipping, failure preservation, retry, and empty-conversation reads.
- Frontend tests cover immediate add response, polling, progress, failed-job Retry, and chat availability during rebuild. Existing backend and frontend suites and build must pass.
- With PostgreSQL and Ollama running and GitHub quota available, a real repository can be added without waiting for the full index in the original POST; progress and terminal state survive page refresh. A failed import remains actionable, and an existing ready index survives a failed rebuild.
- Local startup documentation includes the worker command and explains that ingestion will remain queued if it is not running. Live verification is recorded separately from fixture-based tests; external availability is not assumed.
