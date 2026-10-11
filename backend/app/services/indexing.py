"""Repository indexing orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from app.github.models import GitHubFile, GitHubRepository
from app.persistence.models import Chunk, RebuildRecord, Repository, SourceFile
from app.rag.chunker import chunk_file
from app.rag.file_filter import should_index


class GitHubRepositoryReader(Protocol):
    def resolve(self, url: str) -> GitHubRepository: ...

    def list_files(self, repository: GitHubRepository) -> list[GitHubFile]: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class RebuildResult:
    changed: bool
    index_version: uuid.UUID | None


class IndexingService:
    """Build and atomically activate a replacement repository index."""

    def __init__(
        self,
        session: Session,
        github: GitHubRepositoryReader,
        embeddings: EmbeddingProvider,
    ) -> None:
        self._session = session
        self._github = github
        self._embeddings = embeddings

    def rebuild(self, repository_id: uuid.UUID) -> RebuildResult:
        """Index the current default branch unless its active commit is unchanged."""

        repository = self._session.get(Repository, repository_id)
        if repository is None:
            raise LookupError("Repository was not found")

        resolved = self._github.resolve(repository.url)
        if resolved.commit_sha == repository.active_commit_sha:
            return RebuildResult(changed=False, index_version=repository.active_index_version)

        index_version = uuid.uuid4()
        record = RebuildRecord(
            repository_id=repository.id,
            index_version=index_version,
            status="running",
        )
        self._session.add(record)
        self._session.flush()

        try:
            with self._session.begin_nested():
                self._persist_index(repository, resolved, index_version)
            record.status = "completed"
            self._session.flush()
        except Exception:
            record.status = "failed"
            self._session.flush()
            raise

        return RebuildResult(changed=True, index_version=index_version)

    def _persist_index(
        self,
        repository: Repository,
        resolved: GitHubRepository,
        index_version: uuid.UUID,
    ) -> None:
        for github_file in self._github.list_files(resolved):
            if not should_index(github_file.path, github_file.content):
                continue
            source_file = SourceFile(
                repository_id=repository.id,
                index_version=index_version,
                commit_sha=resolved.commit_sha,
                path=github_file.path,
                content=github_file.content,
            )
            self._session.add(source_file)
            self._session.flush()
            drafts = chunk_file(github_file.content)
            vectors = self._embeddings.embed([draft.text for draft in drafts])
            if len(vectors) != len(drafts):
                raise ValueError("Embedding response count did not match chunk count")
            self._session.add_all(
                Chunk(
                    source_file_id=source_file.id,
                    text=draft.text,
                    start_line=draft.start_line,
                    end_line=draft.end_line,
                    embedding=vector,
                )
                for draft, vector in zip(drafts, vectors, strict=True)
            )

        repository.default_branch = resolved.default_branch
        repository.active_commit_sha = resolved.commit_sha
        repository.active_index_version = index_version
        repository.status = "ready"
        self._session.flush()
