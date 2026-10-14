from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.jobs import JobStore
from app.persistence.models import Base, IngestionJob, Repository
import pytest


def test_claim_is_exclusive_and_expired_job_retries_once() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with Session(engine) as session:
        repo = Repository(url="https://github.com/acme/widgets", full_name="acme/widgets")
        session.add(repo)
        session.flush()
        job = IngestionJob(repository_id=repo.id, kind="import", state="queued")
        session.add(job)
        session.commit()
        job_id = job.id

    store = JobStore(factory)
    now = datetime.now(timezone.utc)
    assert store.claim_next(now) == job_id
    assert store.claim_next(now) is None
    store.progress(job_id, "embedding", 3, 10)
    with factory() as session:
        saved = session.get(IngestionJob, job_id)
        assert (saved.stage, saved.completed_files, saved.total_files) == ("embedding", 3, 10)
    store.recover_expired(now + timedelta(minutes=6))
    assert store.claim_next(now + timedelta(minutes=6)) == job_id
    store.recover_expired(now + timedelta(minutes=12))
    with factory() as session:
        assert session.get(IngestionJob, job_id).state == "failed"


def test_partial_index_rejects_two_active_jobs_for_one_repository() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repo = Repository(url="https://github.com/acme/widgets", full_name="acme/widgets")
        session.add(repo)
        session.flush()
        session.add(IngestionJob(repository_id=repo.id, kind="import", state="queued"))
        session.flush()
        session.add(IngestionJob(repository_id=repo.id, kind="rebuild", state="running"))
        with pytest.raises(IntegrityError):
            session.flush()
