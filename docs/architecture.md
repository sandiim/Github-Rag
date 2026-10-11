# Architecture

## System

```text
React + TypeScript
  -> FastAPI
    -> GitHub adapter
    -> RAG services + Ollama
    -> PostgreSQL + pgvector
```

## Backend Modules

- `api`: FastAPI routes and Pydantic schemas.
- `services`: repository creation, rebuild, and chat orchestration.
- `github`: authenticated GitHub URL validation, commit lookup, and file discovery.
- `rag`: file filtering, chunking, embeddings, retrieval, and citations.
- `persistence`: SQLAlchemy models, migrations, repositories, and vector search.

## Core Rules

- Routes call services; services own business workflows.
- GitHub, Ollama, and persistence integrations remain behind module interfaces.
- A rebuild writes a new index version before atomically activating it.
- Chats stay attached to one repository and retain commit-pinned citations.
- The frontend uses a typed API client and never receives secrets.
