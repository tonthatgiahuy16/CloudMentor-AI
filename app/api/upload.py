import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.core.database import SessionLocal
from app.repos.document_repository import DocumentRepository
from app.repos.subject_repository import (
    SubjectRepository,
)

from io import BytesIO

from app.rag.loader import read_docx_paragraphs

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}

TXT_CONTENT_TYPES = {
    "text/plain",
}

DOCX_CONTENT_TYPES = {
    (
        "application/vnd.openxmlformats-"
        "officedocument.wordprocessingml."
        "document"
    ),
}

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".docx",
}

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


def get_pdf_service():
    from app.services.pdf_service import PDFService

    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)
        yield PDFService(document_repo)

    finally:
        db.close()


def get_upload_subject_repository():
    db = SessionLocal()

    try:
        yield SubjectRepository(db)
    finally:
        db.close()


def get_upload_dir() -> Path:
    return Path(
        os.getenv(
            "CLOUDMENTOR_UPLOAD_DIR",
            "storage/uploads",
        )
    )


def validate_document_upload(
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

    suffix = Path(original_name).suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                "Only PDF, TXT, and DOCX files "
                "are supported"
            ),
        )

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit",
        )

    if suffix == ".pdf":
        if content_type not in PDF_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Invalid PDF content type",
            )

        if not data.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=415,
                detail="File content is not a PDF",
            )

    if suffix == ".txt":
        if content_type not in TXT_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Invalid TXT content type",
            )

        try:
            decoded_text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=415,
                detail="TXT file is not valid UTF-8",
            ) from exc

        if not decoded_text.strip():
            raise HTTPException(
                status_code=400,
                detail="TXT file is empty",
            )

    if suffix == ".docx":
        if content_type not in DOCX_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Invalid DOCX content type",
            )

        try:
            read_docx_paragraphs(
                BytesIO(data)
            )
        except ValueError as exc:
            detail = str(exc)
            status_code = (
                400
                if detail == "DOCX file is empty"
                else 415
            )

            raise HTTPException(
                status_code=status_code,
                detail=detail,
            ) from exc

    return original_name


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    response: Response,
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    chapter: int | None = Form(None),
    pdf_service=Depends(get_pdf_service),
    upload_dir: Path = Depends(get_upload_dir),
    subject_repo=Depends(
        get_upload_subject_repository
    ),
):
    subject = subject_repo.get_by_id(
        subject_id
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    if subject.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subject is not active",
        )

    data = await file.read(MAX_UPLOAD_BYTES + 1)

    original_name = validate_document_upload(
        file.filename,
        file.content_type,
        data,
    )

    content_sha256 = sha256(data).hexdigest()
    file_size_bytes = len(data)

    existing_document = (
        pdf_service.find_active_duplicate(
            subject_id=subject_id,
            content_sha256=content_sha256,
        )
    )

    if existing_document is not None:
        if existing_document.status == "FAILED":
            try:
                total_chunks = (
                    pdf_service.retry_failed_document(
                        existing_document
                    )
                )

            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail="Document retry failed",
                ) from exc

            response.status_code = (
                status.HTTP_200_OK
            )

            return {
                "document_id": (
                    existing_document.document_id
                ),
                "filename": (
                    existing_document.filename
                ),
                "chunks": total_chunks,
            }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DOCUMENT_ALREADY_EXISTS",
                "document_id": (
                    existing_document.document_id
                ),
                "status": existing_document.status,
            },
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

    source_uri = save_path.as_posix()
    save_path.write_bytes(data)

    try:
        total_chunks = pdf_service.upload(
            str(save_path),
            subject_id=subject_id,
            chapter=chapter,
            document_id=document_id,
            original_filename=original_name,
            source_uri=source_uri,
            content_sha256=content_sha256,
            file_size_bytes=file_size_bytes,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Document processing failed",
        ) from exc

    return {
        "document_id": document_id,
        "filename": original_name,
        "chunks": total_chunks,
    }
