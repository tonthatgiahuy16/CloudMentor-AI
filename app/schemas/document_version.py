from datetime import date

from pydantic import BaseModel, Field


class PolicyVersionActivationRequest(BaseModel):
    effective_from: date
    supersedes_document_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
