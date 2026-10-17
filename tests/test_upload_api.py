from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.upload import (
    get_pdf_service,
    get_upload_dir,
    get_upload_subject_repository,
    router,
)


class FakeSubjectRepository:
    def __init__(self, subject):
        self.subject = subject
        self.calls = []

    def get_by_id(self, subject_id):
        self.calls.append(subject_id)
        return self.subject


class FakePDFService:
    def __init__(self):
        self.calls = []

    def find_active_duplicate(
        self,
        *,
        subject_id,
        content_sha256,
    ):
        return None

    def upload(
        self,
        path,
        *,
        subject_id,
        chapter,
        document_id,
        original_filename,
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    ):
        self.calls.append(
            (
                Path(path),
                subject_id,
                chapter,
                document_id,
                original_filename,
                source_uri,
                content_sha256,
                file_size_bytes,
            )
        )
        return 7


class DuplicatePDFService(FakePDFService):
    def find_active_duplicate(
        self,
        *,
        subject_id,
        content_sha256,
    ):
        return SimpleNamespace(
            document_id="existing-document-id",
            filename="existing.pdf",
            status="INDEXED",
        )


class FailedDocumentPDFService(FakePDFService):
    def __init__(self):
        super().__init__()
        self.existing_document = SimpleNamespace(
            document_id="failed-document-id",
            filename="original.pdf",
            status="FAILED",
            source_uri="storage/uploads/failed-document.pdf",
        )
        self.retry_calls = []

    def find_active_duplicate(
        self,
        *,
        subject_id,
        content_sha256,
    ):
        return self.existing_document

    def retry_failed_document(
        self,
        document,
    ):
        self.retry_calls.append(document)
        return 5


class FailingPDFService:
    def upload(self, *args, **kwargs):
        raise RuntimeError(
            "Controlled processing failure"
        )

    def find_active_duplicate(
        self,
        *,
        subject_id,
        content_sha256,
    ):
        return None


class FailingRetryPDFService(
    FailedDocumentPDFService
):
    def retry_failed_document(
        self,
        document,
    ):
        self.retry_calls.append(document)
        raise RuntimeError(
            "Controlled retry failure"
        )

DEFAULT_SUBJECT = object()

def make_client(
    tmp_path,
    service=None,
    subject=DEFAULT_SUBJECT,
):
    if service is None:
        service = FakePDFService()

    if subject is DEFAULT_SUBJECT:
        subject = SimpleNamespace(
            subject_id="subject-active",
            status="ACTIVE",
        )

    subject_repo = FakeSubjectRepository(
        subject
    )

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_pdf_service] = (
        lambda: service
    )
    app.dependency_overrides[get_upload_dir] = (
        lambda: tmp_path
    )
    app.dependency_overrides[
        get_upload_subject_repository
    ] = lambda: subject_repo

    return TestClient(app), service


def test_upload_accepts_pdf_and_uses_safe_server_filename(
    tmp_path,
):
    client, service = make_client(tmp_path)

    pdf_data = b"%PDF-1.4\ncontent"

    response = client.post(
        "/upload/",
        files={
            "file": (
                "lesson.pdf",
                pdf_data,
                "application/pdf",
            )
        },
        data={
            "subject_id": (
                "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"
            ),
            "chapter": "3",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "lesson.pdf"
    assert payload["chunks"] == 7
    (
        saved_path,
        subject_id,
        chapter,
        document_id,
        original_filename,
        source_uri,
        content_sha256,
        file_size_bytes,
    ) = service.calls[0]
    assert subject_id == "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"
    assert chapter == 3
    assert original_filename == "lesson.pdf"
    assert saved_path.name == f"{document_id}_lesson.pdf"
    assert saved_path.read_bytes().startswith(b"%PDF-")
    assert source_uri == saved_path.as_posix()
    assert content_sha256 == sha256(pdf_data).hexdigest()
    assert file_size_bytes == len(pdf_data)


def test_upload_rejects_fake_pdf_content(tmp_path):
    client, _ = make_client(tmp_path)

    response = client.post(
        "/upload/",
        files={"file": ("lesson.pdf", b"not a pdf", "application/pdf")},
        data={"subject_id": "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"},
    )

    assert response.status_code == 415
    assert not list(tmp_path.iterdir())


def test_upload_rejects_wrong_extension(tmp_path):
    client, _ = make_client(tmp_path)

    response = client.post(
        "/upload/",
        files={"file": ("lesson.txt", b"%PDF-1.4", "application/pdf")},
        data={"subject_id": "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"},
    )

    assert response.status_code == 415


def test_upload_retains_valid_pdf_when_processing_fails(
    tmp_path,
):
    service = FailingPDFService()
    client, _ = make_client(
        tmp_path,
        service=service,
    )

    pdf_data = b"%PDF-1.4\nrecoverable content"

    response = client.post(
        "/upload/",
        files={
            "file": (
                "lesson.pdf",
                pdf_data,
                "application/pdf",
            )
        },
        data={
            "subject_id": (
                "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"
            ),
        },
    )

    assert response.status_code == 500

    retained_files = list(
        tmp_path.glob("*_lesson.pdf")
    )

    assert len(retained_files) == 1
    assert retained_files[0].read_bytes() == pdf_data


def test_upload_rejects_active_duplicate_before_writing_file(
    tmp_path,
):
    service = DuplicatePDFService()
    client, _ = make_client(
        tmp_path,
        service=service,
    )

    pdf_data = b"%PDF-1.4\nduplicate content"

    response = client.post(
        "/upload/",
        files={
            "file": (
                "renamed-copy.pdf",
                pdf_data,
                "application/pdf",
            )
        },
        data={
            "subject_id": (
                "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"
            ),
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "DOCUMENT_ALREADY_EXISTS",
            "document_id": "existing-document-id",
            "status": "INDEXED",
        }
    }
    assert service.calls == []
    assert list(tmp_path.iterdir()) == []


def test_upload_retries_failed_document_without_new_source_file(
    tmp_path,
):
    service = FailedDocumentPDFService()
    client, _ = make_client(
        tmp_path,
        service=service,
    )

    pdf_data = b"%PDF-1.4\nretryable content"

    response = client.post(
        "/upload/",
        files={
            "file": (
                "renamed-retry.pdf",
                pdf_data,
                "application/pdf",
            )
        },
        data={
            "subject_id": (
                "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"
            ),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "failed-document-id",
        "filename": "original.pdf",
        "chunks": 5,
    }

    assert service.calls == []
    assert service.retry_calls == [
        service.existing_document
    ]
    assert list(tmp_path.iterdir()) == []


def test_upload_returns_500_when_failed_document_retry_fails(
    tmp_path,
):
    service = FailingRetryPDFService()
    client, _ = make_client(
        tmp_path,
        service=service,
    )

    response = client.post(
        "/upload/",
        files={
            "file": (
                "retry.pdf",
                b"%PDF-1.4\nretryable content",
                "application/pdf",
            )
        },
        data={
            "subject_id": (
                "7d13e6d0-ef38-4bf2-a5cf-a593517087e4"
            ),
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "PDF retry failed"
    }
    assert service.calls == []
    assert service.retry_calls == [
        service.existing_document
    ]
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_subject_in_trash_before_writing(
    tmp_path,
):
    subject = SimpleNamespace(
        subject_id="subject-deleted",
        status="DELETED",
    )
    client, service = make_client(
        tmp_path,
        subject=subject,
    )

    response = client.post(
        "/upload/",
        files={
            "file": (
                "lesson.pdf",
                b"%PDF-1.4\ncontent",
                "application/pdf",
            )
        },
        data={
            "subject_id": "subject-deleted"
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Subject is not active"
    }
    assert service.calls == []
    assert not list(tmp_path.iterdir())


def test_upload_rejects_missing_subject_before_writing(
    tmp_path,
):
    client, service = make_client(
        tmp_path,
        subject=None,
    )

    response = client.post(
        "/upload/",
        files={
            "file": (
                "lesson.pdf",
                b"%PDF-1.4\ncontent",
                "application/pdf",
            )
        },
        data={
            "subject_id": "missing-subject"
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Subject not found"
    }
    assert service.calls == []
    assert not list(tmp_path.iterdir())
