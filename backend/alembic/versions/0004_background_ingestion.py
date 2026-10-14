"""Persist durable ingestion jobs and index selection policy."""

from alembic import op
import sqlalchemy as sa

revision = "0004_background_ingestion"
down_revision = "0003_add_message_sequence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("rebuild_records", "ingestion_jobs")
    op.alter_column("ingestion_jobs", "status", new_column_name="state")
    op.add_column("ingestion_jobs", sa.Column("kind", sa.String(16), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("stage", sa.String(32), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("completed_files", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ingestion_jobs", sa.Column("total_files", sa.Integer(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ingestion_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column("ingestion_jobs", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column("repositories", sa.Column("active_index_policy_version", sa.Integer(), nullable=True))
    op.alter_column("repositories", "default_branch", nullable=True)
    op.execute("UPDATE ingestion_jobs SET kind = 'rebuild'")
    op.alter_column("ingestion_jobs", "kind", nullable=False)
    op.execute("UPDATE ingestion_jobs SET state = 'failed' WHERE state = 'running'")
    op.create_index(
        "uq_ingestion_jobs_active_repository", "ingestion_jobs", ["repository_id"],
        unique=True, postgresql_where=sa.text("state IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_ingestion_jobs_active_repository", table_name="ingestion_jobs")
    op.alter_column("repositories", "default_branch", nullable=False)
    op.drop_column("repositories", "active_index_policy_version")
    for column in ("updated_at", "created_at", "lease_expires_at", "attempt_count", "error_message", "total_files", "completed_files", "stage", "kind"):
        op.drop_column("ingestion_jobs", column)
    op.alter_column("ingestion_jobs", "state", new_column_name="status")
    op.rename_table("ingestion_jobs", "rebuild_records")
