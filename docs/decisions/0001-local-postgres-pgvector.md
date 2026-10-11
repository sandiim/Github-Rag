# Use local PostgreSQL with pgvector

## Decision

Use PostgreSQL with the pgvector extension in Docker for repository indexes, chat history, and vector retrieval.

## Consequences

The application remains local and free to run, but PostgreSQL must be started before the backend. Vector dimensions are fixed to the selected `nomic-embed-text` model.
