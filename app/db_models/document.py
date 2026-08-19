from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )

    subject_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("subjects.subject_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    chapter: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    uploaded_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    indexed_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    deleted_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="UPLOADED",
    )

    failed_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "file_type IN ('pdf', 'txt', 'docx')",
            name="chk_documents_file_type",
        ),
        CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'INDEXED', 'FAILED', 'DELETED')",
            name="chk_documents_status",
        ),
        CheckConstraint(
            "failed_stage IS NULL OR failed_stage IN "
            "('EXTRACT', 'TRANSFORM', 'CHUNK', 'EMBEDDING', 'INDEX')",
            name="chk_documents_failed_stage",
        ),
    )