"""add policy effective windows and indexed chunk count

Revision ID: 7a2d5f1c9b31
Revises: bc77e2046bc3
Create Date: 2026-11-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a2d5f1c9b31"
down_revision: Union[str, Sequence[str], None] = "bc77e2046bc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("effective_until", sa.Date(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("indexed_chunk_count", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "chk_documents_indexed_chunk_count",
        "documents",
        "indexed_chunk_count IS NULL OR indexed_chunk_count > 0",
    )
    op.create_check_constraint(
        "chk_documents_effective_window",
        "documents",
        "effective_until IS NULL OR "
        "(effective_from IS NOT NULL AND "
        "effective_until > effective_from)",
    )

    # Preserve the current retrieval behavior for already-indexed records.
    # New documents remain ineligible until an owner activates them.
    op.execute(
        "UPDATE documents "
        "SET effective_from = CAST(uploaded_at AS DATE) "
        "WHERE status = 'INDEXED' AND deleted_at IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint(
        "chk_documents_effective_window",
        "documents",
        type_="check",
    )
    op.drop_constraint(
        "chk_documents_indexed_chunk_count",
        "documents",
        type_="check",
    )
    op.drop_column("documents", "indexed_chunk_count")
    op.drop_column("documents", "effective_until")
    op.drop_column("documents", "effective_from")
