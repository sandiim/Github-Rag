from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_session
from app.github.models import GitHubRepository, RepositoryReference
from app.main import create_app
from app.persistence.jobs import JobStore
from app.persistence.models import Base
from app.services.ingestion import IngestionRunner


class EmptyGitHub:
    def resolve(self, url: str) -> GitHubRepository:
        return GitHubRepository(RepositoryReference("acme", "widgets"), "main", "commit-123")

    def list_candidates(self, repository: GitHubRepository) -> list:
        return []


class EmptyEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return []


def test_request_enqueues_then_worker_activates_index() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    app = create_app()

    def test_session():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    client = TestClient(app)
    created = client.post("/repositories", json={"url": "https://github.com/acme/widgets"})
    assert created.status_code == 202
    assert created.json()["ingestion"]["state"] == "queued"
    repo_id = created.json()["id"]
    assert client.get(f"/repositories/{repo_id}/conversation").json()["messages"] == []

    runner = IngestionRunner(sessions, EmptyGitHub(), EmptyEmbeddings(), JobStore(sessions))
    assert runner.run_once()
    refreshed = client.get(f"/repositories/{repo_id}")
    assert refreshed.json()["status"] == "ready"
    assert refreshed.json()["ingestion"]["state"] == "completed"
