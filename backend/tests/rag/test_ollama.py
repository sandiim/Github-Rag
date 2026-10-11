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
