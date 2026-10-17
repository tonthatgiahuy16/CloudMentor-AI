from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.subjects import (
    get_subject_repository,
    get_subject_deletion_service,
    get_subject_restore_service,
    router,
)


class FakeSubjectRepository:
    def __init__(self, subjects):
        self.subjects = subjects

    def list_all(self):
        return self.subjects

    def list_active(self):
        return [
            subject
            for subject in self.subjects
            if getattr(
                subject,
                "status",
                "ACTIVE",
            ) == "ACTIVE"
        ]

    def create(self, *, name):
        if any(subject.name == name for subject in self.subjects):
            raise IntegrityError("duplicate", {}, None)

        subject = SimpleNamespace(
            subject_id="subject-created",
            name=name,
        )
        self.subjects.append(subject)
        return subject


    def list_trash(self):
        return [
            subject
            for subject in self.subjects
            if getattr(
                subject,
                "status",
                "ACTIVE",
            ) != "ACTIVE"
        ]


class FakeSubjectDeletionService:
    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.calls = []

    def delete(self, subject_id):
        self.calls.append(subject_id)

        if self.error is not None:
            raise self.error

        return self.result


class FakeSubjectRestoreService:
    def __init__(
        self,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.calls = []

    def restore(self, subject_id):
        self.calls.append(subject_id)

        if self.error is not None:
            raise self.error

        return self.result

def make_client(
    subjects,
    deletion_service=None,
    restore_service=None,
):
    repository = FakeSubjectRepository(subjects)

    if deletion_service is None:
        deletion_service = (
            FakeSubjectDeletionService()
        )

    if restore_service is None:
        restore_service = (
            FakeSubjectRestoreService()
        )

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[
        get_subject_repository
    ] = lambda: repository

    app.dependency_overrides[
        get_subject_deletion_service
    ] = lambda: deletion_service

    app.dependency_overrides[
        get_subject_restore_service
    ] = lambda: restore_service

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


def test_list_subjects_excludes_subjects_in_trash():
    client = make_client(
        [
            SimpleNamespace(
                subject_id="subject-active",
                name="Data Engineering",
                status="ACTIVE",
            ),
            SimpleNamespace(
                subject_id="subject-deleted",
                name="Cloud Computing",
                status="DELETED",
            ),
        ]
    )

    response = client.get("/subjects/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "subject_id": "subject-active",
            "name": "Data Engineering",
        },
    ]

def test_list_subject_trash_returns_lifecycle_details():
    client = make_client(
        [
            SimpleNamespace(
                subject_id="subject-active",
                name="Data Engineering",
                status="ACTIVE",
                deleted_at=None,
                lifecycle_error=None,
            ),
            SimpleNamespace(
                subject_id="subject-failed",
                name="Cloud Computing",
                status="DELETE_FAILED",
                deleted_at=None,
                lifecycle_error="Chroma unavailable",
            ),
        ]
    )

    response = client.get(
        "/subjects/trash"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "subject_id": "subject-failed",
            "name": "Cloud Computing",
            "status": "DELETE_FAILED",
            "deleted_at": None,
            "lifecycle_error": (
                "Chroma unavailable"
            ),
        },
    ]


def test_delete_subject_returns_lifecycle_result():
    deletion_service = FakeSubjectDeletionService(
        result={
            "subject_id": "subject-1",
            "status": "DELETED",
            "processed_documents": 2,
            "deleted_chunks": 5,
        }
    )
    client = make_client(
        [],
        deletion_service=deletion_service,
    )

    response = client.delete(
        "/subjects/subject-1"
    )

    assert response.status_code == 200
    assert response.json() == {
        "subject_id": "subject-1",
        "status": "DELETED",
        "processed_documents": 2,
        "deleted_chunks": 5,
    }
    assert deletion_service.calls == [
        "subject-1"
    ]


def test_delete_subject_returns_404_when_missing():
    deletion_service = FakeSubjectDeletionService(
        error=RuntimeError(
            "Subject not found"
        )
    )
    client = make_client(
        [],
        deletion_service=deletion_service,
    )

    response = client.delete(
        "/subjects/missing-subject"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Subject not found"
    }


def test_delete_subject_returns_500_when_deletion_fails():
    deletion_service = FakeSubjectDeletionService(
        error=RuntimeError(
            "Chroma unavailable"
        )
    )
    client = make_client(
        [],
        deletion_service=deletion_service,
    )

    response = client.delete(
        "/subjects/subject-1"
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Subject deletion failed"
    }


def test_restore_subject_returns_lifecycle_result():
    restore_service = FakeSubjectRestoreService(
        result={
            "subject_id": "subject-1",
            "status": "ACTIVE",
            "processed_documents": 2,
            "indexed_chunks": 5,
        }
    )
    client = make_client(
        [],
        restore_service=restore_service,
    )

    response = client.post(
        "/subjects/subject-1/restore"
    )

    assert response.status_code == 200
    assert response.json() == {
        "subject_id": "subject-1",
        "status": "ACTIVE",
        "processed_documents": 2,
        "indexed_chunks": 5,
    }
    assert restore_service.calls == [
        "subject-1"
    ]


def test_restore_subject_returns_404_when_missing():
    restore_service = FakeSubjectRestoreService(
        error=RuntimeError(
            "Subject not found"
        )
    )
    client = make_client(
        [],
        restore_service=restore_service,
    )

    response = client.post(
        "/subjects/missing-subject/restore"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Subject not found"
    }


def test_restore_subject_returns_500_when_rebuild_fails():
    restore_service = FakeSubjectRestoreService(
        error=RuntimeError(
            "Retained source is missing"
        )
    )
    client = make_client(
        [],
        restore_service=restore_service,
    )

    response = client.post(
        "/subjects/subject-1/restore"
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Subject restoration failed"
    }
