from app.rag.loader import PDFLoader


class ExtractPipeline:

    def __init__(self):

        self.loader = PDFLoader()

    def run(
        self,
        file_path,
        document_id,
        subject_id,
    ):

        return self.loader.load(
            file_path,
            document_id,
            subject_id,
        )
        
        