"""Run one durable ingestion job outside HTTP request handling."""

from datetime import datetime, timezone
from threading import Event, Thread
from uuid import UUID

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.github.client import GitHubRateLimitError
from app.persistence.jobs import JobStore
from app.persistence.models import IngestionJob
from app.services.indexing import EmbeddingProvider, GitHubRepositoryReader, IndexingService


def safe_error(error: Exception) -> str:
    """Keep credentials, URLs and source content out of persisted errors."""
    if isinstance(error, GitHubRateLimitError):
        return "GitHub API rate limit reached. Retry after the quota resets."
    if isinstance(error, httpx.TimeoutException):
        return "A GitHub or Ollama request timed out. Check connectivity and retry."
    if isinstance(error, httpx.HTTPStatusError):
        code = error.response.status_code
        if code in (401, 403, 404):
            return "GitHub denied access or the repository was not found. Check the token and URL."
        return f"An external service returned HTTP {code}. Retry after checking the service."
    if isinstance(error, httpx.RequestError):
        return "Could not reach GitHub or Ollama. Check connectivity and retry."
    return "Repository ingestion failed. Check worker logs and retry."


class IngestionRunner:
    def __init__(
        self, session_factory: sessionmaker[Session], github: GitHubRepositoryReader,
        embeddings: EmbeddingProvider, job_store: JobStore,
    ) -> None:
        self._sessions = session_factory
        self._github = github
        self._embeddings = embeddings
        self._jobs = job_store

    def run_once(self) -> bool:
        now = datetime.now(timezone.utc)
        self._jobs.recover_expired(now)
        job_id = self._jobs.claim_next(now)
        if job_id is None:
            return False

        stop = Event()
        heartbeat = Thread(target=self._keep_lease, args=(job_id, stop), daemon=True)
        heartbeat.start()
        try:
            with self._sessions() as session:
                job = session.get(IngestionJob, job_id)
                result = IndexingService(session, self._github, self._embeddings).rebuild(
                    job.repository_id,
                    progress=lambda stage, done, total: self._jobs.progress(job_id, stage, done, total),
                )
                job.state = "completed" if result.changed else "skipped"
                job.stage = job.state
                job.index_version = result.index_version
                job.error_message = None
                job.lease_expires_at = None
                session.commit()
        except Exception as error:
            self._jobs.fail(job_id, safe_error(error))
        finally:
            stop.set()
            heartbeat.join(timeout=2)
        return True

    def _keep_lease(self, job_id: UUID, stop: Event) -> None:
        while not stop.wait(30):
            try:
                self._jobs.heartbeat(job_id, datetime.now(timezone.utc))
            except Exception:
                # A transient heartbeat failure is handled by lease recovery.
                pass
