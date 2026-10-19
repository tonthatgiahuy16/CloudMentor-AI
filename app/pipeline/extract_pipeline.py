from app.rag.loader import (
    DOCXLoader,
    PDFLoader,
    TextLoader,
)


class ExtractPipeline:

    def __init__(self):
        self.loaders = {
            "pdf": PDFLoader(),
            "txt": TextLoader(),
            "docx": DOCXLoader(),
        }

    def run(
        self,
        *,
        source_data: bytes,
        filename: str,
        file_type: str,
        document_id: str,
        subject_id: str,
    ):
        normalized_file_type = (
            file_type
            .strip()
            .lower()
            .lstrip(".")
        )

        loader = self.loaders.get(
            normalized_file_type
        )

        if loader is None:
            raise ValueError(
                "Unsupported document type: "
                f".{normalized_file_type}"
            )

        return loader.load(
            source_data,
            filename=filename,
            document_id=document_id,
            subject_id=subject_id,
        )
