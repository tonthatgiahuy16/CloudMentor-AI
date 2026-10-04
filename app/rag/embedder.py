from typing import List

import numpy as np
import torch
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer

from app.core import config
from app.core.logger import logger
from app.models.chunk import Chunk


class EmbeddingService:
    def __init__(
        self,
        model_name: str = config.EMBEDDING_MODEL,
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name
        )
        self.model = AutoModel.from_pretrained(
            model_name
        )
        self.model.eval()

        self.max_length = min(
            self.tokenizer.model_max_length,
            8192,
        )

        logger.info(
            f"Loaded embedding model: {model_name}"
        )

    def _encode(
        self,
        texts: list[str],
    ) -> np.ndarray:
        if not texts:
            return np.empty(
                (
                    0,
                    self.model.config.hidden_size,
                ),
                dtype=np.float32,
            )

        batches = []
        batch_size = 4

        for start in range(
            0,
            len(texts),
            batch_size,
        ):
            batch = texts[
                start:start + batch_size
            ]

            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )

            with torch.inference_mode():
                output = self.model(**inputs)

                vectors = (
                    output
                    .last_hidden_state[:, 0]
                )

                vectors = functional.normalize(
                    vectors,
                    p=2,
                    dim=1,
                )

            batches.append(
                vectors.cpu()
            )

        return (
            torch.cat(batches)
            .numpy()
        )

    def embed(
        self,
        chunks: List[Chunk],
    ) -> np.ndarray:
        texts = [
            chunk.text
            for chunk in chunks
        ]

        vectors = self._encode(texts)

        logger.info(
            f"Generated {len(vectors)} embeddings"
        )

        return vectors

    def embed_query(
        self,
        query: str,
    ) -> np.ndarray:
        return self._encode([query])[0]