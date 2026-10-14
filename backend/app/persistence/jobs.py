"""Short, durable transactions for ingestion job ownership and progress."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.models import IngestionJob, Repository

LEASE_DURATION = timedelta(minutes=5)


class JobStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def claim_next(self, now: datetime) -> UUID | None:
        with self._sessions.begin() as session:
            job = session.scalar(
                select(IngestionJob).where(IngestionJob.state == "queued")
                .order_by(IngestionJob.created_at, IngestionJob.id)
                .with_for_update(skip_locked=True).limit(1)
            )
            if job is None:
                return None
            job.state = "running"
            job.stage = "resolving"
            job.attempt_count += 1
            job.lease_expires_at = now + LEASE_DURATION
            return job.id

    def heartbeat(self, job_id: UUID, now: datetime) -> None:
        with self._sessions.begin() as session:
            job = session.get(IngestionJob, job_id)
            if job is not None and job.state == "running":
                job.lease_expires_at = now + LEASE_DURATION

    def progress(self, job_id: UUID, stage: str, done: int, total: int | None) -> None:
        with self._sessions.begin() as session:
            job = session.get(IngestionJob, job_id)
            if job is not None and job.state == "running":
                job.stage = stage
                job.completed_files = done
                job.total_files = total
                job.lease_expires_at = datetime.now(timezone.utc) + LEASE_DURATION

    def fail(self, job_id: UUID, safe_message: str) -> None:
        with self._sessions.begin() as session:
            job = session.get(IngestionJob, job_id)
            if job is None:
                return
            job.state = "failed"
            job.stage = "failed"
            job.error_message = safe_message
            job.lease_expires_at = None
            repository = session.get(Repository, job.repository_id)
            if repository.active_index_version is None:
                repository.status = "failed"

    def recover_expired(self, now: datetime) -> None:
        with self._sessions.begin() as session:
            jobs = session.scalars(
                select(IngestionJob).where(
                    IngestionJob.state == "running",
                    IngestionJob.lease_expires_at < now,
                ).with_for_update(skip_locked=True)
            ).all()
            for job in jobs:
                job.lease_expires_at = None
                if job.attempt_count < 2:
                    job.state = "queued"
                    job.stage = "waiting"
                    job.completed_files = 0
                    job.total_files = None
                else:
                    job.state = "failed"
                    job.stage = "failed"
                    job.error_message = "Worker stopped twice while processing this repository. Retry manually."
                    repository = session.get(Repository, job.repository_id)
                    if repository.active_index_version is None:
                        repository.status = "failed"
