from app.rag.chunker import TextChunker


class ChunkPipeline:

    def __init__(self):

        self.chunker = TextChunker(
            split_paragraphs=True,
        )

    def run(
        self,
        documents,
    ):

        return self.chunker.split(
            documents,
        )
