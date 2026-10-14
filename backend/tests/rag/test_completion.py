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
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["temperature"] == 0
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"sections": [
                {"text": "The app is created in src/app.py.", "source_ids": [1]}
            ]})}}]},
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

    assert answer == "The app is created in src/app.py. [1]"


def test_completion_client_rejects_source_ids_outside_the_supplied_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "sections": [{"text": "The app runs here.", "source_ids": [1, 99, 1]}]
        })}}]})

    client = CompletionClient("http://llm.test/v1", "test-key", "llama3.1:latest", httpx.MockTransport(handler))
    answer = client.answer("Where?", [RetrievedChunk("src/app.py", "app = FastAPI()", 10, 10, "abc123", 0.9)])

    assert answer == "The app runs here. [1]"


def test_completion_client_does_not_present_uncited_sections_as_grounded_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "sections": [{"text": "Unsupported claim.", "source_ids": [99]}]
        })}}]})

    client = CompletionClient("http://llm.test/v1", "test-key", "llama3.1:latest", httpx.MockTransport(handler))
    answer = client.answer("What?", [RetrievedChunk("README.md", "Evidence", 1, 1, "abc123", 0.9)])

    assert answer == "There is not enough information in the provided repository context to answer."


def test_completion_client_skips_model_call_when_no_context_is_available() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("A context-free answer must not call the model")

    client = CompletionClient("http://llm.test/v1", "test-key", "llama3.1:latest", httpx.MockTransport(handler))

    assert client.answer("What?", []) == (
        "There is not enough information in the provided repository context to answer."
    )
