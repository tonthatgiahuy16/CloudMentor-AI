"""enforce active document content uniqueness

Revision ID: bc77e2046bc3
Revises: 0db5de6e26b9
Create Date: 2026-10-20 21:59:25.800762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc77e2046bc3'
down_revision: Union[str, Sequence[str], None] = '0db5de6e26b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_documents_active_subject_content_sha256",
        "documents",
        ["subject_id", "content_sha256"],
        unique=True,
        postgresql_where=sa.text(
            "status != 'DELETED' "
            "AND content_sha256 IS NOT NULL"
        ),
        sqlite_where=sa.text(
            "status != 'DELETED' "
            "AND content_sha256 IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_documents_active_subject_content_sha256",
        table_name="documents",
    )
