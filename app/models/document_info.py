from dataclasses import dataclass


@dataclass
class DocumentInfo:

    id: str

    filename: str

    pages: int

    chunks: int

    uploaded_at: str

    status: str