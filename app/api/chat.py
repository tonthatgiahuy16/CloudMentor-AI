from fastapi import APIRouter

from app.services.chat_service import ChatService


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


chat_service = ChatService()


@router.post("/")
def chat(
    question: str
):

    answer = chat_service.ask(
        question
    )

    return {
        "question": question,
        "answer": answer
    }