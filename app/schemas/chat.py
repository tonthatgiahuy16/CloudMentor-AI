from typing import Annotated

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from app.models.source_location import (
    validate_source_location,
)


class ChatRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=2_000)]
    subject_id: str = Field(
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
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "subject_id must not be empty"
            )

        return normalized


class SourceResponse(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    source: str
    page: int | None = None
    line_range: tuple[int, int] | None = None
    paragraph_range: tuple[int, int] | None = None
    distance: float

    @model_validator(mode="after")
    def source_location_must_be_valid(
        self,
    ):
        validate_source_location(
            owner="Source response",
            page=self.page,
            line_range=self.line_range,
            paragraph_range=(
                self.paragraph_range
            ),
        )

        return self


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]
