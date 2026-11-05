from hashlib import sha256
import json
from typing import List
import uuid

from app.models.chunk import Chunk
from app.models.document import Document

CHUNK_ID_SCHEMA_VERSION = "v2"


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 150,
        split_paragraphs: bool = False,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0:
            raise ValueError("overlap must not be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.split_paragraphs = split_paragraphs

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
            "split_paragraphs": self.split_paragraphs,
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

    def _documents_for_split(
        self,
        document: Document,
    ) -> list[Document]:
        if (
            not self.split_paragraphs
            or document.paragraph_range is None
        ):
            return [document]

        paragraph_start, _ = document.paragraph_range
        return [
            Document(
                document_id=document.document_id,
                subject_id=document.subject_id,
                source=document.source,
                text=paragraph,
                page=document.page,
                paragraph_range=(
                    paragraph_start + offset,
                    paragraph_start + offset,
                ),
            )
            for offset, paragraph in enumerate(
                document.text.split("\n")
            )
        ]

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

            chunk_index = 0
            for split_document in self._documents_for_split(
                document
            ):
                start = 0
                while start < len(split_document.text):
                    end = min(
                        start + self.chunk_size,
                        len(split_document.text),
                    )

                    line_range = None
                    paragraph_range = None

                    if split_document.line_range is not None:
                        line_range = (
                            self._source_range_for_slice(
                                text=split_document.text,
                                source_range=(
                                    split_document.line_range
                                ),
                                start=start,
                                end=end,
                            )
                        )

                    elif (
                        split_document.paragraph_range
                        is not None
                    ):
                        paragraph_range = (
                            self._source_range_for_slice(
                                text=split_document.text,
                                source_range=(
                                    split_document.paragraph_range
                                ),
                                start=start,
                                end=end,
                            )
                        )

                    chunk_text = split_document.text[start:end]

                    chunks.append(
                        Chunk(
                            subject_id=(
                                split_document.subject_id
                            ),
                            id=self._build_chunk_id(
                                document=split_document,
                                chunk_index=chunk_index,
                                chunk_text=chunk_text,
                                line_range=line_range,
                                paragraph_range=(
                                    paragraph_range
                                ),
                            ),
                            document_id=(
                                split_document.document_id
                            ),
                            chunk_index=chunk_index,
                            page=split_document.page,
                            line_range=line_range,
                            paragraph_range=(
                                paragraph_range
                            ),
                            source=split_document.source,
                            text=chunk_text,
                        )
                    )

                    if end >= len(split_document.text):
                        break

                    start += step
                    chunk_index += 1

                if split_document.text:
                    chunk_index += 1

        return chunks
