from app.rag.cleaner import TextCleaner


class TransformPipeline:

    def __init__(self):

        self.cleaner = TextCleaner()

    def run(
        self,
        documents
    ):

        return self.cleaner.clean(
            documents
        )