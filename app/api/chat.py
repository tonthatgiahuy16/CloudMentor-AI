from fastapi import APIRouter, Depends

from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def get_chat_service():
    from app.services.chat_service import ChatService

    return ChatService()


@router.post(
    "/",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    chat_service=Depends(get_chat_service),
):
    return chat_service.ask(
        request.question
    )
