from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


def _normalize(value: str) -> str:
    return " ".join(value.split())


class QuizCreate(BaseModel):
    subject_id: Annotated[str, Field(min_length=1, max_length=100)]
    title: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("subject_id")
    @classmethod
    def subject_id_must_contain_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("subject_id must not be empty")
        return normalized

    @field_validator("title")
    @classmethod
    def title_must_contain_text(cls, value: str) -> str:
        normalized = _normalize(value)
        if not normalized:
            raise ValueError("title must not be empty")
        return normalized


class QuizOptionCreate(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=2_000)]
    is_correct: bool = False

    @field_validator("text")
    @classmethod
    def text_must_contain_text(cls, value: str) -> str:
        normalized = _normalize(value)
        if not normalized:
            raise ValueError("option text must not be empty")
        return normalized


class QuizQuestionCreate(BaseModel):
    prompt: Annotated[str, Field(min_length=1, max_length=4_000)]
    options: Annotated[
        list[QuizOptionCreate],
        Field(min_length=2, max_length=10),
    ]
    source_document_id: Annotated[
        str,
        Field(min_length=1, max_length=100),
    ] | None = None
    source_document_version: Annotated[
        str,
        Field(min_length=1, max_length=100),
    ] | None = None

    @field_validator("prompt")
    @classmethod
    def prompt_must_contain_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prompt must not be empty")
        return normalized

    @model_validator(mode="after")
    def exactly_one_correct_option(self):
        correct_count = sum(
            1 for option in self.options if option.is_correct
        )
        if correct_count != 1:
            raise ValueError(
                "A question must have exactly one correct option"
            )
        return self


class QuizOptionPublic(BaseModel):
    option_id: str
    text: str
    position: int


class QuizQuestionPublic(BaseModel):
    question_id: str
    prompt: str
    position: int
    options: list[QuizOptionPublic]
    source_document_id: str | None = None
    source_document_version: str | None = None


class QuizPublic(BaseModel):
    quiz_id: str
    subject_id: str
    title: str
    status: Literal["PUBLISHED"]
    question_count: int
    questions: list[QuizQuestionPublic]


class QuizSummary(BaseModel):
    quiz_id: str
    subject_id: str
    title: str
    status: Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
    question_count: int


class QuizCreateResponse(BaseModel):
    quiz_id: str
    subject_id: str
    title: str
    status: Literal["DRAFT", "PUBLISHED", "ARCHIVED"]


class QuizPublishResponse(BaseModel):
    quiz_id: str
    status: Literal["PUBLISHED"]
    question_count: int


class AttemptStartRequest(BaseModel):
    employee_id: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("employee_id")
    @classmethod
    def employee_id_must_contain_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("employee_id must not be empty")
        return normalized


class AttemptStartResponse(BaseModel):
    attempt_id: str
    quiz_id: str
    employee_id: str
    status: Literal["IN_PROGRESS"]


class AttemptAnswerSubmit(BaseModel):
    question_id: Annotated[str, Field(min_length=1, max_length=100)]
    option_id: Annotated[str, Field(min_length=1, max_length=100)] | None = None


class AttemptSubmitRequest(BaseModel):
    answers: list[AttemptAnswerSubmit] = Field(
        default_factory=list,
    )


class AttemptAnswerResult(BaseModel):
    question_id: str
    selected_option_id: str | None = None
    correct_option_id: str
    is_correct: bool


class AttemptResult(BaseModel):
    attempt_id: str
    quiz_id: str
    employee_id: str
    status: Literal["GRADED"]
    score: float
    correct_count: int
    total_questions: int
    graded_at: datetime | None = None
    answers: list[AttemptAnswerResult]


class QuizOverview(BaseModel):
    quiz_id: str
    attempt_count: int
    graded_attempt_count: int
    average_score: float | None
