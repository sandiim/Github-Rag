"""Create the initial RAG persistence schema."""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "repositories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False, unique=True),
        sa.Column("full_name", sa.String(512), nullable=False, unique=True),
        sa.Column("default_branch", sa.String(255), nullable=False),
        sa.Column("active_commit_sha", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("repository_id", sa.Uuid(), sa.ForeignKey("repositories.id"), nullable=False, unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "source_files",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("repository_id", sa.Uuid(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_file_id", sa.Uuid(), sa.ForeignKey("source_files.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_table(
        "citations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("message_id", sa.Uuid(), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(4096), nullable=False),
    )
    op.create_table(
        "rebuild_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("repository_id", sa.Uuid(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rebuild_records")
    op.drop_table("citations")
    op.drop_table("messages")
    op.drop_table("chunks")
    op.drop_table("source_files")
    op.drop_table("conversations")
    op.drop_table("repositories")
