from dataclasses import dataclass


@dataclass
class Chunk:
    """
    Một đoạn text được chia nhỏ từ Document.
    """

    id: str
    document_id: str
    subject_id: str
    chunk_index: int
    page: int
    source: str
    text: str