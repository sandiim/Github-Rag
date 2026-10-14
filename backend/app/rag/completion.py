"""OpenAI-compatible grounded completion adapter."""

import json

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

        insufficient = "There is not enough information in the provided repository context to answer."
        if not context:
            return insufficient

        context_text = "\n\n".join(
            f"[{number}] {chunk.path}:{chunk.start_line}-{chunk.end_line}\n{chunk.text}"
            for number, chunk in enumerate(context, 1)
        )
        schema = {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source_ids": {
                                "type": "array",
                                "items": {"type": "integer", "enum": list(range(1, len(context) + 1))},
                            },
                        },
                        "required": ["text", "source_ids"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["sections"],
            "additionalProperties": False,
        }
        response = self._client.post(
            "chat/completions",
            json={
                "model": self._model,
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "grounded_answer", "schema": schema, "strict": True},
                },
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the provided repository context. "
                            "Return a JSON object with sections. Each section must be a complete "
                            "explanatory paragraph in the question's language, not just a heading. "
                            "List the numbered source IDs that support that paragraph. "
                            "If the context is insufficient, return an empty sections array."
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
        try:
            sections = json.loads(response.json()["choices"][0]["message"]["content"])["sections"]
            if not isinstance(sections, list):
                return insufficient
        except (KeyError, TypeError, ValueError):
            return insufficient

        paragraphs: list[str] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            text = section.get("text")
            source_ids = section.get("source_ids")
            if not isinstance(text, str) or not isinstance(source_ids, list):
                continue
            valid_ids = dict.fromkeys(
                source_id for source_id in source_ids
                if type(source_id) is int and 1 <= source_id <= len(context)
            )
            if text.strip() and valid_ids:
                paragraphs.append(f"{text.strip()} " + "".join(f"[{source_id}]" for source_id in valid_ids))
        return "\n\n".join(paragraphs) or insufficient
