import json

import httpx

from app.rag.ollama import EmbeddingClient


def test_embedding_client_returns_ollama_embeddings() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        assert json.loads(request.content) == {
            "model": "nomic-embed-text:latest",
            "input": ["first", "second"],
        }
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    client = EmbeddingClient(
        base_url="http://ollama.test",
        model="nomic-embed-text:latest",
        transport=httpx.MockTransport(handler),
    )

    assert client.embed(["first", "second"]) == [[0.1, 0.2], [0.3, 0.4]]


def test_embedding_client_allows_local_model_more_than_default_read_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.extensions["timeout"]["read"] >= 60
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    client = EmbeddingClient(
        base_url="http://ollama.test",
        model="nomic-embed-text:latest",
        transport=httpx.MockTransport(handler),
    )

    assert client.embed(["one chunk"]) == [[0.1, 0.2]]
