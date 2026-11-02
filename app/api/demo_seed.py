from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core import config
from app.core.database import SessionLocal
from app.repos.document_repository import DocumentRepository
from app.repos.subject_repository import SubjectRepository
from app.services.demo_seed_service import DemoSeedService
from app.storage.source_storage_factory import create_source_storage

router = APIRouter(prefix="/internal", tags=["Internal"])


def require_demo_seed_token(
    x_demo_seed_token: str | None = Header(default=None),
) -> None:
    if (
        not config.DEMO_MODE
        or not config.DEMO_SEED_TOKEN
        or x_demo_seed_token is None
        or not compare_digest(x_demo_seed_token, config.DEMO_SEED_TOKEN)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def get_demo_seed_service():
    from app.services.pdf_service import PDFService
    db = SessionLocal()
    try:
        yield DemoSeedService(
            subject_repo=SubjectRepository(db),
            pdf_service=PDFService(DocumentRepository(db), source_storage=create_source_storage()),
            seed_dir=config.DEMO_SEED_DIR,
        )
    finally:
        db.close()


@router.post("/demo-seed")
def seed_demo(
    _=Depends(require_demo_seed_token),
    service=Depends(get_demo_seed_service),
):
    return service.seed()
