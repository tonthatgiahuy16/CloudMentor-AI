"""add document processing activity metadata

Revision ID: 1835db288a63
Revises: 88c313b33018
Create Date: 2026-10-17 15:28:25.629451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1835db288a63'
down_revision: Union[str, Sequence[str], None] = '88c313b33018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "documents",
        sa.Column(
            "processing_attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "last_processing_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "last_processing_heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "current_stage",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "chk_documents_processing_attempt_count",
        "documents",
        "processing_attempt_count >= 0",
    )
    op.create_check_constraint(
        "chk_documents_current_stage",
        "documents",
        "current_stage IS NULL OR current_stage IN "
        "('EXTRACT', 'TRANSFORM', 'CHUNK', "
        "'EMBEDDING', 'INDEX')",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "chk_documents_current_stage",
        "documents",
        type_="check",
    )
    op.drop_constraint(
        "chk_documents_processing_attempt_count",
        "documents",
        type_="check",
    )

    op.drop_column(
        "documents",
        "current_stage",
    )
    op.drop_column(
        "documents",
        "last_processing_heartbeat_at",
    )
    op.drop_column(
        "documents",
        "last_processing_started_at",
    )
    op.drop_column(
        "documents",
        "processing_attempt_count",
    )
    # ### end Alembic commands ###
