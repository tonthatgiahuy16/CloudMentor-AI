from app.models.document import Document
from app.rag.cleaner import TextCleaner

class TransformPipeline:

    def __init__(self):

        self.cleaner = TextCleaner()


    def run(
        self,
        documents
    ):

        cleaned_documents = []

        for document in documents:

            cleaned_text = self.cleaner.clean(
                document.text
            )

            cleaned_documents.append(
                Document(
                    page=document.page,
                    source=document.source,
                    text=cleaned_text
                )
            )

        return cleaned_documents