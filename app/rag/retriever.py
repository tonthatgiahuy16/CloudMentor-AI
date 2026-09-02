from typing import Any

from app.core import config
from app.core.logger import logger


class Retriever:
    """Query a vector collection and normalize traceable retrieval results."""

    def __init__(self, vector_store: Any):
        self.collection = vector_store.collection

    def search(
        self,
        query_embedding: Any,
        top_k: int = config.TOP_K,
        threshold: float = config.SIMILARITY_THRESHOLD,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        embedding = (
            query_embedding.tolist()
            if hasattr(query_embedding, "tolist")
            else list(query_embedding)
        )
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )
        groups = (
            results.get("ids", []),
            results.get("documents", []),
            results.get("metadatas", []),
            results.get("distances", []),
        )
        if not all(groups) or not all(group[0] for group in groups):
            return []

        retrieved = []
        for chunk_id, document, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if distance <= threshold:
                retrieved.append(
                    {
                        "chunk_id": chunk_id,
                        "document": document,
                        "metadata": metadata,
                        "distance": distance,
                    }
                )

        logger.info("Retrieved %s documents", len(retrieved))
        return retrieved
