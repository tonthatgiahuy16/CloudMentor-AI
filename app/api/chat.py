from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from functools import lru_cache
from app.core.rate_limit import enforce_chat_rate_limit
from app.llm.exceptions import (
    LLMProviderError,
    LLMProviderUnavailableError,
)
from app.schemas.chat import ChatRequest, ChatResponse

from app.core.database import SessionLocal
from app.repos.document_repository import DocumentRepository
from app.repos.subject_repository import (
    SubjectRepository,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


class ApplicableDocumentResolver:
    """Resolve applicable documents with a short-lived DB session."""

    def list_applicable_document_ids(
        self,
        *,
        subject_id: str,
        as_of,
    ) -> list[str]:
        db = SessionLocal()
        try:
            return DocumentRepository(db).list_applicable_document_ids(
                subject_id=subject_id,
                as_of=as_of,
            )
        finally:
            db.close()


@lru_cache
def get_chat_service():
    from app.services.chat_service import ChatService

    service = ChatService()
    service.document_repo = ApplicableDocumentResolver()
    return service


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
            as_of=request.as_of,
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
