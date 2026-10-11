"""Active-index vector retrieval."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
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


class RetrievalService:
    """Embed a question and search only the currently active index version."""

    def __init__(self, session: Session, embeddings: EmbeddingClient) -> None:
        self._session = session
        self._embeddings = embeddings

    def retrieve(self, repository_id: uuid.UUID, question: str, limit: int = 6) -> list[RetrievedChunk]:
        """Return the nearest chunks in the repository's active replacement index."""

        repository = self._session.get(Repository, repository_id)
        if repository is None or repository.active_index_version is None:
            return []
        question_embedding = self._embeddings.embed([question])[0]
        distance = Chunk.embedding.cosine_distance(question_embedding).label("distance")
        rows = self._session.execute(
            select(Chunk, SourceFile, distance)
            .join(SourceFile, Chunk.source_file_id == SourceFile.id)
            .where(
                SourceFile.repository_id == repository_id,
                SourceFile.index_version == repository.active_index_version,
            )
            .order_by(distance)
            .limit(limit)
        ).all()
        return [
            RetrievedChunk(
                path=source_file.path,
                text=chunk.text,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                commit_sha=source_file.commit_sha,
                score=1.0 - float(chunk_distance),
            )
            for chunk, source_file, chunk_distance in rows
        ]
