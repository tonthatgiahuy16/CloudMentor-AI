from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class SourceResponse(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    source: str
    page: int
    distance: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]