"""OpenAI-compatible grounded completion adapter."""

import json
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from app.rag.retrieval import RetrievedChunk
from app.rag.section_stream import CompletedSection, DraftDelta, SectionStream


INSUFFICIENT = "There is not enough information in the provided repository context to answer."


@dataclass(frozen=True)
class AnswerDelta:
    text: str


@dataclass(frozen=True)
class AnswerCheckpoint:
    text: str


@dataclass(frozen=True)
class AnswerComplete:
    text: str


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

        if not context:
            return INSUFFICIENT

        response = self._client.post(
            "chat/completions",
            json=self._payload(question, context),
        )
        response.raise_for_status()
        try:
            sections = json.loads(response.json()["choices"][0]["message"]["content"])["sections"]
        except (KeyError, TypeError, ValueError):
            return INSUFFICIENT
        return self._render_sections(sections, context)

    def stream_answer(
        self, question: str, context: list[RetrievedChunk]
    ) -> Iterator[AnswerDelta | AnswerCheckpoint | AnswerComplete]:
        """Yield readable draft fragments and validated section checkpoints."""

        if not context:
            yield AnswerComplete(INSUFFICIENT)
            return

        parser = SectionStream()
        confirmed: list[str] = []
        drafting = False
        finished = False
        with self._client.stream(
            "POST", "chat/completions", json=self._payload(question, context, stream=True),
            timeout=httpx.Timeout(180.0, connect=10.0),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    finished = True
                    break
                fragment = json.loads(data)["choices"][0].get("delta", {}).get("content")
                if not fragment:
                    continue
                for event in parser.feed(fragment):
                    if isinstance(event, DraftDelta):
                        prefix = "\n\n" if confirmed and not drafting else ""
                        yield AnswerDelta(prefix + event.text)
                        drafting = True
                    elif isinstance(event, CompletedSection):
                        paragraph = self._render_section(event.section, context)
                        if paragraph:
                            confirmed.append(paragraph)
                        yield AnswerCheckpoint("\n\n".join(confirmed))
                        drafting = False
        if not finished:
            raise RuntimeError("The model stream ended before completion")
        try:
            sections = json.loads(parser.raw)["sections"]
        except (KeyError, TypeError, ValueError):
            sections = []
        yield AnswerComplete(self._render_sections(sections, context))

    def _payload(self, question: str, context: list[RetrievedChunk], stream: bool = False) -> dict:
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
        payload = {
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
        }
        if stream:
            payload["stream"] = True
        return payload

    @classmethod
    def _render_sections(cls, sections: object, context: list[RetrievedChunk]) -> str:
        if not isinstance(sections, list):
            return INSUFFICIENT
        paragraphs = [cls._render_section(section, context) for section in sections]
        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph) or INSUFFICIENT

    @staticmethod
    def _render_section(section: object, context: list[RetrievedChunk]) -> str | None:
        if not isinstance(section, dict):
            return None
        text = section.get("text")
        source_ids = section.get("source_ids")
        if not isinstance(text, str) or not isinstance(source_ids, list):
            return None
        if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
            return None
        valid_ids = dict.fromkeys(
            source_id for source_id in source_ids
            if type(source_id) is int and 1 <= source_id <= len(context)
        )
        if text.strip() and valid_ids:
            return f"{text.strip()} " + "".join(f"[{source_id}]" for source_id in valid_ids)
        return None
