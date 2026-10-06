import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest


def test_chat_request_trims_question():
    assert ChatRequest(question="  hello  ").question == "hello"


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
def test_chat_request_rejects_invalid_question(question):
    with pytest.raises(ValidationError):
        ChatRequest(question=question)

def test_chat_request_trims_subject_id():
    request = ChatRequest(
        question="hello",
        subject_id="  subject-1  ",
    )

    assert request.subject_id == "subject-1"