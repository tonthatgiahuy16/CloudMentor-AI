from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from app.core.rate_limit import enforce_chat_rate_limit
from app.llm.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
)
from app.schemas.chat import ChatRequest, ChatResponse

from functools import lru_cache
from app.core.database import SessionLocal
from app.repos.subject_repository import (
    SubjectRepository,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

@lru_cache
def get_chat_service():
    from app.services.chat_service import ChatService

    return ChatService()


def get_chat_subject_repository():
    db = SessionLocal()

    try:
        yield SubjectRepository(db)
    finally:
        db.close()


@router.post(
    "/",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    http_request: Request,
    chat_service=Depends(get_chat_service),
    subject_repo=Depends(
        get_chat_subject_repository
    ),
):

    enforce_chat_rate_limit(http_request)

    subject = subject_repo.get_by_id(
        request.subject_id
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found",
        )

    if subject.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subject is not active",
        )

    try:
        return chat_service.ask(
            request.question,
            subject_id=request.subject_id,
        )
    except LLMProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider request failed",
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM provider request failed",
        ) from exc
