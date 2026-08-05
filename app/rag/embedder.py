from typing import List

from sentence_transformers import SentenceTransformer

from app.models.chunk import Chunk
from app.core.logger import logger


class EmbeddingService:

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3"
    ):

        self.model = SentenceTransformer(model_name)

        logger.info(
            f"Loaded embedding model: {model_name}"
        )


    def embed(
        self,
        chunks: List[Chunk]
    ):

        texts = [
            chunk.text
            for chunk in chunks
        ]

        vectors = self.model.encode(
            texts,
            show_progress_bar=True
        )

        logger.info(
            f"Generated {len(vectors)} embeddings"
        )

        return vectors