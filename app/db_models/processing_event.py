from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


PROCESSING_STAGES = (
    "EXTRACT",
    "TRANSFORM",
    "CHUNK",
    "EMBEDDING",
    "INDEX",
)

PROCESSING_EVENT_STATUSES = ("SUCCEEDED", "FAILED")


class ProcessingEvent(Base):
    """One observed pipeline-stage run for a document.

    PostgreSQL remains the system of record: these events make stage
    duration and failure history queryable instead of only keeping the
    latest document state. Log lines stay useful for debugging, but
    metrics are aggregated from this table.
    """

    __tablename__ = "document_processing_events"

    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey(
            "documents.document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    occurred_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "stage IN ('EXTRACT', 'TRANSFORM', 'CHUNK', "
            "'EMBEDDING', 'INDEX')",
            name="chk_processing_events_stage",
        ),
        CheckConstraint(
            "status IN ('SUCCEEDED', 'FAILED')",
            name="chk_processing_events_status",
        ),
        CheckConstraint(
            "duration_ms >= 0",
            name="chk_processing_events_duration",
        ),
        Index(
            "ix_processing_events_stage_occurred_at",
            "stage",
            "occurred_at",
        ),
    )
