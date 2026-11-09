import pytest

from app.repos.quiz_repository import QuizRepository
from app.services.quiz_authoring_service import (
    QuizAuthoringService,
)


def make_service(db_session):
    return QuizAuthoringService(QuizRepository(db_session))


def make_draft_quiz(service, subject_id):
    return service.create_quiz(
        subject_id=subject_id,
        title="Cloud Security",
    )


def add_valid_question(
    service,
    quiz_id,
    *,
    correct_first=True,
):
    return service.add_question(
        quiz_id=quiz_id,
        prompt="IAM là gì?",
        options=[
            {
                "text": "Identity and Access Management",
                "is_correct": correct_first,
            },
            {
                "text": "Infrastructure as a Service",
                "is_correct": not correct_first,
            },
        ],
        source_document_id="document-1",
        source_document_version="3",
    )


def test_create_quiz_returns_summary(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)

    result = make_draft_quiz(
        service,
        quiz_subject.subject_id,
    )

    assert result["status"] == "DRAFT"
    assert result["subject_id"] == quiz_subject.subject_id
    assert result["title"] == "Cloud Security"
    assert result["question_count"] == 0


def test_add_question_persists_options_without_answer_key(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)

    result = add_valid_question(
        service,
        quiz["quiz_id"],
    )

    assert result["position"] == 0
    assert result["source_document_id"] == "document-1"
    assert result["source_document_version"] == "3"
    assert len(result["options"]) == 2
    assert all(
        "is_correct" not in option
        for option in result["options"]
    )


def test_add_question_assigns_incrementing_positions(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)

    first = add_valid_question(service, quiz["quiz_id"])
    second = add_valid_question(service, quiz["quiz_id"])

    assert first["position"] == 0
    assert second["position"] == 1


def test_add_question_rejects_missing_quiz(
    quiz_db_session,
):
    service = make_service(quiz_db_session)

    with pytest.raises(
        RuntimeError,
        match="Quiz not found",
    ):
        add_valid_question(service, "missing-quiz")


def test_add_question_rejects_published_quiz(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)
    add_valid_question(service, quiz["quiz_id"])
    service.publish_quiz(quiz["quiz_id"])

    with pytest.raises(
        RuntimeError,
        match="Only draft quizzes can be edited",
    ):
        add_valid_question(service, quiz["quiz_id"])


def test_add_question_rejects_multiple_correct_options(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)

    with pytest.raises(
        RuntimeError,
        match="exactly one correct option",
    ):
        service.add_question(
            quiz_id=quiz["quiz_id"],
            prompt="IAM là gì?",
            options=[
                {"text": "A", "is_correct": True},
                {"text": "B", "is_correct": True},
            ],
        )


def test_publish_requires_at_least_one_question(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)

    with pytest.raises(
        RuntimeError,
        match="at least one question",
    ):
        service.publish_quiz(quiz["quiz_id"])


def test_publish_requires_two_options_per_question(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)
    service.add_question(
        quiz_id=quiz["quiz_id"],
        prompt="IAM là gì?",
        options=[{"text": "Only one", "is_correct": True}],
    )

    with pytest.raises(
        RuntimeError,
        match="at least two options",
    ):
        service.publish_quiz(quiz["quiz_id"])


def test_publish_marks_quiz_published(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)
    add_valid_question(service, quiz["quiz_id"])

    result = service.publish_quiz(quiz["quiz_id"])

    assert result["status"] == "PUBLISHED"
    assert result["question_count"] == 1


def test_publish_is_idempotent(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)
    add_valid_question(service, quiz["quiz_id"])
    service.publish_quiz(quiz["quiz_id"])

    second = service.publish_quiz(quiz["quiz_id"])

    assert second["status"] == "PUBLISHED"
    assert second["question_count"] == 1


def test_get_published_quiz_hides_answer_key(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)
    add_valid_question(service, quiz["quiz_id"])
    service.publish_quiz(quiz["quiz_id"])

    result = service.get_published_quiz(quiz["quiz_id"])

    assert result["status"] == "PUBLISHED"
    assert result["question_count"] == 1
    assert result["questions"][0]["prompt"] == "IAM là gì?"
    assert all(
        "is_correct" not in option
        for option in result["questions"][0]["options"]
    )


def test_get_published_quiz_rejects_draft(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    quiz = make_draft_quiz(service, quiz_subject.subject_id)

    with pytest.raises(
        RuntimeError,
        match="Quiz is not published",
    ):
        service.get_published_quiz(quiz["quiz_id"])


def test_list_published_quizzes_excludes_drafts(
    quiz_db_session,
    quiz_subject,
):
    service = make_service(quiz_db_session)
    published = make_draft_quiz(
        service,
        quiz_subject.subject_id,
    )
    add_valid_question(service, published["quiz_id"])
    service.publish_quiz(published["quiz_id"])
    make_draft_quiz(service, quiz_subject.subject_id)

    results = service.list_published_quizzes(
        subject_id=quiz_subject.subject_id
    )

    assert [quiz["quiz_id"] for quiz in results] == [
        published["quiz_id"]
    ]
