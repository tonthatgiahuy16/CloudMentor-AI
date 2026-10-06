from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class SubjectCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError("name must not be empty")

        return normalized


class SubjectResponse(BaseModel):
    subject_id: str
    name: str
