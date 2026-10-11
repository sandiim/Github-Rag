"""Repository-oriented persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.persistence.models import Conversation, Repository


class RepositoryStore:
    """Persist repositories and their one durable conversation."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, url: str, full_name: str, default_branch: str) -> Repository:
        repository = Repository(url=url, full_name=full_name, default_branch=default_branch)
        self._session.add(repository)
        self._session.flush()
        return repository

    def get_or_create_conversation(self, repository_id, title: str) -> Conversation:
        conversation = self._session.scalar(
            select(Conversation).where(Conversation.repository_id == repository_id)
        )
        if conversation is None:
            conversation = Conversation(repository_id=repository_id, title=title)
            self._session.add(conversation)
            self._session.flush()
        return conversation
