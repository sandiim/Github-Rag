import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.github.models import GitHubRepository, RepositoryReference
from app.persistence.jobs import JobStore
from app.persistence.models import Base, IngestionJob, Repository
from app.services.ingestion import IngestionRunner


class EmptyGitHub:
    def resolve(self, url: str) -> GitHubRepository:
        return GitHubRepository(RepositoryReference("acme", "widgets"), "main", "commit-123")

    def list_candidates(self, repository: GitHubRepository) -> list:
        return []


class EmptyEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return []


class FailingGitHub(EmptyGitHub):
    def resolve(self, url: str) -> GitHubRepository:
        raise RuntimeError("secret source content")


def test_runner_activates_queued_repository() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with Session(engine) as session:
        repo = Repository(url="https://github.com/acme/widgets", full_name="acme/widgets")
        session.add(repo)
        session.flush()
        session.add(IngestionJob(repository_id=repo.id, kind="import", state="queued"))
        session.commit()
        repo_id = repo.id

    runner = IngestionRunner(factory, EmptyGitHub(), EmptyEmbeddings(), JobStore(factory))
    assert runner.run_once() is True
    assert runner.run_once() is False
    with factory() as session:
        assert session.get(Repository, repo_id).status == "ready"
        assert session.query(IngestionJob).one().state == "completed"


def test_runner_failure_preserves_previous_index_and_sanitizes_error() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with Session(engine) as session:
        repo = Repository(
            url="https://github.com/acme/widgets", full_name="acme/widgets",
            active_commit_sha="old", active_index_version=uuid.uuid4(), status="ready",
        )
        session.add(repo)
        session.flush()
        session.add(IngestionJob(repository_id=repo.id, kind="rebuild", state="queued"))
        session.commit()
        repo_id = repo.id

    assert IngestionRunner(factory, FailingGitHub(), EmptyEmbeddings(), JobStore(factory)).run_once()
    with factory() as session:
        repo = session.get(Repository, repo_id)
        job = session.query(IngestionJob).one()
        assert repo.active_commit_sha == "old"
        assert repo.status == "ready"
        assert job.state == "failed"
        assert "secret" not in job.error_message


def test_runner_skips_unchanged_commit_and_policy() -> None:
    from app.rag.file_filter import INDEX_POLICY_VERSION

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with Session(engine) as session:
        repo = Repository(
            url="https://github.com/acme/widgets", full_name="acme/widgets",
            active_commit_sha="commit-123", active_index_policy_version=INDEX_POLICY_VERSION,
            status="ready",
        )
        session.add(repo)
        session.flush()
        session.add(IngestionJob(repository_id=repo.id, kind="rebuild", state="queued"))
        session.commit()

    assert IngestionRunner(factory, EmptyGitHub(), EmptyEmbeddings(), JobStore(factory)).run_once()
    with factory() as session:
        assert session.query(IngestionJob).one().state == "skipped"
