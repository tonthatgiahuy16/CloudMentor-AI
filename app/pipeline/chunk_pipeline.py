from app.rag.chunker import TextChunker


class ChunkPipeline:

    def __init__(self):

        self.chunker = TextChunker()

    def run(
        self,
        documents,
        document_id: str
    ):

        return self.chunker.split(
            documents,
            document_id
        )