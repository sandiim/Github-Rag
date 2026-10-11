"""Add deterministic conversation message ordering."""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_message_sequence"
down_revision = "0002_add_index_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("sequence", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH numbered AS (
            SELECT id, row_number() OVER (PARTITION BY conversation_id ORDER BY id) AS sequence
            FROM messages
        )
        UPDATE messages
        SET sequence = numbered.sequence
        FROM numbered
        WHERE messages.id = numbered.id
        """
    )
    op.alter_column("messages", "sequence", nullable=False)
    op.create_unique_constraint("uq_messages_conversation_sequence", "messages", ["conversation_id", "sequence"])


def downgrade() -> None:
    op.drop_constraint("uq_messages_conversation_sequence", "messages", type_="unique")
    op.drop_column("messages", "sequence")
