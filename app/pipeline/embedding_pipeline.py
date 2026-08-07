from app.rag.embedder import EmbeddingService


class EmbeddingPipeline:

    def __init__(self):

        self.embedder = EmbeddingService()

    def run(
        self,
        chunks
    ):

        return self.embedder.embed(
            chunks
        )