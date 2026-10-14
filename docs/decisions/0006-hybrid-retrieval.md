# Combine vector and keyword retrieval

## Decision

Search the active index with both pgvector cosine distance and PostgreSQL full-text search. Normalize path separators before tokenization, weight file paths above chunk text, combine candidate ranks with reciprocal-rank fusion, and favor distinct files in the final six chunks.

## Rationale

Embedding-only retrieval can miss exact filenames and symbols. The application already runs PostgreSQL, so keyword search needs no additional service or embedding model. Rank fusion uses relative order rather than trying to compare incompatible vector and text-search scores.

## Tradeoffs

This adds a second database query per chat question. The current full-text expression spans source-file paths and chunk text, so it is not covered by a single index and may need profiling or a denormalized search column for much larger repositories. Retrieval still has no token budget or reranker, and quality depends on the files in the active index.
