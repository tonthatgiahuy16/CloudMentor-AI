from datetime import date

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    DateTime,
    Date,
    ForeignKey,
    CheckConstraint,
    Text,
    Index,
    text,
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

    source_uri: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    processing_attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    last_processing_started_at: Mapped[
        object | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_processing_heartbeat_at: Mapped[
        object | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    current_stage: Mapped[str | None] = mapped_column(
        String(50),
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

    # A NULL effective_from means this indexed document has not been
    # explicitly activated as a policy version.
    effective_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Exclusive end date: the version is not applicable on this date.
    effective_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    indexed_chunk_count: Mapped[int | None] = mapped_column(
        Integer,
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
            "processing_attempt_count >= 0",
            name=(
                "chk_documents_"
                "processing_attempt_count"
            ),
        ),

        CheckConstraint(
            "current_stage IS NULL OR current_stage IN "
            "('EXTRACT', 'TRANSFORM', 'CHUNK', "
            "'EMBEDDING', 'INDEX')",
            name="chk_documents_current_stage",
        ),

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

        CheckConstraint(
            "content_sha256 IS NULL OR "
            "length(content_sha256) = 64",
            name="chk_documents_content_sha256_length",
        ),

        CheckConstraint(
            "file_size_bytes IS NULL OR "
            "file_size_bytes >= 0",
            name="chk_documents_file_size_bytes",
        ),

        CheckConstraint(
            "indexed_chunk_count IS NULL OR indexed_chunk_count > 0",
            name="chk_documents_indexed_chunk_count",
        ),

        CheckConstraint(
            "effective_until IS NULL OR "
            "(effective_from IS NOT NULL AND "
            "effective_until > effective_from)",
            name="chk_documents_effective_window",
        ),

        Index(
                    "uq_documents_active_subject_content_sha256",
                    "subject_id",
                    "content_sha256",
                    unique=True,
                    postgresql_where=text(
                        "status != 'DELETED' "
                        "AND content_sha256 IS NOT NULL"
                    ),
                    sqlite_where=text(
                        "status != 'DELETED' "
                        "AND content_sha256 IS NOT NULL"
                    ),
                ),
    )
