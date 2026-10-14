from __future__ import annotations

import json
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.persistence.models import Base, Message, Repository
from app.rag.completion import AnswerCheckpoint, AnswerComplete, AnswerDelta
from app.rag.retrieval import RetrievedChunk
from app.services.chat_stream import StreamingChatService


class StubRetriever:
    def retrieve(self, repository_id, question):
        return [RetrievedChunk("src/app.py", "app = FastAPI()", 10, 10, "abc123", 0.9)]


class StubCompletion:
    def stream_answer(self, question, context):
        yield AnswerDelta("The app ")
        yield AnswerDelta("runs here.")
        yield AnswerCheckpoint("The app runs here. [1]")
        yield AnswerComplete("The app runs here. [1]")


def setup_repository():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    repository_id = uuid.uuid4()
    with factory() as session:
        session.add(Repository(
            id=repository_id, url="https://github.com/acme/widgets", full_name="acme/widgets",
            active_index_version=uuid.uuid4(), active_commit_sha="abc123",
        ))
        session.commit()
    return factory, repository_id


def test_stream_emits_cited_checkpoint_then_commits_final_conversation() -> None:
    factory, repository_id = setup_repository()
    service = StreamingChatService(factory, lambda session: StubRetriever(), StubCompletion())

    service.preflight(repository_id)
    events = [json.loads(line) for line in service.stream(repository_id, "Where is the app?")]

    assert [event["type"] for event in events] == [
        "status", "status", "delta", "delta", "checkpoint", "complete"
    ]
    assert events[0]["stage"] == "retrieving"
    assert events[1]["stage"] == "generating"
    assert events[4]["text"] == "The app runs here. [src/app.py:10-10]"
    assert events[4]["citations"][0]["url"] == (
        "https://github.com/acme/widgets/blob/abc123/src/app.py#L10-L10"
    )
    assert events[5]["text"] == events[4]["text"]
    with factory() as session:
        roles = [message.role for message in session.scalars(select(Message).order_by(Message.sequence))]
        assert roles == [
            "user", "assistant"
        ]


def test_failed_stream_exposes_safe_error_without_persisting_partial_messages() -> None:
    factory, repository_id = setup_repository()

    class FailingCompletion:
        def stream_answer(self, question, context):
            yield AnswerDelta("A provisional claim")
            raise RuntimeError("secret model failure")

    service = StreamingChatService(factory, lambda session: StubRetriever(), FailingCompletion())
    events = [json.loads(line) for line in service.stream(repository_id, "Where is the app?")]

    assert [event["type"] for event in events] == ["status", "status", "delta", "error"]
    assert "secret" not in events[-1]["message"]
    with factory() as session:
        assert session.scalars(select(Message)).all() == []


def test_closed_stream_does_not_persist_a_partial_turn() -> None:
    factory, repository_id = setup_repository()
    service = StreamingChatService(factory, lambda session: StubRetriever(), StubCompletion())
    stream = service.stream(repository_id, "Where is the app?")

    assert json.loads(next(stream))["type"] == "status"
    assert json.loads(next(stream))["type"] == "status"
    assert json.loads(next(stream))["type"] == "delta"
    stream.close()

    with factory() as session:
        assert session.scalars(select(Message)).all() == []


def test_closed_stream_closes_the_model_response() -> None:
    factory, repository_id = setup_repository()
    closed = False

    class ClosableCompletion:
        def stream_answer(self, question, context):
            nonlocal closed
            try:
                yield AnswerDelta("Still generating")
                yield AnswerComplete("Finished [1]")
            finally:
                closed = True

    service = StreamingChatService(factory, lambda session: StubRetriever(), ClosableCompletion())
    stream = service.stream(repository_id, "Where is the app?")
    next(stream)
    next(stream)
    next(stream)
    stream.close()

    assert closed is True
