import pytest
from pydantic import ValidationError

from app.schemas.quiz import (
    AttemptAnswerSubmit,
    AttemptStartRequest,
    AttemptSubmitRequest,
    QuizCreate,
    QuizOptionCreate,
    QuizQuestionCreate,
)


def make_option(text="Option", is_correct=False):
    return QuizOptionCreate(
        text=text,
        is_correct=is_correct,
    )


def test_quiz_create_normalizes_title():
    payload = QuizCreate(
        subject_id="subject-1",
        title="  Cloud   Security  ",
    )

    assert payload.title == "Cloud Security"


def test_quiz_create_rejects_blank_title():
    with pytest.raises(ValidationError):
        QuizCreate(
            subject_id="subject-1",
            title="   ",
        )


def test_quiz_create_rejects_blank_subject_id():
    with pytest.raises(ValidationError):
        QuizCreate(
            subject_id="   ",
            title="Cloud",
        )


def test_question_requires_exactly_one_correct_option():
    payload = QuizQuestionCreate(
        prompt="IAM là gì?",
        options=[
            make_option("Identity and Access Management", True),
            make_option("Infrastructure"),
        ],
    )

    assert payload.options[0].is_correct is True


def test_question_rejects_zero_correct_options():
    with pytest.raises(ValidationError):
        QuizQuestionCreate(
            prompt="IAM là gì?",
            options=[
                make_option("Identity"),
                make_option("Infrastructure"),
            ],
        )


def test_question_rejects_multiple_correct_options():
    with pytest.raises(ValidationError):
        QuizQuestionCreate(
            prompt="IAM là gì?",
            options=[
                make_option("Identity", True),
                make_option("Infrastructure", True),
            ],
        )


def test_question_requires_at_least_two_options():
    with pytest.raises(ValidationError):
        QuizQuestionCreate(
            prompt="IAM là gì?",
            options=[make_option("Identity", True)],
        )


def test_option_text_is_normalized_and_blank_rejected():
    assert QuizOptionCreate(
        text="  Identity   and Access  "
    ).text == "Identity and Access"

    with pytest.raises(ValidationError):
        QuizOptionCreate(text="   ")


def test_attempt_start_requires_employee_identity():
    assert AttemptStartRequest(
        employee_id="  new-hire-1 "
    ).employee_id == "new-hire-1"

    with pytest.raises(ValidationError):
        AttemptStartRequest(employee_id="   ")


def test_attempt_submit_allows_unanswered_question():
    payload = AttemptSubmitRequest(
        answers=[
            AttemptAnswerSubmit(
                question_id="question-1",
                option_id=None,
            )
        ]
    )

    assert payload.answers[0].option_id is None


def test_attempt_submit_defaults_to_empty_answers():
    assert AttemptSubmitRequest().answers == []
