from dataclasses import dataclass


@dataclass
class Document:
    """
    Đại diện cho một trang tài liệu sau khi đọc từ PDF.
    """
    document_id: str
    subject_id: str
    page: int
    source: str
    text: str