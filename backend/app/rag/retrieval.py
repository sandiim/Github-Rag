"""Active-index hybrid repository retrieval."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, replace

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.persistence.models import Chunk, Repository, SourceFile
from app.rag.ollama import EmbeddingClient


@dataclass(frozen=True)
class RetrievedChunk:
    path: str
    text: str
    start_line: int
    end_line: int
    commit_sha: str
    score: float


def fuse_ranked_chunks(
    vector_hits: list[RetrievedChunk], keyword_hits: list[RetrievedChunk], limit: int
) -> list[RetrievedChunk]:
    """Fuse candidate ranks and spread the first results across source files."""

    if limit <= 0:
        return []
    scores: dict[tuple[str, int, int, str], float] = {}
    chunks: dict[tuple[str, int, int, str], RetrievedChunk] = {}
    for hits, weight in ((vector_hits, 1.0), (keyword_hits, 1.1)):
        for rank, hit in enumerate(hits, start=1):
            key = (hit.path, hit.start_line, hit.end_line, hit.commit_sha)
            scores[key] = scores.get(key, 0.0) + weight / (60 + rank)
            chunks[key] = hit

    ranked = sorted(scores, key=lambda key: (-scores[key], key))
    selected: list[tuple[str, int, int, str]] = []
    per_file: Counter[str] = Counter()
    for key in ranked:
        if per_file[key[0]] < 2:
            selected.append(key)
            per_file[key[0]] += 1
        if len(selected) == limit:
            break
    if len(selected) < limit:
        selected.extend(key for key in ranked if key not in selected)  # Fill sparse repositories.
    return [replace(chunks[key], score=scores[key]) for key in selected[:limit]]


class RetrievalService:
    """Search vector and lexical candidates from the active index version."""

    def __init__(self, session: Session, embeddings: EmbeddingClient) -> None:
        self._session = session
        self._embeddings = embeddings

    def retrieve(self, repository_id: uuid.UUID, question: str, limit: int = 6) -> list[RetrievedChunk]:
        """Return fused chunks from the repository's active replacement index."""

        repository = self._session.get(Repository, repository_id)
        if repository is None or repository.active_index_version is None or limit <= 0:
            return []
        question_embedding = self._embeddings.embed([question])[0]
        distance = Chunk.embedding.cosine_distance(question_embedding).label("distance")
        candidate_limit = max(16, limit * 4)
        vector_rows = self._session.execute(
            select(Chunk, SourceFile, distance)
            .join(SourceFile, Chunk.source_file_id == SourceFile.id)
            .where(
                SourceFile.repository_id == repository_id,
                SourceFile.index_version == repository.active_index_version,
            )
            .order_by(distance)
            .limit(candidate_limit)
        ).all()
        vector_hits = [
            RetrievedChunk(
                path=source_file.path,
                text=chunk.text,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                commit_sha=source_file.commit_sha,
                score=1.0 - float(chunk_distance),
            )
            for chunk, source_file, chunk_distance in vector_rows
        ]

        terms = list(dict.fromkeys(re.findall(r"[A-Za-z_][A-Za-z0-9_.-]*", question)))[:12]
        if not terms:
            return fuse_ranked_chunks(vector_hits, [], limit)
        query = func.websearch_to_tsquery("english", " OR ".join(terms))
        path_text = func.regexp_replace(SourceFile.path, r"[^[:alnum:]_]+", " ", "g")
        searchable = func.setweight(func.to_tsvector("english", path_text), literal_column("'A'")).op("||")(
            func.setweight(func.to_tsvector("english", Chunk.text), literal_column("'D'"))
        )
        rank = func.ts_rank_cd(searchable, query).label("rank")
        keyword_rows = self._session.execute(
            select(Chunk, SourceFile, rank)
            .join(SourceFile, Chunk.source_file_id == SourceFile.id)
            .where(
                SourceFile.repository_id == repository_id,
                SourceFile.index_version == repository.active_index_version,
                searchable.op("@@")(query),
            )
            .order_by(rank.desc())
            .limit(candidate_limit)
        ).all()
        keyword_hits = [
            RetrievedChunk(
                path=source_file.path,
                text=chunk.text,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                commit_sha=source_file.commit_sha,
                score=float(keyword_rank),
            )
            for chunk, source_file, keyword_rank in keyword_rows
        ]
        return fuse_ranked_chunks(vector_hits, keyword_hits, limit)
