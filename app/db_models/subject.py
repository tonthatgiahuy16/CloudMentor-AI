from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="ACTIVE",
    )

    deleted_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lifecycle_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'ACTIVE', "
            "'DELETING', "
            "'DELETED', "
            "'DELETE_FAILED', "
            "'RESTORING', "
            "'RESTORE_FAILED'"
            ")",
            name="chk_subjects_status",
        ),
    )