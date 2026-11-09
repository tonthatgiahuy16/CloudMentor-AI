from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.core.date_utils import get_current_business_date
from app.core.demo_mode import require_mutations_enabled
from app.repos.document_repository import DocumentRepository
from app.services.document_deletion_service import (
    DocumentDeletionService,
)
from app.schemas.document_version import (
    PolicyVersionActivationRequest,
)
from app.services.policy_version_service import (
    PolicyVersionService,
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


def get_policy_version_service():
    from app.rag.vector_store import VectorStore

    db = SessionLocal()
    try:
        yield PolicyVersionService(
            document_repo=DocumentRepository(db),
            vector_store=VectorStore(),
        )
    finally:
        db.close()


def serialize_document(document) -> dict:
    effective_from = getattr(document, "effective_from", None)
    effective_until = getattr(document, "effective_until", None)
    today = get_current_business_date()
    is_current = (
        document.status == "INDEXED"
        and effective_from is not None
        and effective_from <= today
        and (
            effective_until is None
            or effective_until > today
        )
    )
    return {
        "document_id": document.document_id,
        "subject_id": document.subject_id,
        "filename": document.filename,
        "file_type": document.file_type,
        "chapter": document.chapter,
        "status": document.status,
        "uploaded_at": document.uploaded_at,
        "indexed_at": document.indexed_at,
        "effective_from": effective_from,
        "effective_until": effective_until,
        "effective_date": effective_from,
        "is_current": is_current,
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
    document = (
        document_repo.get_visible_by_id(
            document_id
            )
    )

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
    _=Depends(require_mutations_enabled),
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


@router.post("/{document_id}/activate")
def activate_policy_version(
    document_id: str,
    payload: PolicyVersionActivationRequest,
    _=Depends(require_mutations_enabled),
    version_service=Depends(get_policy_version_service),
):
    try:
        document = version_service.activate(
            document_id=document_id,
            effective_from=payload.effective_from,
            supersedes_document_id=(
                payload.supersedes_document_id
            ),
        )
    except RuntimeError as exc:
        message = str(exc)
        if message in {
            "Document not found",
            "Superseded document not found",
        }:
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc
        raise HTTPException(
            status_code=409,
            detail=message,
        ) from exc

    return serialize_document(document)
