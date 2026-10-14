import json

import httpx

from app.rag.completion import CompletionClient
from app.rag.retrieval import RetrievedChunk


def test_completion_client_sends_grounding_context_to_openai_compatible_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "llama3.1:latest"
        assert "[1] src/app.py:10-10" in payload["messages"][1]["content"]
        assert "[1]" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "The app is created in src/app.py."}}]},
        )

    client = CompletionClient(
        base_url="http://llm.test/v1",
        api_key="test-key",
        model="llama3.1:latest",
        transport=httpx.MockTransport(handler),
    )

    answer = client.answer(
        "Where is the app created?",
        [
            RetrievedChunk(
                path="src/app.py",
                text="app = FastAPI()",
                start_line=10,
                end_line=10,
                commit_sha="abc123",
                score=0.9,
            )
        ],
    )

    assert answer == "The app is created in src/app.py."
