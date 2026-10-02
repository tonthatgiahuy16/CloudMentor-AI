from fastapi import APIRouter, Depends, HTTPException

from app.core.database import SessionLocal
from app.rag.vector_store import VectorStore
from app.repos.document_repository import DocumentRepository
from app.services.document_deletion_service import (
    DocumentDeletionService,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def get_document_deletion_service():
    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)
        vector_store = VectorStore()

        yield DocumentDeletionService(
            document_repo=document_repo,
            vector_store=vector_store,
        )

    finally:
        db.close()


@router.delete(
    "/{document_id}",
)
def delete_document(
    document_id: str,
    deletion_service=Depends(get_document_deletion_service),
):
    try:
        return deletion_service.delete(document_id)

    except RuntimeError as exc:
        if str(exc) == "Document not found":
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            ) from exc

        raise HTTPException(
            status_code=500,
            detail="Document deletion failed",
        ) from exc