from app.rag.vector_store import VectorStore


class IndexPipeline:

    def __init__(self):

        self.vector_store = VectorStore()

    def run(
        self,
        chunks,
        embeddings
    ):

        self.vector_store.add(
            chunks,
            embeddings
        )

        return len(chunks)