from typing import List, Dict, Any

from app.core.logger import logger
from app.core import config

class Retriever:
    """
    Thực hiện truy vấn Vector Database và trả về
    dữ liệu đã được chuẩn hóa.
    """

    def __init__(self, vector_store):
        self.collection = vector_store.collection

    def search(
    self,
    query_embedding,
    top_k=config.TOP_K,
    threshold=config.SIMILARITY_THRESHOLD
):
        results = self.collection.query(
            query_embeddings=[
                query_embedding.tolist()
            ],
            n_results=top_k
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        retrieved = []

        for doc, metadata, distance in zip(
            documents,
            metadatas,
            distances
        ):

            # Chỉ lấy kết quả đủ liên quan
            if distance <= threshold:

                retrieved.append(
                    {
                        "document": doc,
                        "metadata": metadata,
                        "distance": distance
                    }
                )

        logger.info(
            f"Retrieved {len(retrieved)} documents"
        )

        return retrieved