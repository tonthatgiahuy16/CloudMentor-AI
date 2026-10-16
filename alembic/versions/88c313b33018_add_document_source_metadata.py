"""add document source metadata

Revision ID: 88c313b33018
Revises: 9d22d3ffc4d8
Create Date: 2026-10-17 00:13:36.890435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88c313b33018'
down_revision: Union[str, Sequence[str], None] = '9d22d3ffc4d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "documents",
        sa.Column(
            "source_uri",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "content_sha256",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_documents_content_sha256"),
        "documents",
        ["content_sha256"],
        unique=False,
    )

    op.create_check_constraint(
        "chk_documents_content_sha256_length",
        "documents",
        "content_sha256 IS NULL OR "
        "length(content_sha256) = 64",
    )

    op.create_check_constraint(
        "chk_documents_file_size_bytes",
        "documents",
        "file_size_bytes IS NULL OR "
        "file_size_bytes >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_documents_content_sha256"),
        table_name="documents",
    )

    op.drop_constraint(
        "chk_documents_file_size_bytes",
        "documents",
        type_="check",
    )

    op.drop_constraint(
        "chk_documents_content_sha256_length",
        "documents",
        type_="check",
    )

    op.drop_column(
        "documents",
        "file_size_bytes",
    )

    op.drop_column(
        "documents",
        "content_sha256",
    )

    op.drop_column(
        "documents",
        "source_uri",
    )
