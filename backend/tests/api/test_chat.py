from fastapi.testclient import TestClient

from app.api.dependencies import get_chat_service, get_repository_service
from app.main import create_app
from app.services.chat import ChatAnswer, CitationResult
from app.services.repositories import ConversationSummary, MessageSummary, RepositorySummary

REPOSITORY_ID = "00000000-0000-0000-0000-000000000001"


class FakeRepositoryService:
    def get(self, repository_id: str) -> RepositorySummary:
        assert repository_id == REPOSITORY_ID
        return RepositorySummary(id=repository_id, name="widgets", status="ready")

    def rebuild(self, repository_id: str) -> RepositorySummary:
        assert repository_id == REPOSITORY_ID
        return RepositorySummary(id=repository_id, name="widgets", status="ready")

    def conversation(self, repository_id: str) -> ConversationSummary:
        assert repository_id == REPOSITORY_ID
        return ConversationSummary(
            title="widgets",
            messages=[MessageSummary(role="user", content="Where is the app?", citations=[])],
        )


class FakeChatService:
    def ask(self, repository_id: str, question: str) -> ChatAnswer:
        assert repository_id == REPOSITORY_ID
        assert question == "Where is the app?"
        return ChatAnswer(
            text="It is in src/app.py.",
            citations=[
                CitationResult(
                    path="src/app.py",
                    start_line=10,
                    end_line=10,
                    url="https://github.com/acme/widgets/blob/abc/src/app.py#L10-L10",
                )
            ],
        )


def test_repository_rebuild_conversation_and_chat_routes_return_typed_data() -> None:
    app = create_app()
    app.dependency_overrides[get_repository_service] = lambda: FakeRepositoryService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    repository = client.get(f"/repositories/{REPOSITORY_ID}")
    rebuilt = client.post(f"/repositories/{REPOSITORY_ID}/rebuild")
    conversation = client.get(f"/repositories/{REPOSITORY_ID}/conversation")
    answer = client.post(f"/repositories/{REPOSITORY_ID}/chat", json={"question": "Where is the app?"})

    assert repository.json() == {"id": REPOSITORY_ID, "name": "widgets", "status": "ready", "ingestion": None}
    assert rebuilt.status_code == 202
    assert rebuilt.json() == repository.json()
    assert conversation.json()["messages"][0]["content"] == "Where is the app?"
    assert answer.json()["citations"][0]["path"] == "src/app.py"


def test_chat_without_an_active_index_returns_conflict() -> None:
    class NoIndexChatService:
        def ask(self, repository_id: str, question: str) -> ChatAnswer:
            raise ValueError("Repository has no active index")

    app = create_app()
    app.dependency_overrides[get_chat_service] = lambda: NoIndexChatService()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(f"/repositories/{REPOSITORY_ID}/chat", json={"question": "Where is the app?"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Repository has no active index"}
