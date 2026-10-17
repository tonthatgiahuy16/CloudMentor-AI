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


    def delete_by_document_id(
        self,
        document_id: str,
    ) -> int:
        return (
            self.vector_store
            .delete_by_document_id(document_id)
        )
