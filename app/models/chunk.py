from dataclasses import dataclass

from app.models.source_location import (
    validate_source_location,
)


@dataclass
class Chunk:
    """
    A retrieval chunk with traceable source location.
    """

    id: str
    document_id: str
    subject_id: str
    chunk_index: int
    source: str
    text: str
    page: int | None = None
    line_range: tuple[int, int] | None = None
    paragraph_range: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        validate_source_location(
            owner="Chunk",
            page=self.page,
            line_range=self.line_range,
            paragraph_range=(
                self.paragraph_range
            ),
        )
