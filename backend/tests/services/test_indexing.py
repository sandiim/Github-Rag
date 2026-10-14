from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.github.models import GitHubBlobCandidate, GitHubFile, GitHubRepository, RepositoryReference
from app.persistence.models import Base, Chunk, Repository, SourceFile
from app.rag.file_filter import INDEX_POLICY_VERSION
from app.services.indexing import IndexingService


class StubGitHubClient:
    def __init__(self, repository: GitHubRepository, files: list[GitHubFile]) -> None:
        self.repository = repository
        self.files = files

    def resolve(self, url: str) -> GitHubRepository:
        return self.repository

    def list_files(self, repository: GitHubRepository) -> list[GitHubFile]:
        return self.files

    def list_candidates(self, repository: GitHubRepository) -> list[GitHubBlobCandidate]:
        return [GitHubBlobCandidate(path=file.path, sha=file.sha, size=len(file.content)) for file in self.files]

    def download_blob(self, repository: GitHubRepository, candidate: GitHubBlobCandidate) -> GitHubFile:
        return next(file for file in self.files if file.sha == candidate.sha)


class StubEmbeddingClient:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.5] * 768 for _ in texts]


class FailingEmbeddingClient:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("Ollama is unavailable")


def test_rebuild_activates_a_complete_filtered_index() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    resolved = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="commit-123",
    )
    github = StubGitHubClient(
        resolved,
        [
            GitHubFile(path="src/app.py", content="one\ntwo", sha="blob-1"),
            GitHubFile(path="package-lock.json", content="ignored", sha="blob-2"),
        ],
    )

    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
        )
        session.add(repository)
        session.flush()

        events = []
        result = IndexingService(session, github, StubEmbeddingClient()).rebuild(
            repository.id, progress=lambda stage, done, total: events.append((stage, done, total))
        )

        source_files = session.scalars(select(SourceFile)).all()
        chunks = session.scalars(select(Chunk)).all()
        assert result.changed is True
        assert repository.active_commit_sha == "commit-123"
        assert repository.active_index_version == result.index_version
        assert [source_file.path for source_file in source_files] == ["src/app.py"]
        assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 2)]
        assert chunks[0].embedding == [0.5] * 768
        assert ("embedding", 1, 2) in events
        assert repository.active_index_policy_version == INDEX_POLICY_VERSION


def test_rebuild_skips_work_when_the_active_commit_is_unchanged() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    resolved = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="commit-123",
    )

    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
            active_commit_sha="commit-123",
            active_index_policy_version=INDEX_POLICY_VERSION,
        )
        session.add(repository)
        session.flush()

        result = IndexingService(session, StubGitHubClient(resolved, []), StubEmbeddingClient()).rebuild(
            repository.id
        )

        assert result.changed is False
        assert session.scalars(select(SourceFile)).all() == []


def test_failed_rebuild_keeps_the_previous_active_index() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    resolved = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="commit-456",
    )

    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
            active_commit_sha="commit-123",
        )
        session.add(repository)
        session.commit()
        repository_id = repository.id

        try:
            IndexingService(
                session,
                StubGitHubClient(
                    resolved,
                    [GitHubFile(path="src/app.py", content="one", sha="blob-1")],
                ),
                FailingEmbeddingClient(),
            ).rebuild(repository.id)
        except RuntimeError as error:
            assert str(error) == "Ollama is unavailable"
        else:
            raise AssertionError("Expected the embedding failure to be re-raised")

        assert repository.active_commit_sha == "commit-123"
        session.rollback()
        assert session.get(Repository, repository_id).active_commit_sha == "commit-123"
        assert session.scalars(select(SourceFile)).all() == []


def test_same_commit_rebuilds_when_selection_policy_changed() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    resolved = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main", commit_sha="commit-123",
    )
    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets", full_name="acme/widgets",
            default_branch="main", active_commit_sha="commit-123",
            active_index_policy_version=1,
        )
        session.add(repository)
        session.flush()
        result = IndexingService(session, StubGitHubClient(resolved, []), StubEmbeddingClient()).rebuild(repository.id)
        assert result.changed
        assert repository.active_index_policy_version == INDEX_POLICY_VERSION
