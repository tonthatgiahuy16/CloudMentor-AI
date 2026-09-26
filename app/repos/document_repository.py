from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db_models.document import Document


class DocumentRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, document_id: str) -> Document | None:
        return (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
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
        document.deleted_at = func.now()

        self.db.commit()
        self.db.refresh(document)

        return document


    def mark_processing(self, document_id: str):
        document = (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )

        if document is None:
            raise RuntimeError("Document not found")
        document.status = "PROCESSING"
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
    ) -> Document:
        document = Document(
            document_id=document_id,
            subject_id=subject_id,
            filename=filename,
            file_type=file_type,
            chapter=chapter,
            status="UPLOADED",
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return document