from fastapi import APIRouter, Depends

from app.core.database import SessionLocal
from app.repos.subject_repository import SubjectRepository


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


@router.get("/")
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