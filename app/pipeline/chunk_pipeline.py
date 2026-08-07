from app.rag.chunker import TextChunker


class ChunkPipeline:

    def __init__(self):

        self.chunker = TextChunker()

    def run(
        self,
        documents
    ):

        return self.chunker.chunk(
            documents
        )