"""Add replacement index version identifiers."""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_index_versions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("active_index_version", sa.Uuid(), nullable=True))
    op.add_column("source_files", sa.Column("index_version", sa.Uuid(), nullable=True))
    op.execute("UPDATE source_files SET index_version = gen_random_uuid() WHERE index_version IS NULL")
    op.alter_column("source_files", "index_version", nullable=False)
    op.add_column("rebuild_records", sa.Column("index_version", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("rebuild_records", "index_version")
    op.drop_column("source_files", "index_version")
    op.drop_column("repositories", "active_index_version")
