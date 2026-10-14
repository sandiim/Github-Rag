from app.persistence.models import IngestionJob, Repository


def test_ingestion_model_preserves_job_history_shape() -> None:
    assert IngestionJob.__table__.name == "ingestion_jobs"
    assert Repository.__table__.c.default_branch.nullable
    assert "uq_ingestion_jobs_active_repository" in {
        index.name for index in IngestionJob.__table__.indexes
    }
