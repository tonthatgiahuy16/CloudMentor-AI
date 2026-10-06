from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.repos.subject_repository import SubjectRepository
from app.schemas.subject import SubjectCreate, SubjectResponse


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


@router.get("/", response_model=list[SubjectResponse])
def list_subjects(
    subject_repo=Depends(get_subject_repository),
):
    subjects = subject_repo.list_all()

    return [
        {
            "subject_id": subject.subject_id,
            "name": subject.name,
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
