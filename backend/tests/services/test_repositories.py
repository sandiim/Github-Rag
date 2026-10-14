import uuid

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.persistence.models import Base, IngestionJob, Repository
from app.services.repositories import RepositoryService


def test_repository_without_messages_has_an_empty_conversation() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
            status="ready",
        )
        session.add(repository)
        session.flush()

        conversation = RepositoryService(session).conversation(str(repository.id))

        assert conversation.title == "widgets"
        assert conversation.messages == []


def test_create_enqueues_once_without_contacting_github() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = RepositoryService(session)
        created = service.create("https://github.com/acme/widgets")
        again = service.create("https://github.com/acme/widgets")
        assert created.id == again.id
        assert created.status == "pending"
        assert created.latest_job.state == "queued"
        assert session.scalar(select(func.count()).select_from(IngestionJob)) == 1


def test_failed_repository_can_enqueue_retry() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = RepositoryService(session)
        created = service.create("https://github.com/acme/widgets")
        job = session.get(IngestionJob, uuid.UUID(created.latest_job.id))
        job.state = "failed"
        session.get(Repository, uuid.UUID(created.id)).status = "failed"
        session.commit()
        retried = service.rebuild(created.id)
        assert retried.id == created.id
        assert retried.latest_job.state == "queued"
        assert session.scalar(select(func.count()).select_from(IngestionJob)) == 2
