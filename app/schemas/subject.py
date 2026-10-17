from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Annotated, Literal


class SubjectCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("name")
    @classmethod
    def name_must_contain_text(cls, value: str) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError("name must not be empty")

        return normalized


class SubjectTrashResponse(BaseModel):
    subject_id: str
    name: str
    status: Literal[
        "DELETING",
        "DELETED",
        "DELETE_FAILED",
        "RESTORING",
        "RESTORE_FAILED",
    ]
    deleted_at: datetime | None
    lifecycle_error: str | None


class SubjectResponse(BaseModel):
    subject_id: str
    name: str


class SubjectDeletionResponse(BaseModel):
    subject_id: str
    status: Literal["DELETED"]
    processed_documents: Annotated[
        int,
        Field(ge=0),
    ]
    deleted_chunks: Annotated[
        int,
        Field(ge=0),
    ]


class SubjectRestoreResponse(BaseModel):
    subject_id: str
    status: Literal["ACTIVE"]
    processed_documents: Annotated[
        int,
        Field(ge=0),
    ]
    indexed_chunks: Annotated[
        int,
        Field(ge=0),
    ]
