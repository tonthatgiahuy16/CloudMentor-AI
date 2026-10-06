from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.subjects import (
    get_subject_repository,
    router,
)


class FakeSubjectRepository:
    def __init__(self, subjects):
        self.subjects = subjects

    def list_all(self):
        return self.subjects

    def create(self, *, name):
        if any(subject.name == name for subject in self.subjects):
            raise IntegrityError("duplicate", {}, None)

        subject = SimpleNamespace(
            subject_id="subject-created",
            name=name,
        )
        self.subjects.append(subject)
        return subject


def make_client(subjects):
    repository = FakeSubjectRepository(subjects)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[
        get_subject_repository
    ] = lambda: repository

    return TestClient(app)


def test_list_subjects_returns_subjects():
    client = make_client(
        [
            SimpleNamespace(
                subject_id="subject-1",
                name="Cloud Computing",
            ),
            SimpleNamespace(
                subject_id="subject-2",
                name="Data Engineering",
            ),
        ]
    )

    response = client.get("/subjects/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "subject_id": "subject-1",
            "name": "Cloud Computing",
        },
        {
            "subject_id": "subject-2",
            "name": "Data Engineering",
        },
    ]


def test_list_subjects_returns_empty_list():
    client = make_client([])

    response = client.get("/subjects/")

    assert response.status_code == 200
    assert response.json() == []


def test_create_subject_returns_created_subject():
    client = make_client([])

    response = client.post(
        "/subjects/",
        json={"name": "  Data   Engineering  "},
    )

    assert response.status_code == 201
    assert response.json() == {
        "subject_id": "subject-created",
        "name": "Data Engineering",
    }


def test_create_subject_rejects_duplicate_name():
    client = make_client(
        [SimpleNamespace(subject_id="subject-1", name="Data Engineering")]
    )

    response = client.post(
        "/subjects/",
        json={"name": "Data Engineering"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Môn học đã tồn tại"}


def test_create_subject_rejects_blank_name():
    client = make_client([])

    response = client.post(
        "/subjects/",
        json={"name": "   "},
    )

    assert response.status_code == 422
