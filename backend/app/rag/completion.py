"""OpenAI-compatible grounded completion adapter."""

import httpx

from app.rag.retrieval import RetrievedChunk


class CompletionClient:
    """Generate repository answers from explicit retrieved source context."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def answer(self, question: str, context: list[RetrievedChunk]) -> str:
        """Ask the configured model to answer using only retrieved source text."""

        context_text = "\n\n".join(
            f"[{chunk.path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.text}" for chunk in context
        )
        response = self._client.post(
            "chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the provided repository context. "
                            "If it is insufficient, say so plainly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nRepository context:\n{context_text}",
                    },
                ],
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
