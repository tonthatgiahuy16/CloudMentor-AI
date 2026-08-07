from pathlib import Path
import shutil

from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

from app.services.pdf_service import PDFService


router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

pdf_service = PDFService()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/")
def upload_pdf(
    file: UploadFile = File(...)
):

    save_path = UPLOAD_DIR / file.filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    total_chunks = pdf_service.upload(
        str(save_path)
    )

    return {
        "message": "Upload thành công",
        "chunks": total_chunks
    }