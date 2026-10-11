# Use full versioned rebuilds

## Decision

When a repository commit changes, build a complete replacement index and activate it only after success.

## Consequences

Rebuilds are simpler and retain a usable prior index if a GitHub or Ollama operation fails. They take more time and storage than incremental indexing.
