from pathlib import Path

from app.rag.loader import (
    DOCXLoader,
    PDFLoader,
    TextLoader,
)


class ExtractPipeline:

    def __init__(self):
        self.loaders = {
            ".pdf": PDFLoader(),
            ".txt": TextLoader(),
            ".docx": DOCXLoader(),
        }

    def run(
        self,
        file_path,
        document_id,
        subject_id,
    ):
        suffix = Path(file_path).suffix.lower()
        loader = self.loaders.get(suffix)

        if loader is None:
            raise ValueError(
                f"Unsupported document type: {suffix}"
            )

        return loader.load(
            file_path,
            document_id,
            subject_id,
        )
