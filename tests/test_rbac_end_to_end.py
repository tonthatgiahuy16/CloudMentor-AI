from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.documents import get_document_repository
from app.api.quizzes import (
    get_quiz_grading_service,
    get_quiz_repository,
)
from app.api.subjects import get_subject_repository
from app.core.security import create_access_token, hash_password
from app.db_models.user import User
from app.main import app
from app.repos.user_repository import UserRepository


@pytest.fixture
def client(quiz_db_session):
    def override_db():
        yield quiz_db_session

    app.dependency_overrides[get_db] = override_db
    UserRepository(quiz_db_session).create(
        employee_id="alice",
        password_hash=hash_password("correct horse battery"),
        role="employee",
    )
    UserRepository(quiz_db_session).create(
        employee_id="root",
        password_hash=hash_password("correct horse battery"),
        role="admin",
    )

    try:
        yield TestClient(app), quiz_db_session
    finally:
        app.dependency_overrides.clear()


def _headers(employee_id, role):
    token = create_access_token(
        employee_id=employee_id,
        role=role,
    )
    return {"Authorization": f"Bearer {token}"}


class FakeSubjectRepository:
    def list_active(self):
        return []


class FakeDocumentRepository:
    def list_active(self):
        return []


class FakeGradingService:
    def __init__(self, *, result=None):
        self.result = result or {}
        self.calls = []

    def start_attempt(self, *, quiz_id, employee_id):
        self.calls.append(("start", quiz_id, employee_id))
        return {
            "attempt_id": "attempt-1",
            "quiz_id": quiz_id,
            "employee_id": employee_id,
            "status": "IN_PROGRESS",
        }

    def get_result(self, attempt_id):
        self.calls.append(("result", attempt_id))
        return self.result

    def submit_attempt(self, *, attempt_id, answers):
        self.calls.append(("submit", attempt_id, answers))
        return self.result

    def get_overview(self, quiz_id):
        self.calls.append(("overview", quiz_id))
        return {
            "quiz_id": quiz_id,
            "attempt_count": 0,
            "graded_attempt_count": 0,
            "average_score": None,
        }


class FakeAttemptRepository:
    def __init__(self, employee_id):
        self.employee_id = employee_id

    def get_attempt(self, attempt_id):
        return SimpleNamespace(
            attempt_id=attempt_id,
            employee_id=self.employee_id,
        )


def test_employee_cannot_list_admin_documents(client):
    test_client, _ = client
    app.dependency_overrides[get_document_repository] = (
        lambda: FakeDocumentRepository()
    )

    response = test_client.get(
        "/documents/",
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 403


def test_admin_can_list_documents(client):
    test_client, _ = client
    app.dependency_overrides[get_document_repository] = (
        lambda: FakeDocumentRepository()
    )

    response = test_client.get(
        "/documents/",
        headers=_headers("root", "admin"),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_employee_cannot_create_subject(client):
    test_client, _ = client
    app.dependency_overrides[get_subject_repository] = (
        lambda: FakeSubjectRepository()
    )

    response = test_client.post(
        "/subjects/",
        json={"name": "Policies"},
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 403


def test_employee_can_list_subjects(client):
    test_client, _ = client
    app.dependency_overrides[get_subject_repository] = (
        lambda: FakeSubjectRepository()
    )

    response = test_client.get(
        "/subjects/",
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_start_attempt_uses_token_identity_not_request_body(client):
    test_client, _ = client
    grading = FakeGradingService()
    app.dependency_overrides[get_quiz_grading_service] = (
        lambda: grading
    )

    response = test_client.post(
        "/quizzes/quiz-1/attempts",
        json={"employee_id": "someone-else"},
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 201
    assert grading.calls == [
        ("start", "quiz-1", "alice"),
    ]
    assert response.json()["employee_id"] == "alice"


def test_employee_cannot_read_another_employees_attempt(client):
    test_client, _ = client
    grading = FakeGradingService()
    app.dependency_overrides[get_quiz_grading_service] = (
        lambda: grading
    )
    app.dependency_overrides[get_quiz_repository] = (
        lambda: FakeAttemptRepository("bob")
    )

    response = test_client.get(
        "/quizzes/attempts/attempt-1",
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 404
    assert grading.calls == []


def test_employee_cannot_submit_another_employees_attempt(client):
    test_client, _ = client
    grading = FakeGradingService()
    app.dependency_overrides[get_quiz_grading_service] = (
        lambda: grading
    )
    app.dependency_overrides[get_quiz_repository] = (
        lambda: FakeAttemptRepository("bob")
    )

    response = test_client.post(
        "/quizzes/attempts/attempt-1/submit",
        json={"answers": []},
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 404
    assert grading.calls == []


def test_admin_can_read_any_attempt(client):
    test_client, _ = client
    grading = FakeGradingService(
        result={
            "attempt_id": "attempt-1",
            "quiz_id": "quiz-1",
            "employee_id": "bob",
            "status": "GRADED",
            "score": 1.0,
            "correct_count": 1,
            "total_questions": 1,
            "answers": [],
        }
    )
    app.dependency_overrides[get_quiz_grading_service] = (
        lambda: grading
    )
    app.dependency_overrides[get_quiz_repository] = (
        lambda: FakeAttemptRepository("bob")
    )

    response = test_client.get(
        "/quizzes/attempts/attempt-1",
        headers=_headers("root", "admin"),
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == "bob"


def test_employee_cannot_read_training_overview(client):
    test_client, _ = client
    app.dependency_overrides[get_quiz_grading_service] = (
        lambda: FakeGradingService()
    )

    response = test_client.get(
        "/quizzes/quiz-1/overview",
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 403


def test_admin_can_read_training_overview(client):
    test_client, _ = client
    app.dependency_overrides[get_quiz_grading_service] = (
        lambda: FakeGradingService()
    )

    response = test_client.get(
        "/quizzes/quiz-1/overview",
        headers=_headers("root", "admin"),
    )

    assert response.status_code == 200


def test_missing_token_is_rejected_before_service_use(client):
    test_client, _ = client

    response = test_client.get("/documents/")

    assert response.status_code == 401


def test_employee_token_cannot_access_metrics(client):
    test_client, _ = client

    response = test_client.get(
        "/metrics/pipeline",
        headers=_headers("alice", "employee"),
    )

    assert response.status_code == 403
