from typing import List
import uuid

from app.models.chunk import Chunk
from app.models.document import Document


class TextChunker:
    def __init__(self, chunk_size: int = 800, overlap: int = 150):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0:
            raise ValueError("overlap must not be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, documents: List[Document]) -> List[Chunk]:
        chunks: List[Chunk] = []
        step = self.chunk_size - self.overlap

        for document in documents:
            start = 0
            chunk_index = 0

            while start < len(document.text):
                end = start + self.chunk_size
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document.document_id,
                        chunk_index=chunk_index,
                        page=document.page,
                        source=document.source,
                        text=document.text[start:end],
                    )
                )
                if end >= len(document.text):
                    break
                start += step
                chunk_index += 1

        return chunks
