"""Repository creation and listing workflows."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.github.client import GitHubClient
from app.persistence.models import Citation, Conversation, Message, Repository
from app.services.indexing import IndexingService


@dataclass(frozen=True)
class RepositorySummary:
    id: str
    name: str
    status: str


@dataclass(frozen=True)
class RebuildSummary:
    changed: bool
    status: str


@dataclass(frozen=True)
class CitationSummary:
    path: str
    start_line: int
    end_line: int
    url: str


@dataclass(frozen=True)
class MessageSummary:
    role: str
    content: str
    citations: list[CitationSummary]


@dataclass(frozen=True)
class ConversationSummary:
    title: str
    messages: list[MessageSummary]


class RepositoryService:
    def __init__(self, session: Session, github: GitHubClient, indexing: IndexingService) -> None:
        self._session = session
        self._github = github
        self._indexing = indexing

    def create(self, url: str) -> RepositorySummary:
        resolved = self._github.resolve(url)
        repository = Repository(
            url=url,
            full_name=f"{resolved.reference.owner}/{resolved.reference.name}",
            default_branch=resolved.default_branch,
        )
        self._session.add(repository)
        self._session.flush()
        self._indexing.rebuild(repository.id)
        self._session.commit()
        return self._summary(repository)

    def list(self) -> list[RepositorySummary]:
        return [self._summary(repository) for repository in self._session.scalars(select(Repository)).all()]

    def get(self, repository_id: str) -> RepositorySummary:
        return self._summary(self._repository(repository_id))

    def rebuild(self, repository_id: str) -> RebuildSummary:
        repository = self._repository(repository_id)
        result = self._indexing.rebuild(repository.id)
        self._session.commit()
        return RebuildSummary(changed=result.changed, status=repository.status)

    def conversation(self, repository_id: str) -> ConversationSummary:
        repository = self._repository(repository_id)
        conversation = self._session.scalar(
            select(Conversation).where(Conversation.repository_id == repository.id)
        )
        if conversation is None:
            return ConversationSummary(title=repository.full_name.rsplit("/", 1)[-1], messages=[])
        messages = self._session.scalars(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.sequence)
        ).all()
        return ConversationSummary(
            title=conversation.title,
            messages=[
                MessageSummary(
                    role=message.role,
                    content=message.content,
                    citations=[
                        CitationSummary(
                            path=citation.path,
                            start_line=citation.start_line,
                            end_line=citation.end_line,
                            url=citation.url,
                        )
                        for citation in self._session.scalars(
                            select(Citation).where(Citation.message_id == message.id)
                        ).all()
                    ],
                )
                for message in messages
            ],
        )

    def _repository(self, repository_id: str) -> Repository:
        repository = self._session.get(Repository, uuid.UUID(repository_id))
        if repository is None:
            raise LookupError("Repository was not found")
        return repository

    @staticmethod
    def _summary(repository: Repository) -> RepositorySummary:
        return RepositorySummary(
            id=str(repository.id),
            name=repository.full_name.rsplit("/", 1)[-1],
            status=repository.status,
        )
