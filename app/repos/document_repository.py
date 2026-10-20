from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.db_models.document import Document
from app.db_models.subject import Subject

PROCESSING_STAGES = {
    "EXTRACT",
    "TRANSFORM",
    "CHUNK",
    "EMBEDDING",
    "INDEX",
}

@dataclass(frozen=True)
class DocumentReconciliationRecord:
    document_id: str
    subject_id: str
    document_status: str
    subject_status: str


class DocumentRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, document_id: str) -> Document | None:
        return (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

    def attach_source_metadata(
        self,
        *,
        document_id: str,
        source_uri: str,
        content_sha256: str,
        file_size_bytes: int,
    ) -> Document:
        document = self.get_by_id(document_id)

        if document is None:
            raise RuntimeError("Document not found")

        current_metadata = (
            document.source_uri,
            document.content_sha256,
            document.file_size_bytes,
        )
        requested_metadata = (
            source_uri,
            content_sha256,
            file_size_bytes,
        )

        if any(
            value is not None
            for value in current_metadata
        ):
            if current_metadata == requested_metadata:
                return document

            raise RuntimeError(
                "Document source metadata conflict"
            )


        document.source_uri = source_uri
        document.content_sha256 = content_sha256
        document.file_size_bytes = file_size_bytes

        self.db.commit()
        self.db.refresh(document)

        return document

    def replace_source_uri_if_matches(
        self,
        *,
        document_id: str,
        expected_source_uri: str,
        expected_content_sha256: str,
        expected_file_size_bytes: int,
        new_source_uri: str,
    ) -> Document:
        try:
            updated_rows = (
                self.db.query(Document)
                .filter(
                    Document.document_id
                    == document_id,
                    Document.source_uri
                    == expected_source_uri,
                    Document.content_sha256
                    == expected_content_sha256,
                    Document.file_size_bytes
                    == expected_file_size_bytes,
                )
                .update(
                    {
                        Document.source_uri: (
                            new_source_uri
                        ),
                    },
                    synchronize_session=False,
                )
            )

            if updated_rows != 1:
                raise RuntimeError(
                    "Document source changed "
                    "during migration"
                )

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        document = self.get_by_id(document_id)

        if document is None:
            raise RuntimeError("Document not found")

        self.db.refresh(document)

        return document

    def get_visible_by_id(
        self,
        document_id: str,
    ) -> Document | None:
        return (
            self.db.query(Document)
            .join(
                Subject,
                Subject.subject_id
                == Document.subject_id,
            )
            .filter(
                Document.document_id
                == document_id,
                Document.status != "DELETED",
                Subject.status == "ACTIVE",
            )
            .first()
        )


    def get_active_by_subject_and_sha256(
        self,
        subject_id: str,
        content_sha256: str,
    ) -> Document | None:
        return (
            self.db.query(Document)
            .filter(
                Document.subject_id == subject_id,
                Document.content_sha256
                == content_sha256,
                Document.status != "DELETED",
            )
            .order_by(
                Document.uploaded_at.desc()
            )
            .first()
        )


    def list_all(self) -> list[Document]:
        return (
            self.db.query(Document)
            .order_by(
                Document.document_id.asc()
            )
            .all()
        )


    def list_active(self) -> list[Document]:
        return (
            self.db.query(Document)
            .join(
                Subject,
                Subject.subject_id
                == Document.subject_id,
            )
            .filter(
                Document.status != "DELETED",
                Subject.status == "ACTIVE",
            )
            .order_by(
                Document.uploaded_at.desc()
            )
            .all()
        )

    def list_indexed_for_active_subjects(
        self,
    ) -> list[Document]:
        return (
            self.db.query(Document)
            .join(
                Subject,
                Subject.subject_id
                == Document.subject_id,
            )
            .filter(
                Document.status == "INDEXED",
                Subject.status == "ACTIVE",
            )
            .order_by(
                Document.document_id.asc()
            )
            .all()
        )

    def list_reconciliation_records(
        self,
    ) -> list[DocumentReconciliationRecord]:
        rows = (
            self.db.query(
                Document.document_id,
                Document.subject_id,
                Document.status.label(
                    "document_status"
                ),
                Subject.status.label(
                    "subject_status"
                ),
            )
            .join(
                Subject,
                Subject.subject_id
                == Document.subject_id,
            )
            .order_by(
                Document.document_id.asc()
            )
            .all()
        )

        return [
            DocumentReconciliationRecord(
                document_id=row.document_id,
                subject_id=row.subject_id,
                document_status=(
                    row.document_status
                ),
                subject_status=(
                    row.subject_status
                ),
            )
            for row in rows
        ]


    def list_active_by_subject(
        self,
        subject_id: str,
    ) -> list[Document]:
        return (
            self.db.query(Document)
            .filter(
                Document.subject_id == subject_id,
                Document.status != "DELETED",
            )
            .order_by(
                Document.uploaded_at.desc()
            )
            .all()
        )


    def list_stale_ingestions(
        self,
        stale_before: datetime,
    ) -> list[Document]:
        return (
            self.db.query(Document)
            .filter(
                or_(
                    and_(
                        Document.status == "UPLOADED",
                        Document.uploaded_at
                        <= stale_before,
                    ),
                    and_(
                        Document.status == "PROCESSING",
                        func.coalesce(
                            Document
                            .last_processing_heartbeat_at,
                            Document
                            .last_processing_started_at,
                            Document.uploaded_at,
                        ) <= stale_before,
                    ),
                )
            )
            .order_by(
                func.coalesce(
                    Document
                    .last_processing_heartbeat_at,
                    Document
                    .last_processing_started_at,
                    Document.uploaded_at,
                ).asc()
            )
            .all()
        )


    def mark_deleted(
        self,
        document_id: str,
    ) -> Document:
        document = self.get_by_id(document_id)

        if document is None:
            raise RuntimeError("Document not found")

        if document.status == "DELETED":
            return document

        document.status = "DELETED"
        document.current_stage = None
        document.deleted_at = func.now()

        self.db.commit()
        self.db.refresh(document)

        return document


    def mark_processing(
        self,
        document_id: str,
    ) -> Document:
        document = self.get_by_id(document_id)

        if document is None:
            raise RuntimeError("Document not found")

        document.status = "PROCESSING"
        document.processing_attempt_count = (
            document.processing_attempt_count or 0
        ) + 1
        document.last_processing_started_at = (
            func.now()
        )
        document.last_processing_heartbeat_at = (
            func.now()
        )

        document.current_stage = None
        document.failed_stage = None
        document.error_message = None

        self.db.commit()
        self.db.refresh(document)

        return document


    def record_processing_heartbeat(
        self,
        document_id: str,
        stage: str,
    ) -> Document:
        if stage not in PROCESSING_STAGES:
            raise ValueError(
                "Invalid processing stage"
            )

        document = self.get_by_id(document_id)

        if document is None:
            raise RuntimeError(
                "Document not found"
            )

        if document.status != "PROCESSING":
            raise RuntimeError(
                "Document is not processing"
            )

        document.current_stage = stage
        document.last_processing_heartbeat_at = (
            func.now()
        )

        self.db.commit()
        self.db.refresh(document)

        return document


    def mark_indexed(self, document_id: str):
        document = (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        if document is None:
            raise RuntimeError("Document not found")

        document.status = "INDEXED"
        document.current_stage = None
        document.failed_stage = None
        document.error_message = None
        document.indexed_at = func.now()

        self.db.commit()
        self.db.refresh(document)
        return document


    def mark_failed(
            self,
            document_id: str,
            failed_stage: str,
            error_message: str
    ):
        document = (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        if document is None:
            raise RuntimeError("Document not found")

        document.status = "FAILED"
        document.current_stage = None
        document.failed_stage = failed_stage
        document.error_message = error_message

        self.db.commit()
        self.db.refresh(document)

        return document


    def create(
        self,
        document_id: str,
        subject_id: str,
        filename: str,
        file_type: str,
        chapter: int | None,
        source_uri: str | None = None,
        content_sha256: str | None = None,
        file_size_bytes: int | None = None,
    ) -> Document:
        document = Document(
            document_id=document_id,
            subject_id=subject_id,
            filename=filename,
            file_type=file_type,
            chapter=chapter,
            status="UPLOADED",
            source_uri=source_uri,
            content_sha256=content_sha256,
            file_size_bytes=file_size_bytes,
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return document
