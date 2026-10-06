from pathlib import Path
from typing import List

from pypdf import PdfReader

from app.core.logger import logger
from app.models.document import Document


class PDFLoader:
    """Read a PDF into page-level documents with lineage metadata."""

    def load(self, pdf_path: str, document_id: str, subject_id: str) -> List[Document]:
        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        if not pdf_file.is_file():
            raise ValueError(f"PDF path is not a file: {pdf_path}")
        if pdf_file.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file: {pdf_path}")

        logger.info("Loading PDF: %s", pdf_file.name)
        reader = PdfReader(pdf_file)
        documents = [
            Document(
                document_id=document_id,
                subject_id=subject_id,
                page=page_number,
                source=pdf_file.name,
                text=page.extract_text() or "",
            )
            for page_number, page in enumerate(reader.pages, start=1)
        ]
        logger.info("Loaded %s pages from %s", len(documents), pdf_file.name)
        return documents
