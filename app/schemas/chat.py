from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be empty")
        return normalized


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
