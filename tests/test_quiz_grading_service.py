import pytest

from app.repos.quiz_repository import QuizRepository
from app.services.quiz_authoring_service import (
    QuizAuthoringService,
)
from app.services.quiz_grading_service import (
    QuizGradingService,
)


@pytest.fixture
def services(quiz_db_session):
    repository = QuizRepository(quiz_db_session)
    return (
        QuizAuthoringService(repository),
        QuizGradingService(repository),
    )


def add_question(
    authoring_service,
    quiz_id,
    *,
    correct_first=True,
):
    return authoring_service.add_question(
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
    )


def publish_quiz_with_questions(
    authoring_service,
    subject_id,
):
    quiz = authoring_service.create_quiz(
        subject_id=subject_id,
        title="Cloud Security",
    )
    first = add_question(
        authoring_service,
        quiz["quiz_id"],
    )
    second = add_question(
        authoring_service,
        quiz["quiz_id"],
    )
    authoring_service.publish_quiz(quiz["quiz_id"])
    return quiz, first, second


def correct_option(question):
    return question["options"][0]["option_id"]


def wrong_option(question):
    return question["options"][1]["option_id"]


def test_start_attempt_requires_published_quiz(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz = authoring_service.create_quiz(
        subject_id=quiz_subject.subject_id,
        title="Draft quiz",
    )

    with pytest.raises(
        RuntimeError,
        match="Quiz is not published",
    ):
        grading_service.start_attempt(
            quiz_id=quiz["quiz_id"],
            employee_id="new-hire-1",
        )


def test_start_attempt_rejects_missing_quiz(services):
    _, grading_service = services

    with pytest.raises(
        RuntimeError,
        match="Quiz not found",
    ):
        grading_service.start_attempt(
            quiz_id="missing-quiz",
            employee_id="new-hire-1",
        )


def test_submit_grades_all_questions(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )

    result = grading_service.submit_attempt(
        attempt_id=attempt["attempt_id"],
        answers=[
            {
                "question_id": first["question_id"],
                "option_id": correct_option(first),
            },
            {
                "question_id": second["question_id"],
                "option_id": wrong_option(second),
            },
        ],
    )

    assert result["status"] == "GRADED"
    assert result["employee_id"] == "new-hire-1"
    assert result["correct_count"] == 1
    assert result["total_questions"] == 2
    assert result["score"] == 0.5

    by_question = {
        answer["question_id"]: answer
        for answer in result["answers"]
    }
    assert by_question[first["question_id"]]["is_correct"] is True
    assert by_question[second["question_id"]]["is_correct"] is False


def test_unanswered_question_is_incorrect(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )

    result = grading_service.submit_attempt(
        attempt_id=attempt["attempt_id"],
        answers=[
            {
                "question_id": first["question_id"],
                "option_id": correct_option(first),
            }
        ],
    )

    assert result["correct_count"] == 1
    assert result["total_questions"] == 2
    assert result["score"] == 0.5
    by_question = {
        answer["question_id"]: answer
        for answer in result["answers"]
    }
    assert (
        by_question[second["question_id"]]["selected_option_id"]
        is None
    )
    assert (
        by_question[second["question_id"]]["is_correct"]
        is False
    )


def test_submit_rejects_question_outside_quiz(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, _ = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )

    with pytest.raises(
        RuntimeError,
        match="outside the quiz",
    ):
        grading_service.submit_attempt(
            attempt_id=attempt["attempt_id"],
            answers=[
                {
                    "question_id": "foreign-question",
                    "option_id": "foreign-option",
                }
            ],
        )


def test_submit_rejects_duplicate_answers(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, _ = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )

    with pytest.raises(
        RuntimeError,
        match="Duplicate answer",
    ):
        grading_service.submit_attempt(
            attempt_id=attempt["attempt_id"],
            answers=[
                {
                    "question_id": first["question_id"],
                    "option_id": correct_option(first),
                },
                {
                    "question_id": first["question_id"],
                    "option_id": wrong_option(first),
                },
            ],
        )


def test_submit_rejects_option_from_another_question(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )

    with pytest.raises(
        RuntimeError,
        match="does not belong to the question",
    ):
        grading_service.submit_attempt(
            attempt_id=attempt["attempt_id"],
            answers=[
                {
                    "question_id": first["question_id"],
                    "option_id": correct_option(second),
                }
            ],
        )


def test_submit_twice_is_rejected(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )
    grading_service.submit_attempt(
        attempt_id=attempt["attempt_id"],
        answers=[],
    )

    with pytest.raises(
        RuntimeError,
        match="already submitted",
    ):
        grading_service.submit_attempt(
            attempt_id=attempt["attempt_id"],
            answers=[],
        )


def test_get_result_reconstructs_graded_attempt(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )
    submitted = grading_service.submit_attempt(
        attempt_id=attempt["attempt_id"],
        answers=[
            {
                "question_id": first["question_id"],
                "option_id": correct_option(first),
            }
        ],
    )

    result = grading_service.get_result(
        attempt["attempt_id"]
    )

    assert result["score"] == submitted["score"]
    assert result["correct_count"] == 1
    assert len(result["answers"]) == 2
    assert all(
        answer["correct_option_id"] is not None
        for answer in result["answers"]
    )


def test_get_result_rejects_in_progress_attempt(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, _, _ = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )
    attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )

    with pytest.raises(
        RuntimeError,
        match="not graded",
    ):
        grading_service.get_result(attempt["attempt_id"])


def test_get_overview_averages_graded_attempts(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )

    first_attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )
    grading_service.submit_attempt(
        attempt_id=first_attempt["attempt_id"],
        answers=[
            {
                "question_id": first["question_id"],
                "option_id": correct_option(first),
            },
            {
                "question_id": second["question_id"],
                "option_id": correct_option(second),
            },
        ],
    )

    second_attempt = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-2",
    )
    grading_service.submit_attempt(
        attempt_id=second_attempt["attempt_id"],
        answers=[],
    )

    # A third, ungraded attempt must not affect the average.
    grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-3",
    )

    overview = grading_service.get_overview(quiz["quiz_id"])

    assert overview["attempt_count"] == 3
    assert overview["graded_attempt_count"] == 2
    assert overview["average_score"] == 0.5


def test_get_overview_without_graded_attempts(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, _, _ = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )

    overview = grading_service.get_overview(quiz["quiz_id"])

    assert overview["attempt_count"] == 0
    assert overview["graded_attempt_count"] == 0
    assert overview["average_score"] is None


def test_list_attempt_results_returns_only_graded_attempts(
    services,
    quiz_subject,
):
    authoring_service, grading_service = services
    quiz, first, second = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )

    graded = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-1",
    )
    grading_service.submit_attempt(
        attempt_id=graded["attempt_id"],
        answers=[
            {
                "question_id": first["question_id"],
                "option_id": correct_option(first),
            },
            {
                "question_id": second["question_id"],
                "option_id": wrong_option(second),
            },
        ],
    )

    in_progress = grading_service.start_attempt(
        quiz_id=quiz["quiz_id"],
        employee_id="new-hire-2",
    )

    results = grading_service.list_attempt_results(
        quiz["quiz_id"]
    )

    assert [result["attempt_id"] for result in results] == [
        graded["attempt_id"]
    ]
    assert results[0]["employee_id"] == "new-hire-1"
    assert results[0]["score"] == 0.5
    assert results[0]["correct_count"] == 1
    assert results[0]["total_questions"] == 2
    assert results[0]["status"] == "GRADED"
    assert in_progress["attempt_id"] not in {
        result["attempt_id"] for result in results
    }

    by_question = {
        answer["question_id"]: answer
        for answer in results[0]["answers"]
    }
    assert (
        by_question[first["question_id"]]["correct_option_id"]
        == correct_option(first)
    )
    assert (
        by_question[second["question_id"]]["correct_option_id"]
        == correct_option(second)
    )
    assert (
        by_question[first["question_id"]]["selected_option_id"]
        == correct_option(first)
    )


def test_list_attempt_results_without_attempts(services, quiz_subject):
    authoring_service, grading_service = services
    quiz, _, _ = publish_quiz_with_questions(
        authoring_service,
        quiz_subject.subject_id,
    )

    assert (
        grading_service.list_attempt_results(quiz["quiz_id"])
        == []
    )


def test_list_attempt_results_rejects_missing_quiz(services):
    _, grading_service = services

    with pytest.raises(
        RuntimeError,
        match="Quiz not found",
    ):
        grading_service.list_attempt_results("missing-quiz")
