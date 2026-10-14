# Architecture

## System

```text
React + TypeScript
  -> FastAPI
    -> PostgreSQL ingestion job
      -> separate Python worker
        -> GitHub adapter
        -> file filter + chunker + Ollama embeddings
        -> PostgreSQL + pgvector replacement index
```

## Backend Modules

- `api`: FastAPI routes and Pydantic schemas.
- `services`: fast repository enqueue, worker indexing, and chat orchestration.
- `github`: authenticated GitHub URL validation, commit lookup, and file discovery.
- `rag`: file filtering, chunking, embeddings, retrieval, and citations.
- `persistence`: SQLAlchemy models, migrations, job leasing/progress, and vector search.

## Ingestion Flow

`POST /repositories` validates a GitHub URL and commits a queued `ingestion_jobs` row before returning HTTP 202. `python -m app.worker` claims one job at a time with a PostgreSQL row lock and lease, resolves the branch commit, selects eligible tree blobs, downloads and embeds each file, and updates progress in short independent transactions. It commits the completed job and replacement active index in one transaction; on failure it rolls back the candidate index and stores a safe error. Expired leases get one automatic retry. React polls `GET /repositories` every two seconds while any job is active.

The file-selection policy has a version independent of the commit SHA. A manual rebuild reindexes an unchanged commit when that policy changes. Chat always reads the active index, so a failed or in-progress rebuild leaves the prior version usable.

The file filter admits selected text suffixes, including R Markdown (`.rmd`), before chunking. Answer generation calls the local Ollama OpenAI-compatible API using the app-specific `github-rag-llama3.1:8k` alias; embeddings use `nomic-embed-text:latest` through Ollama's native API.

The completion prompt labels retrieved chunks with temporary numeric source markers. Chat resolves valid markers into stable `[path:start-end]` references before persisting the answer, retaining only referenced citations when markers are present. The frontend turns references matching the message's citation records into commit-pinned inline links; an unmarked older answer keeps the separate source list.

## Core Rules

- Routes call services; services own business workflows.
- GitHub, Ollama, and persistence integrations remain behind module interfaces.
- A rebuild writes a new index version before atomically activating it.
- Chats stay attached to one repository and retain commit-pinned citations.
- The frontend uses a typed API client and never receives secrets.
