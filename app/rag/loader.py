from pathlib import Path
from typing import List

from pypdf import PdfReader

from app.core.logger import logger
from app.models.document import Document
from app.rag.cleaner import TextCleaner


class PDFLoader:
    """
    Chịu trách nhiệm đọc PDF và chuyển thành List[Document].
    """

    def __init__(self):
        self.cleaner = TextCleaner()


    def load(self, pdf_path: str) -> List[Document]:

        pdf_file = Path(pdf_path)

        if not pdf_file.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {pdf_path}"
            )


        logger.info(
            f"Loading PDF: {pdf_file.name}"
        )


        reader = PdfReader(pdf_file)


        documents = []


        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            text = page.extract_text() or ""


            text = self.cleaner.clean(text)


            documents.append(
                Document(
                    page=page_number,
                    source=pdf_file.name,
                    text=text.strip()
                )
            )


        logger.info(
            f"Loaded {len(documents)} pages from {pdf_file.name}"
        )


        return documents