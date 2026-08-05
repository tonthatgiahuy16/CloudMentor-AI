from fastapi import APIRouter

from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


chat_service = ChatService()


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):

    return chat_service.ask(
        request.question
    )