"""add subject lifecycle metadata

Revision ID: 0db5de6e26b9
Revises: 1835db288a63
Create Date: 2026-10-17 16:55:56.713562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0db5de6e26b9'
down_revision: Union[str, Sequence[str], None] = '1835db288a63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "subjects",
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="ACTIVE",
            nullable=False,
        ),
    )
    op.add_column(
        "subjects",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "subjects",
        sa.Column(
            "lifecycle_error",
            sa.Text(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "chk_subjects_status",
        "subjects",
        "status IN ("
        "'ACTIVE', "
        "'DELETING', "
        "'DELETED', "
        "'DELETE_FAILED', "
        "'RESTORING', "
        "'RESTORE_FAILED'"
        ")",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "chk_subjects_status",
        "subjects",
        type_="check",
    )

    op.drop_column(
        "subjects",
        "lifecycle_error",
    )
    op.drop_column(
        "subjects",
        "deleted_at",
    )
    op.drop_column(
        "subjects",
        "status",
    )
    # ### end Alembic commands ###
