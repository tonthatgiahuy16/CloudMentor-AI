from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=2_000)]
    subject_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @field_validator("question")
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("question must not be empty")

        return normalized

    @field_validator("subject_id")
    @classmethod
    def subject_id_must_contain_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            raise ValueError("subject_id must not be empty")

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
