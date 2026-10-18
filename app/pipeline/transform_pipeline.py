from app.models.document import Document
from app.rag.cleaner import TextCleaner


class TransformPipeline:
    def __init__(self):
        self.cleaner = TextCleaner()

    def run(
        self,
        documents,
    ):
        cleaned_documents = []

        for document in documents:
            preserve_line_breaks = (
                document.line_range is not None
                or document.paragraph_range
                is not None
            )

            cleaned_text = self.cleaner.clean(
                document.text,
                preserve_line_breaks=(
                    preserve_line_breaks
                ),
            )

            cleaned_documents.append(
                Document(
                    document_id=(
                        document.document_id
                    ),
                    subject_id=(
                        document.subject_id
                    ),
                    source=document.source,
                    text=cleaned_text,
                    page=document.page,
                    line_range=(
                        document.line_range
                    ),
                    paragraph_range=(
                        document.paragraph_range
                    ),
                )
            )

        return cleaned_documents
