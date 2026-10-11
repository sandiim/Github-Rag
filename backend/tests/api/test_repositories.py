from fastapi.testclient import TestClient

from app.api.dependencies import get_repository_service
from app.main import create_app
from app.services.repositories import RepositorySummary


class FakeRepositoryService:
    def create(self, url: str) -> RepositorySummary:
        assert url == "https://github.com/acme/widgets"
        return RepositorySummary(id="repo-1", name="widgets", status="ready")

    def list(self) -> list[RepositorySummary]:
        return [RepositorySummary(id="repo-1", name="widgets", status="ready")]


def test_create_and_list_repositories_use_typed_responses() -> None:
    app = create_app()
    app.dependency_overrides[get_repository_service] = lambda: FakeRepositoryService()
    client = TestClient(app)

    created = client.post("/repositories", json={"url": "https://github.com/acme/widgets"})
    listed = client.get("/repositories")

    assert created.status_code == 201
    assert created.json() == {"id": "repo-1", "name": "widgets", "status": "ready"}
    assert listed.status_code == 200
    assert listed.json() == [{"id": "repo-1", "name": "widgets", "status": "ready"}]


def test_create_repository_maps_invalid_url_to_validation_error() -> None:
    class InvalidUrlService:
        def create(self, url: str) -> RepositorySummary:
            raise ValueError("Expected a GitHub repository URL")

    app = create_app()
    app.dependency_overrides[get_repository_service] = lambda: InvalidUrlService()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/repositories", json={"url": "https://github.com/acme/widgets"})

    assert response.status_code == 422
    assert response.json() == {"detail": "Expected a GitHub repository URL"}
