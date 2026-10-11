# GitHub Repository RAG

A single-user web application for indexing public or private GitHub repositories and asking cited questions about their contents.

## Stack

- React and TypeScript frontend
- FastAPI backend
- PostgreSQL with pgvector
- Ollama `llama3.1:latest` and `nomic-embed-text:latest`

## Local Prerequisites

- Python 3.13+
- Node.js 24+
- Docker Desktop
- Ollama with the required models

## Planned Local Setup

1. Copy `.env.example` values into the existing `.env` without replacing configured secrets.
2. Start PostgreSQL: `docker compose up -d postgres`.
3. Create and migrate the backend database after the backend milestone is complete.
4. Start the backend and frontend after their milestones are complete.

See `PROJECT_STATE.md` for current work and `docs/architecture.md` for module boundaries.
