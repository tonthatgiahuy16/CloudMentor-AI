from hashlib import sha256
import json
from typing import List
import uuid

from app.models.chunk import Chunk
from app.models.document import Document

CHUNK_ID_SCHEMA_VERSION = "v1"


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

    def _build_chunk_id(
        self,
        *,
        document: Document,
        chunk_index: int,
        chunk_text: str,
        line_range: tuple[int, int] | None,
        paragraph_range: tuple[int, int] | None,
    ) -> str:
        payload = {
            "schema_version": CHUNK_ID_SCHEMA_VERSION,
            "document_id": document.document_id,
            "chunk_index": chunk_index,
            "source": document.source,
            "page": document.page,
            "line_range": (
                list(line_range)
                if line_range is not None
                else None
            ),
            "paragraph_range": (
                list(paragraph_range)
                if paragraph_range is not None
                else None
            ),
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "text_sha256": sha256(
                chunk_text.encode("utf-8")
            ).hexdigest(),
        }

        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                canonical_payload,
            )
        )

    @staticmethod
    def _source_range_for_slice(
        *,
        text: str,
        source_range: tuple[int, int],
        start: int,
        end: int,
    ) -> tuple[int, int]:
        base_start, declared_end = (
            source_range
        )

        start_offset = text.count(
            "\n",
            0,
            start,
        )

        last_character_index = end - 1
        end_offset = text.count(
            "\n",
            0,
            last_character_index,
        )

        calculated_range = (
            base_start + start_offset,
            base_start + end_offset,
        )

        if calculated_range[1] > declared_end:
            raise ValueError(
                "Source range does not match "
                "text boundaries"
            )

        return calculated_range


    @staticmethod
    def _validate_text_boundaries(
        document: Document,
    ) -> None:
        source_range = (
            document.line_range
            if document.line_range is not None
            else document.paragraph_range
        )

        if source_range is None:
            return

        declared_start, declared_end = (
            source_range
        )
        expected_unit_count = (
            declared_end
            - declared_start
            + 1
        )
        actual_unit_count = (
            document.text.count("\n")
            + 1
        )

        if (
            actual_unit_count
            != expected_unit_count
        ):
            raise ValueError(
                "Source range does not match "
                "text boundaries"
            )


    def split(self, documents: List[Document]) -> List[Chunk]:
        chunks: List[Chunk] = []
        step = self.chunk_size - self.overlap

        for document in documents:
            self._validate_text_boundaries(
                document
            )

            start = 0
            chunk_index = 0

            while start < len(document.text):
                end = min(
                    start + self.chunk_size,
                    len(document.text),
                )

                line_range = None
                paragraph_range = None

                if document.line_range is not None:
                    line_range = (
                        self._source_range_for_slice(
                            text=document.text,
                            source_range=(
                                document.line_range
                            ),
                            start=start,
                            end=end,
                        )
                    )

                elif (
                    document.paragraph_range
                    is not None
                ):
                    paragraph_range = (
                        self._source_range_for_slice(
                            text=document.text,
                            source_range=(
                                document.paragraph_range
                            ),
                            start=start,
                            end=end,
                        )
                    )

                chunk_text = document.text[start:end]

                chunks.append(
                    Chunk(
                        subject_id=(
                            document.subject_id
                        ),
                        id=self._build_chunk_id(
                            document=document,
                            chunk_index=chunk_index,
                            chunk_text=chunk_text,
                            line_range=line_range,
                            paragraph_range=(
                                paragraph_range
                            ),
                        ),
                        document_id=(
                            document.document_id
                        ),
                        chunk_index=chunk_index,
                        page=document.page,
                        line_range=line_range,
                        paragraph_range=(
                            paragraph_range
                        ),
                        source=document.source,
                        text=chunk_text,
                    )
                )

                if end >= len(document.text):
                    break

                start += step
                chunk_index += 1

        return chunks
