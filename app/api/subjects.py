from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.api.upload import get_source_storage
from app.core.database import SessionLocal
from app.repos.subject_repository import SubjectRepository
from app.schemas.subject import (
    SubjectCreate,
    SubjectDeletionResponse,
    SubjectResponse,
    SubjectRestoreResponse,
    SubjectTrashResponse,
)


router = APIRouter(
    prefix="/subjects",
    tags=["Subjects"],
)


def get_subject_repository():
    db = SessionLocal()

    try:
        yield SubjectRepository(db)

    finally:
        db.close()


def get_subject_deletion_service():
    from app.rag.vector_store import VectorStore
    from app.repos.document_repository import (
        DocumentRepository,
    )
    from app.services.subject_deletion_service import (
        SubjectDeletionService,
    )

    db = SessionLocal()

    try:
        yield SubjectDeletionService(
            subject_repo=SubjectRepository(db),
            document_repo=DocumentRepository(db),
            vector_store=VectorStore(),
        )
    finally:
        db.close()


def get_subject_restore_service(
    source_storage=Depends(get_source_storage),
):
    from app.repos.document_repository import (
        DocumentRepository,
    )
    from app.services.pdf_service import PDFService
    from app.services.subject_restore_service import (
        SubjectRestoreService,
    )

    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)

        yield SubjectRestoreService(
            subject_repo=SubjectRepository(db),
            document_repo=document_repo,
            pdf_service=PDFService(
                document_repo,
                source_storage=source_storage,
            ),
        )
    finally:
        db.close()


@router.get("/", response_model=list[SubjectResponse])
def list_subjects(
    subject_repo=Depends(get_subject_repository),
):
    subjects = subject_repo.list_active()

    return [
        {
            "subject_id": subject.subject_id,
            "name": subject.name,
        }
        for subject in subjects
    ]


@router.get(
    "/trash",
    response_model=list[SubjectTrashResponse],
)
def list_subject_trash(
    subject_repo=Depends(get_subject_repository),
):
    subjects = subject_repo.list_trash()

    return [
        {
            "subject_id": subject.subject_id,
            "name": subject.name,
            "status": subject.status,
            "deleted_at": subject.deleted_at,
            "lifecycle_error": (
                subject.lifecycle_error
            ),
        }
        for subject in subjects
    ]


@router.post(
    "/",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: SubjectCreate,
    subject_repo=Depends(get_subject_repository),
):
    try:
        subject = subject_repo.create(name=payload.name)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Môn học đã tồn tại",
        ) from exc

    return {
        "subject_id": subject.subject_id,
        "name": subject.name,
    }


@router.delete(
    "/{subject_id}",
    response_model=SubjectDeletionResponse,
)
def delete_subject(
    subject_id: str,
    deletion_service=Depends(
        get_subject_deletion_service
    ),
):
    try:
        return deletion_service.delete(
            subject_id
        )
    except RuntimeError as exc:
        if str(exc) == "Subject not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found",
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Subject deletion failed",
        ) from exc


@router.post(
    "/{subject_id}/restore",
    response_model=SubjectRestoreResponse,
)
def restore_subject(
    subject_id: str,
    restore_service=Depends(
        get_subject_restore_service
    ),
):
    try:
        return restore_service.restore(
            subject_id
        )
    except RuntimeError as exc:
        if str(exc) == "Subject not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subject not found",
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Subject restoration failed",
        ) from exc
