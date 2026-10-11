from __future__ import annotations

import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.persistence.models import Base, Citation, Message, Repository
from app.rag.retrieval import RetrievedChunk
from app.services.chat import ChatService


class StubRetriever:
    def retrieve(self, repository_id, question: str) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                path="src/app.py",
                text="app = FastAPI()",
                start_line=10,
                end_line=10,
                commit_sha="abc123",
                score=0.9,
            )
        ]


class StubAnswerGenerator:
    def answer(self, question: str, context: list[RetrievedChunk]) -> str:
        return "The application is created in src/app.py."


def test_ask_persists_a_grounded_answer_with_commit_pinned_citation() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
            active_commit_sha="abc123",
            active_index_version=uuid.uuid4(),
        )
        session.add(repository)
        session.flush()

        answer = ChatService(session, StubRetriever(), StubAnswerGenerator()).ask(
            repository.id,
            "Where is the application created?",
        )

        messages = session.scalars(select(Message).order_by(Message.id)).all()
        citations = session.scalars(select(Citation)).all()
        assert answer.text == "The application is created in src/app.py."
        assert answer.citations[0].url == (
            "https://github.com/acme/widgets/blob/abc123/src/app.py#L10-L10"
        )
        assert [message.role for message in messages] == ["user", "assistant"]
        assert [citation.url for citation in citations] == [
            "https://github.com/acme/widgets/blob/abc123/src/app.py#L10-L10"
        ]


def test_ask_rejects_a_repository_without_an_active_index() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
        )
        session.add(repository)
        session.flush()

        try:
            ChatService(session, StubRetriever(), StubAnswerGenerator()).ask(repository.id, "Question")
        except ValueError as error:
            assert str(error) == "Repository has no active index"
        else:
            raise AssertionError("Expected an active-index validation error")
