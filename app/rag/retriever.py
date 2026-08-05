from typing import List

from app.core.logger import logger


class Retriever:

    def __init__(
        self,
        vector_store
    ):

        self.collection = vector_store.collection


    def search(
        self,
        query_embedding,
        top_k: int = 5
        threshold=1.0
    ):

        results = self.collection.query(
            query_embeddings=[
                query_embedding.tolist()
            ],
            n_results=top_k
        )


        logger.info(
            f"Retrieved {top_k} documents"
        )


        return results