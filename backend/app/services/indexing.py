"""Repository indexing orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.github.models import GitHubBlobCandidate, GitHubFile, GitHubRepository
from app.persistence.models import Chunk, Repository, SourceFile
from app.rag.chunker import chunk_file
from app.rag.file_filter import INDEX_POLICY_VERSION, should_index


class GitHubRepositoryReader(Protocol):
    def resolve(self, url: str) -> GitHubRepository: ...

    def list_candidates(self, repository: GitHubRepository) -> list[GitHubBlobCandidate]: ...

    def download_blob(self, repository: GitHubRepository, candidate: GitHubBlobCandidate) -> GitHubFile | None: ...


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

    def rebuild(
        self, repository_id: uuid.UUID,
        progress: Callable[[str, int, int | None], None] | None = None,
    ) -> RebuildResult:
        """Index the current default branch unless its active commit is unchanged."""

        repository = self._session.get(Repository, repository_id)
        if repository is None:
            raise LookupError("Repository was not found")

        report = progress or (lambda stage, done, total: None)
        report("resolving", 0, None)
        resolved = self._github.resolve(repository.url)
        if (resolved.commit_sha == repository.active_commit_sha
                and repository.active_index_policy_version == INDEX_POLICY_VERSION):
            return RebuildResult(changed=False, index_version=repository.active_index_version)

        index_version = uuid.uuid4()
        self._persist_index(repository, resolved, index_version, report)

        return RebuildResult(changed=True, index_version=index_version)

    def _persist_index(
        self,
        repository: Repository,
        resolved: GitHubRepository,
        index_version: uuid.UUID,
        progress: Callable[[str, int, int | None], None],
    ) -> None:
        candidates = self._github.list_candidates(resolved)
        progress("downloading", 0, len(candidates))
        for number, candidate in enumerate(candidates, 1):
            github_file = self._github.download_blob(resolved, candidate)
            if github_file is None:
                progress("embedding", number, len(candidates))
                continue
            if not should_index(github_file.path, github_file.content):
                progress("embedding", number, len(candidates))
                continue
            self._persist_file(repository, resolved, index_version, github_file)
            progress("embedding", number, len(candidates))

        progress("activating", len(candidates), len(candidates))
        repository.default_branch = resolved.default_branch
        repository.active_commit_sha = resolved.commit_sha
        repository.active_index_version = index_version
        repository.active_index_policy_version = INDEX_POLICY_VERSION
        repository.status = "ready"
        self._session.flush()

    def _persist_file(
        self, repository: Repository, resolved: GitHubRepository,
        index_version: uuid.UUID, github_file: GitHubFile,
    ) -> None:
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

