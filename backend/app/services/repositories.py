"""Repository creation and listing workflows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.github.client import parse_repository_url
from app.persistence.models import Citation, Conversation, IngestionJob, Message, Repository


@dataclass(frozen=True)
class RepositorySummary:
    id: str
    name: str
    status: str
    latest_job: IngestionJobSummary | None = None


@dataclass(frozen=True)
class IngestionJobSummary:
    id: str
    state: str
    stage: str | None
    completed_files: int
    total_files: int | None
    error_message: str | None


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
    def __init__(self, session: Session, github: object = None, indexing: object = None) -> None:
        self._session = session

    def create(self, url: str) -> RepositorySummary:
        reference = parse_repository_url(url)
        full_name = f"{reference.owner}/{reference.name}"
        existing = self._session.scalar(select(Repository).where(Repository.full_name == full_name))
        if existing is not None:
            return self._summary(existing)
        repository = Repository(
            url=f"https://github.com/{full_name}",
            full_name=full_name,
            default_branch=None,
            status="pending",
        )
        self._session.add(repository)
        self._session.flush()
        self._session.add(IngestionJob(
            repository_id=repository.id, kind="import", state="queued",
            created_at=datetime.now(timezone.utc),
        ))
        self._session.commit()
        return self._summary(repository)

    def list(self) -> list[RepositorySummary]:
        return [self._summary(repository) for repository in self._session.scalars(select(Repository)).all()]

    def get(self, repository_id: str) -> RepositorySummary:
        return self._summary(self._repository(repository_id))

    def rebuild(self, repository_id: str) -> RepositorySummary:
        repository = self._repository(repository_id)
        active = self._session.scalar(
            select(IngestionJob).where(
                IngestionJob.repository_id == repository.id,
                IngestionJob.state.in_(("queued", "running")),
            )
        )
        if active is not None:
            return self._summary(repository)
        self._session.add(IngestionJob(
            repository_id=repository.id, kind="rebuild", state="queued",
            created_at=datetime.now(timezone.utc),
        ))
        self._session.commit()
        return self._summary(repository)

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

    def _summary(self, repository: Repository) -> RepositorySummary:
        job = self._session.scalar(
            select(IngestionJob).where(IngestionJob.repository_id == repository.id)
            .order_by(IngestionJob.created_at.desc(), IngestionJob.id.desc()).limit(1)
        )
        return RepositorySummary(
            id=str(repository.id),
            name=repository.full_name.rsplit("/", 1)[-1],
            status=repository.status,
            latest_job=IngestionJobSummary(
                id=str(job.id), state=job.state, stage=job.stage,
                completed_files=job.completed_files, total_files=job.total_files,
                error_message=job.error_message,
            ) if job is not None else None,
        )
