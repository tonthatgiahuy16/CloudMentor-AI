from typing import List
import uuid

from app.models.document import Document
from app.models.chunk import Chunk


class TextChunker:

    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 150
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(
        self,
        documents: List[Document],
        document_id: str
    ) -> List[Chunk]:

        chunks: List[Chunk] = []

        for document in documents:

            text = document.text

            start = 0

            while start < len(text):

                end = start + self.chunk_size

                chunk_text = text[start:end]

                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_index=len(chunks),
                        page=document.page,
                        source=document.source,
                        text=chunk_text
                    )
                )

                start += self.chunk_size - self.overlap

        return chunks