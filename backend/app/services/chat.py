"""Durable grounded repository chat orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.persistence.models import Citation, Conversation, Message, Repository
from app.rag.citations import build_github_url, resolve_citation_markers
from app.rag.retrieval import RetrievedChunk


class ChunkRetriever(Protocol):
    def retrieve(self, repository_id: uuid.UUID, question: str) -> list[RetrievedChunk]: ...


class AnswerGenerator(Protocol):
    def answer(self, question: str, context: list[RetrievedChunk]) -> str: ...


@dataclass(frozen=True)
class CitationResult:
    path: str
    start_line: int
    end_line: int
    url: str


@dataclass(frozen=True)
class ChatAnswer:
    text: str
    citations: list[CitationResult]


def build_chat_answer(full_name: str, raw_answer: str, context: list[RetrievedChunk]) -> ChatAnswer:
    """Resolve model source markers into checked file-line citations."""

    text, used_indices = resolve_citation_markers(raw_answer, context)
    citations = [
        CitationResult(
            path=context[index].path,
            start_line=context[index].start_line,
            end_line=context[index].end_line,
            url=build_github_url(
                full_name,
                context[index].commit_sha,
                context[index].path,
                context[index].start_line,
                context[index].end_line,
            ),
        )
        for index in used_indices
    ]
    return ChatAnswer(text=text, citations=citations)


class ChatService:
    """Persist questions and grounded responses for a repository conversation."""

    def __init__(self, session: Session, retriever: ChunkRetriever, generator: AnswerGenerator) -> None:
        self._session = session
        self._retriever = retriever
        self._generator = generator

    def ask(self, repository_id: uuid.UUID, question: str) -> ChatAnswer:
        """Answer a question from the active index and persist its supporting citations."""

        repository = self._session.get(Repository, repository_id)
        if repository is None:
            raise LookupError("Repository was not found")
        if repository.active_index_version is None:
            raise ValueError("Repository has no active index")

        context = self._retriever.retrieve(repository_id, question)
        raw_answer = self._generator.answer(question, context)
        return self.persist_answer(repository_id, question, raw_answer, context)

    def persist_answer(
        self, repository_id: uuid.UUID, question: str, raw_answer: str,
        context: list[RetrievedChunk],
    ) -> ChatAnswer:
        """Commit one validated user/assistant turn after generation has finished."""

        repository = self._session.get(Repository, repository_id)
        if repository is None:
            raise LookupError("Repository was not found")
        if repository.active_index_version is None:
            raise ValueError("Repository has no active index")
        answer = build_chat_answer(repository.full_name, raw_answer, context)

        conversation = self._session.scalar(
            select(Conversation).where(Conversation.repository_id == repository_id)
        )
        if conversation is None:
            conversation = Conversation(repository_id=repository_id, title=repository.full_name.rsplit("/", 1)[-1])
            self._session.add(conversation)
            self._session.flush()

        next_sequence = (
            self._session.scalar(
                select(func.coalesce(func.max(Message.sequence), 0)).where(
                    Message.conversation_id == conversation.id
                )
            )
            + 1
        )
        self._session.add(
            Message(
                conversation_id=conversation.id,
                sequence=next_sequence,
                role="user",
                content=question,
            )
        )
        assistant_message = Message(
            conversation_id=conversation.id,
            sequence=next_sequence + 1,
            role="assistant",
            content=answer.text,
        )
        self._session.add(assistant_message)
        self._session.flush()

        self._session.add_all(
            Citation(
                message_id=assistant_message.id,
                path=citation.path,
                start_line=citation.start_line,
                end_line=citation.end_line,
                url=citation.url,
            )
            for citation in answer.citations
        )
        self._session.flush()
        self._session.commit()
        return answer
