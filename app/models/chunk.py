from dataclasses import dataclass


@dataclass
class Chunk:
    """
    Một đoạn văn bản sau khi được chia nhỏ từ Document.
    """

    id: str
    page: int
    source: str
    text: str