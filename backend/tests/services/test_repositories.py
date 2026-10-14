from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.persistence.models import Base, Repository
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

        conversation = RepositoryService(session, github=None, indexing=None).conversation(str(repository.id))

        assert conversation.title == "widgets"
        assert conversation.messages == []
