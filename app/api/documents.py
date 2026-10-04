from fastapi import APIRouter, Depends, HTTPException

from app.core.database import SessionLocal
from app.repos.document_repository import DocumentRepository
from app.services.document_deletion_service import (
    DocumentDeletionService,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def get_document_deletion_service():
    from app.rag.vector_store import VectorStore
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


def get_document_repository():
    db = SessionLocal()

    try:
        yield DocumentRepository(db)

    finally:
        db.close()


def serialize_document(document) -> dict:
    return {
        "document_id": document.document_id,
        "subject_id": document.subject_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "chapter": document.chapter,
        "status": document.status,
        "uploaded_at": document.uploaded_at,
        "indexed_at": document.indexed_at,
    }

@router.get(
    "/",
)
def list_documents(
    document_repo=Depends(get_document_repository),
):
    documents = document_repo.list_active()

    return [
        serialize_document(document)
        for document in documents
    ]



@router.get(
    "/{document_id}",
)
def get_document(
    document_id: str,
    document_repo=Depends(get_document_repository),
):
    document = document_repo.get_by_id(document_id)

    if (
        document is None
        or document.status == "DELETED"
    ):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return serialize_document(document)



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