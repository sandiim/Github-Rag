from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.persistence.models import Base
from app.persistence.repositories import RepositoryStore


def test_repository_has_one_durable_conversation() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        store = RepositoryStore(session)
        repository = store.create(
            url="https://github.com/acme/widgets",
            full_name="acme/widgets",
            default_branch="main",
        )
        first = store.get_or_create_conversation(repository.id, "widgets")
        second = store.get_or_create_conversation(repository.id, "widgets")

    assert first.id == second.id
    assert first.title == "widgets"
