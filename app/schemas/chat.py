from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class SourceResponse(BaseModel):
    source: str
    page: int
    distance: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]