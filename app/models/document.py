from dataclasses import dataclass


@dataclass
class Document:
    """
    Đại diện cho một trang tài liệu sau khi đọc từ PDF.
    """

    page: int
    source: str
    text: str