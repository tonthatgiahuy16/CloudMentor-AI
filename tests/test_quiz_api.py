from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.quizzes import (
    get_quiz_authoring_service,
    get_quiz_grading_service,
    router,
)


class FakeAuthoringService:
    def __init__(
        self,
        *,
        create_result=None,
        list_result=None,
        question_result=None,
        publish_result=None,
        quiz_result=None,
        error=None,
    ):
        self.create_result = create_result
        self.list_result = list_result
        self.question_result = question_result
        self.publish_result = publish_result
        self.quiz_result = quiz_result
        self.error = error
        self.calls = []

    def create_quiz(self, *, subject_id, title):
        self.calls.append(("create_quiz", subject_id, title))
        self._maybe_raise()
        return self.create_result

    def list_published_quizzes(self, *, subject_id):
        self.calls.append(("list", subject_id))
        self._maybe_raise()
        return self.list_result

    def add_question(self, **kwargs):
        self.calls.append(("add_question", kwargs))
        self._maybe_raise()
        return self.question_result

    def publish_quiz(self, quiz_id):
        self.calls.append(("publish", quiz_id))
        self._maybe_raise()
        return self.publish_result

    def get_published_quiz(self, quiz_id):
        self.calls.append(("get_quiz", quiz_id))
        self._maybe_raise()
        return self.quiz_result

    def _maybe_raise(self):
        if self.error is not None:
            raise self.error


class FakeGradingService:
    def __init__(
        self,
        *,
        start_result=None,
        submit_result=None,
        result=None,
        overview_result=None,
        list_result=None,
        error=None,
    ):
        self.start_result = start_result
        self.submit_result = submit_result
        self.result = result
        self.overview_result = overview_result
        self.list_result = list_result
        self.error = error
        self.calls = []

    def start_attempt(self, *, quiz_id, employee_id):
        self.calls.append(("start", quiz_id, employee_id))
        self._maybe_raise()
        return self.start_result

    def submit_attempt(self, *, attempt_id, answers):
        self.calls.append(("submit", attempt_id, answers))
        self._maybe_raise()
        return self.submit_result

    def get_result(self, attempt_id):
        self.calls.append(("result", attempt_id))
        self._maybe_raise()
        return self.result

    def get_overview(self, quiz_id):
        self.calls.append(("overview", quiz_id))
        self._maybe_raise()
        return self.overview_result

    def list_attempt_results(self, quiz_id):
        self.calls.append(("list_attempts", quiz_id))
        self._maybe_raise()
        return self.list_result

    def _maybe_raise(self):
        if self.error is not None:
            raise self.error


def make_client(
    authoring_service=None,
    grading_service=None,
):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[
        get_quiz_authoring_service
    ] = lambda: authoring_service or FakeAuthoringService()
    app.dependency_overrides[
        get_quiz_grading_service
    ] = lambda: grading_service or FakeGradingService()

    return TestClient(app)


def question_payload():
    return {
        "prompt": "IAM là gì?",
        "options": [
            {
                "text": "Identity and Access Management",
                "is_correct": True,
            },
            {
                "text": "Infrastructure as a Service",
                "is_correct": False,
            },
        ],
        "source_document_id": "document-1",
        "source_document_version": "3",
    }


def test_create_quiz_returns_created():
    service = FakeAuthoringService(
        create_result={
            "quiz_id": "quiz-1",
            "subject_id": "subject-1",
            "title": "Cloud Security",
            "status": "DRAFT",
            "question_count": 0,
        }
    )
    client = make_client(authoring_service=service)

    response = client.post(
        "/quizzes/",
        json={
            "subject_id": "subject-1",
            "title": "  Cloud   Security ",
        },
    )

    assert response.status_code == 201
    assert response.json()["quiz_id"] == "quiz-1"
    assert service.calls == [
        ("create_quiz", "subject-1", "Cloud Security")
    ]


def test_list_quizzes_requires_subject_id():
    client = make_client()

    response = client.get("/quizzes/")

    assert response.status_code == 422


def test_list_quizzes_returns_published_summaries():
    service = FakeAuthoringService(
        list_result=[
            {
                "quiz_id": "quiz-1",
                "subject_id": "subject-1",
                "title": "Cloud Security",
                "status": "PUBLISHED",
                "question_count": 2,
            }
        ]
    )
    client = make_client(authoring_service=service)

    response = client.get(
        "/quizzes/",
        params={"subject_id": "subject-1"},
    )

    assert response.status_code == 200
    assert response.json()[0]["quiz_id"] == "quiz-1"
    assert service.calls == [("list", "subject-1")]


def test_add_question_returns_created():
    service = FakeAuthoringService(
        question_result={
            "question_id": "question-1",
            "prompt": "IAM là gì?",
            "position": 0,
            "source_document_id": "document-1",
            "source_document_version": "3",
            "options": [
                {
                    "option_id": "option-1",
                    "text": "Identity and Access Management",
                    "position": 0,
                },
                {
                    "option_id": "option-2",
                    "text": "Infrastructure as a Service",
                    "position": 1,
                },
            ],
        }
    )
    client = make_client(authoring_service=service)

    response = client.post(
        "/quizzes/quiz-1/questions",
        json=question_payload(),
    )

    assert response.status_code == 201
    assert response.json()["question_id"] == "question-1"
    assert "is_correct" not in response.json()["options"][0]


def test_add_question_translates_missing_quiz_to_404():
    service = FakeAuthoringService(
        error=RuntimeError("Quiz not found")
    )
    client = make_client(authoring_service=service)

    response = client.post(
        "/quizzes/missing/questions",
        json=question_payload(),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}


def test_add_question_translates_business_error_to_409():
    service = FakeAuthoringService(
        error=RuntimeError(
            "Only draft quizzes can be edited"
        )
    )
    client = make_client(authoring_service=service)

    response = client.post(
        "/quizzes/quiz-1/questions",
        json=question_payload(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Only draft quizzes can be edited"
    }


def test_publish_quiz_returns_published_status():
    service = FakeAuthoringService(
        publish_result={
            "quiz_id": "quiz-1",
            "status": "PUBLISHED",
            "question_count": 2,
        }
    )
    client = make_client(authoring_service=service)

    response = client.post("/quizzes/quiz-1/publish")

    assert response.status_code == 200
    assert response.json() == {
        "quiz_id": "quiz-1",
        "status": "PUBLISHED",
        "question_count": 2,
    }


def test_get_quiz_returns_public_questions():
    service = FakeAuthoringService(
        quiz_result={
            "quiz_id": "quiz-1",
            "subject_id": "subject-1",
            "title": "Cloud Security",
            "status": "PUBLISHED",
            "question_count": 1,
            "questions": [
                {
                    "question_id": "question-1",
                    "prompt": "IAM là gì?",
                    "position": 0,
                    "source_document_id": "document-1",
                    "source_document_version": "3",
                    "options": [
                        {
                            "option_id": "option-1",
                            "text": "Identity and Access Management",
                            "position": 0,
                        }
                    ],
                }
            ],
        }
    )
    client = make_client(authoring_service=service)

    response = client.get("/quizzes/quiz-1")

    assert response.status_code == 200
    assert response.json()["status"] == "PUBLISHED"
    assert "is_correct" not in response.json()["questions"][0][
        "options"
    ][0]


def test_start_attempt_returns_created():
    service = FakeGradingService(
        start_result={
            "attempt_id": "attempt-1",
            "quiz_id": "quiz-1",
            "employee_id": "new-hire-1",
            "status": "IN_PROGRESS",
        }
    )
    client = make_client(grading_service=service)

    response = client.post(
        "/quizzes/quiz-1/attempts",
        json={"employee_id": "new-hire-1"},
    )

    assert response.status_code == 201
    assert response.json()["attempt_id"] == "attempt-1"


def test_submit_attempt_returns_grade():
    service = FakeGradingService(
        submit_result={
            "attempt_id": "attempt-1",
            "quiz_id": "quiz-1",
            "employee_id": "new-hire-1",
            "status": "GRADED",
            "score": 0.5,
            "correct_count": 1,
            "total_questions": 2,
            "answers": [
                {
                    "question_id": "question-1",
                    "selected_option_id": "option-1",
                    "correct_option_id": "option-1",
                    "is_correct": True,
                }
            ],
        }
    )
    client = make_client(grading_service=service)

    response = client.post(
        "/quizzes/attempts/attempt-1/submit",
        json={
            "answers": [
                {
                    "question_id": "question-1",
                    "option_id": "option-1",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "GRADED"
    assert service.calls == [
        (
            "submit",
            "attempt-1",
            [
                {
                    "question_id": "question-1",
                    "option_id": "option-1",
                }
            ],
        )
    ]


def test_get_attempt_result_translates_missing_to_404():
    service = FakeGradingService(
        error=RuntimeError("Attempt not found")
    )
    client = make_client(grading_service=service)

    response = client.get("/quizzes/attempts/missing")

    assert response.status_code == 404


def test_get_attempt_result_translates_business_error_to_409():
    service = FakeGradingService(
        error=RuntimeError("Attempt is not graded")
    )
    client = make_client(grading_service=service)

    response = client.get("/quizzes/attempts/attempt-1")

    assert response.status_code == 409


def test_overview_returns_aggregate():
    service = FakeGradingService(
        overview_result={
            "quiz_id": "quiz-1",
            "attempt_count": 3,
            "graded_attempt_count": 2,
            "average_score": 0.5,
        }
    )
    client = make_client(grading_service=service)

    response = client.get("/quizzes/quiz-1/overview")

    assert response.status_code == 200
    assert response.json()["average_score"] == 0.5


def test_list_attempt_results_returns_graded_attempts():
    service = FakeGradingService(
        list_result=[
            {
                "attempt_id": "attempt-1",
                "quiz_id": "quiz-1",
                "employee_id": "new-hire-1",
                "status": "GRADED",
                "score": 0.5,
                "correct_count": 1,
                "total_questions": 2,
                "answers": [
                    {
                        "question_id": "question-1",
                        "selected_option_id": "option-1",
                        "correct_option_id": "option-1",
                        "is_correct": True,
                    }
                ],
            }
        ]
    )
    client = make_client(grading_service=service)

    response = client.get("/quizzes/quiz-1/attempts")

    assert response.status_code == 200
    assert response.json()[0]["attempt_id"] == "attempt-1"
    assert response.json()[0]["status"] == "GRADED"
    assert service.calls == [("list_attempts", "quiz-1")]


def test_list_attempt_results_translates_missing_quiz_to_404():
    service = FakeGradingService(
        error=RuntimeError("Quiz not found")
    )
    client = make_client(grading_service=service)

    response = client.get("/quizzes/missing/attempts")

    assert response.status_code == 404
    assert response.json() == {"detail": "Quiz not found"}


def test_demo_mode_blocks_mutations(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config, "DEMO_MODE", True)
    service = FakeAuthoringService(
        create_result={
            "quiz_id": "quiz-1",
            "subject_id": "subject-1",
            "title": "Cloud Security",
            "status": "DRAFT",
            "question_count": 0,
        }
    )
    client = make_client(authoring_service=service)

    response = client.post(
        "/quizzes/",
        json={
            "subject_id": "subject-1",
            "title": "Cloud Security",
        },
    )

    assert response.status_code == 403
    assert service.calls == []
