"""Durable NDJSON chat streaming with generator-owned database sessions."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import Repository
from app.rag.completion import AnswerCheckpoint, AnswerComplete, AnswerDelta
from app.rag.retrieval import RetrievedChunk
from app.services.chat import ChatService, ChunkRetriever, build_chat_answer


class StreamingAnswerGenerator(Protocol):
    def stream_answer(
        self, question: str, context: list[RetrievedChunk]
    ) -> Iterator[AnswerDelta | AnswerCheckpoint | AnswerComplete]: ...


def _line(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


class StreamingChatService:
    """Own the database session until the final event or client disconnect."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        retriever_factory: Callable[[Session], ChunkRetriever],
        generator: StreamingAnswerGenerator,
    ) -> None:
        self._session_factory = session_factory
        self._retriever_factory = retriever_factory
        self._generator = generator

    def preflight(self, repository_id: uuid.UUID) -> None:
        """Raise before response headers if the repository cannot be chatted with."""

        with self._session_factory() as session:
            repository = session.get(Repository, repository_id)
            if repository is None:
                raise LookupError("Repository was not found")
            if repository.active_index_version is None:
                raise ValueError("Repository has no active index")

    def stream(self, repository_id: uuid.UUID, question: str) -> Iterator[str]:
        yield _line({"type": "status", "stage": "retrieving"})
        with self._session_factory() as session:
            try:
                repository = session.get(Repository, repository_id)
                if repository is None or repository.active_index_version is None:
                    raise ValueError("Repository is no longer ready")
                full_name = repository.full_name
                retriever = self._retriever_factory(session)
                context = retriever.retrieve(repository_id, question)
                session.rollback()  # Do not hold a DB transaction during local model generation.
                yield _line({"type": "status", "stage": "generating"})

                completed = False
                for event in self._generator.stream_answer(question, context):
                    if isinstance(event, AnswerDelta):
                        yield _line({"type": "delta", "text": event.text})
                    elif isinstance(event, AnswerCheckpoint):
                        answer = build_chat_answer(full_name, event.text, context)
                        yield _line({
                            "type": "checkpoint", "text": answer.text,
                            "citations": [asdict(citation) for citation in answer.citations],
                        })
                    elif isinstance(event, AnswerComplete):
                        answer = ChatService(session, retriever, self._generator).persist_answer(
                            repository_id, question, event.text, context
                        )
                        completed = True
                        yield _line({
                            "type": "complete", "text": answer.text,
                            "citations": [asdict(citation) for citation in answer.citations],
                        })
                if not completed:
                    raise RuntimeError("The model stream did not finish")
            except Exception:
                session.rollback()
                yield _line({
                    "type": "error", "message": "Answer generation failed. Please try again."
                })
