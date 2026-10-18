import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatRequest,
    SourceResponse,
)


def test_chat_request_trims_question():
    request = ChatRequest(
        question="  hello  ",
        subject_id="subject-1",
    )

    assert request.question == "hello"


@pytest.mark.parametrize(
    "question",
    [
        "",
        "   ",
        "x" * 2001,
    ],
)
def test_chat_request_rejects_invalid_question(
    question,
):
    with pytest.raises(ValidationError):
        ChatRequest(
            question=question,
            subject_id="subject-1",
        )


def make_source_response(**location):
    return SourceResponse(
        chunk_id="chunk-1",
        document_id="document-1",
        chunk_index=0,
        source="lesson",
        distance=0.1,
        **location,
    )


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (
            {"page": 3},
            (3, None, None),
        ),
        (
            {"line_range": (4, 9)},
            (None, (4, 9), None),
        ),
        (
            {"paragraph_range": (2, 5)},
            (None, None, (2, 5)),
        ),
    ],
)
def test_source_response_accepts_one_source_location(
    location,
    expected,
):
    source = make_source_response(
        **location
    )

    assert (
        source.page,
        source.line_range,
        source.paragraph_range,
    ) == expected


@pytest.mark.parametrize(
    "location",
    [
        {},
        {
            "page": 1,
            "line_range": (1, 2),
        },
        {
            "page": 1,
            "paragraph_range": (1, 2),
        },
        {
            "line_range": (1, 2),
            "paragraph_range": (1, 2),
        },
        {"page": 0},
        {"line_range": (0, 2)},
        {"line_range": (4, 3)},
        {"paragraph_range": (0, 2)},
        {"paragraph_range": (4, 3)},
    ],
)
def test_source_response_rejects_invalid_source_location(
    location,
):
    with pytest.raises(ValidationError):
        make_source_response(
            **location
        )
