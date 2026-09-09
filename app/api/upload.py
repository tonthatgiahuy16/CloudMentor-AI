import os
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.core.database import SessionLocal
from app.repos.document_repository import DocumentRepository
from app.services.pdf_service import PDFService


MAX_UPLOAD_BYTES = 10 * 1024 * 1024

PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


def get_pdf_service():
    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)
        yield PDFService(document_repo)

    finally:
        db.close()


def get_upload_dir() -> Path:
    return Path(
        os.getenv(
            "CLOUDMENTOR_UPLOAD_DIR",
            "storage/uploads",
        )
    )


def validate_pdf_upload(
    filename: str | None,
    content_type: str | None,
    data: bytes,
) -> str:
    original_name = (filename or "").strip()

    if not original_name:
        raise HTTPException(
            status_code=400,
            detail="A filename is required",
        )

    if (
        Path(original_name).name != original_name
        or "\\" in original_name
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    if Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are supported",
        )

    if content_type not in PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Invalid PDF content type",
        )

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the 10 MB limit",
        )

    if not data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=415,
            detail="File content is not a PDF",
        )

    return original_name


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    chapter: int | None = Form(None),
    pdf_service=Depends(get_pdf_service),
    upload_dir: Path = Depends(get_upload_dir),
):
    data = await file.read(MAX_UPLOAD_BYTES + 1)

    original_name = validate_pdf_upload(
        file.filename,
        file.content_type,
        data,
    )

    document_id = str(uuid4())

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_path = (
        upload_dir
        / f"{document_id}_{original_name}"
    )

    save_path.write_bytes(data)

    try:
        total_chunks = pdf_service.upload(
            str(save_path),
            subject_id=subject_id,
            chapter=chapter,
            document_id=document_id,
        )

    except Exception as exc:
        save_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="PDF processing failed",
        ) from exc

    return {
        "document_id": document_id,
        "filename": original_name,
        "chunks": total_chunks,
    }