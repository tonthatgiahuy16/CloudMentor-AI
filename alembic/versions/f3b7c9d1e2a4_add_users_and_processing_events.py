"""add users and document processing events

Revision ID: f3b7c9d1e2a4
Revises: c4f1a9b2d7e5
Create Date: 2026-11-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3b7c9d1e2a4"
down_revision: Union[str, Sequence[str], None] = "c4f1a9b2d7e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="employee",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'employee')",
            name="chk_users_role",
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("employee_id"),
    )
    op.create_index(
        op.f("ix_users_employee_id"),
        "users",
        ["employee_id"],
        unique=True,
    )

    op.create_table(
        "document_processing_events",
        sa.Column(
            "event_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "stage",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "error_code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "stage IN ('EXTRACT', 'TRANSFORM', 'CHUNK', "
            "'EMBEDDING', 'INDEX')",
            name="chk_processing_events_stage",
        ),
        sa.CheckConstraint(
            "status IN ('SUCCEEDED', 'FAILED')",
            name="chk_processing_events_status",
        ),
        sa.CheckConstraint(
            "duration_ms >= 0",
            name="chk_processing_events_duration",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.document_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        op.f("ix_document_processing_events_document_id"),
        "document_processing_events",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_processing_events_occurred_at"),
        "document_processing_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_processing_events_stage_occurred_at",
        "document_processing_events",
        ["stage", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_processing_events_stage_occurred_at",
        table_name="document_processing_events",
    )
    op.drop_index(
        op.f("ix_document_processing_events_occurred_at"),
        table_name="document_processing_events",
    )
    op.drop_index(
        op.f("ix_document_processing_events_document_id"),
        table_name="document_processing_events",
    )
    op.drop_table("document_processing_events")
    op.drop_index(
        op.f("ix_users_employee_id"),
        table_name="users",
    )
    op.drop_table("users")
