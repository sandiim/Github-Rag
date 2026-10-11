"""Ollama embedding adapter."""

import httpx


class EmbeddingClient:
    """Request batch embeddings from a locally configured Ollama server."""

    def __init__(
        self,
        base_url: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        self._client = httpx.Client(base_url=base_url, transport=transport)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed text in order using Ollama's batch embedding endpoint."""

        if not texts:
            return []
        response = self._client.post("/api/embed", json={"model": self._model, "input": texts})
        response.raise_for_status()
        return response.json()["embeddings"]
