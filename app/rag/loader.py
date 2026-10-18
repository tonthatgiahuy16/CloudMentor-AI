from pathlib import Path
from typing import List

from pypdf import PdfReader

from app.core.logger import logger
from app.models.document import Document
from docx import Document as WordDocument
from zipfile import BadZipFile

from docx.opc.exceptions import (
    PackageNotFoundError,
)

def normalize_docx_paragraph_text(
    text: str,
) -> str:
    return (
        text
        .replace("\r\n", " ")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def read_docx_paragraphs(source) -> list[str]:
    try:
        word_document = WordDocument(source)
    except (
        BadZipFile,
        PackageNotFoundError,
    ) as exc:
        raise ValueError(
            "DOCX file is not valid"
        ) from exc

    if any(
        cell.text.strip()
        for table in word_document.tables
        for row in table.rows
        for cell in row.cells
    ):
        raise ValueError(
            "DOCX tables are not supported"
        )

    paragraphs = [
        normalize_docx_paragraph_text(
        paragraph.text
        )
        for paragraph in word_document.paragraphs
    ]

    if not paragraphs or not any(
        paragraph.strip()
        for paragraph in paragraphs
    ):
        raise ValueError(
            "DOCX file is empty"
        )

    return paragraphs


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


class TextLoader:
    """Read a UTF-8 TXT file with line-level lineage."""

    def load(
        self,
        txt_path: str,
        document_id: str,
        subject_id: str,
    ) -> List[Document]:
        txt_file = Path(txt_path)

        if not txt_file.exists():
            raise FileNotFoundError(
                f"TXT file not found: {txt_path}"
            )
        if not txt_file.is_file():
            raise ValueError(
                f"TXT path is not a file: {txt_path}"
            )
        if txt_file.suffix.lower() != ".txt":
            raise ValueError(
                f"Expected a TXT file: {txt_path}"
            )

        logger.info("Loading TXT: %s", txt_file.name)

        try:
            text = txt_file.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"TXT file is not valid UTF-8: {txt_path}"
            ) from exc

        lines = text.splitlines()

        if not lines or not any(
            line.strip() for line in lines
        ):
            raise ValueError(
                f"TXT file is empty: {txt_path}"
            )

        normalized_text = "\n".join(lines)

        document = Document(
            document_id=document_id,
            subject_id=subject_id,
            source=txt_file.name,
            text=normalized_text,
            line_range=(1, len(lines)),
        )

        logger.info(
            "Loaded %s lines from %s",
            len(lines),
            txt_file.name,
        )
        return [document]


class DOCXLoader:
    """Read DOCX body paragraphs with exact lineage."""

    def load(
        self,
        docx_path: str,
        document_id: str,
        subject_id: str,
    ) -> List[Document]:
        docx_file = Path(docx_path)

        if not docx_file.exists():
            raise FileNotFoundError(
                f"DOCX file not found: {docx_path}"
            )
        if not docx_file.is_file():
            raise ValueError(
                f"DOCX path is not a file: {docx_path}"
            )
        if docx_file.suffix.lower() != ".docx":
            raise ValueError(
                f"Expected a DOCX file: {docx_path}"
            )

        logger.info(
            "Loading DOCX: %s",
            docx_file.name,
        )

        paragraphs = read_docx_paragraphs(
            docx_file
        )

        document = Document(
            document_id=document_id,
            subject_id=subject_id,
            source=docx_file.name,
            text="\n".join(paragraphs),
            paragraph_range=(
                1,
                len(paragraphs),
            ),
        )

        logger.info(
            "Loaded %s paragraphs from %s",
            len(paragraphs),
            docx_file.name,
        )
        return [document]
