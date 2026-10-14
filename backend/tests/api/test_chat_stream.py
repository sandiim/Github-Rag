import json

from fastapi.testclient import TestClient

from app.api.dependencies import get_chat_stream_service
from app.main import create_app


REPOSITORY_ID = "00000000-0000-0000-0000-000000000001"


def test_chat_stream_route_returns_newline_delimited_events() -> None:
    class FakeStreamService:
        def preflight(self, repository_id):
            assert str(repository_id) == REPOSITORY_ID

        def stream(self, repository_id, question):
            assert question == "Where is the app?"
            yield '{"type":"status","stage":"retrieving"}\n'
            yield '{"type":"complete","text":"In src/app.py","citations":[]}\n'

    app = create_app()
    app.dependency_overrides[get_chat_stream_service] = lambda: FakeStreamService()
    response = TestClient(app).post(
        f"/repositories/{REPOSITORY_ID}/chat/stream", json={"question": "Where is the app?"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert [json.loads(line)["type"] for line in response.text.splitlines()] == ["status", "complete"]


def test_chat_stream_route_reports_missing_index_before_streaming() -> None:
    class NoIndexStreamService:
        def preflight(self, repository_id):
            raise ValueError("Repository has no active index")

    app = create_app()
    app.dependency_overrides[get_chat_stream_service] = lambda: NoIndexStreamService()
    response = TestClient(app).post(
        f"/repositories/{REPOSITORY_ID}/chat/stream", json={"question": "Where?"}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Repository has no active index"}
