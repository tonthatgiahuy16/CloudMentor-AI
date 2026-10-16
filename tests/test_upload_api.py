from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.upload import (
    get_pdf_service,
    get_upload_dir,
    router,
)


class FakePDFService:
    def __init__(self):
        self.calls = []

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


class FailingPDFService:
    def upload(self, *args, **kwargs):
        raise RuntimeError(
            "Controlled processing failure"
        )


def make_client(
    tmp_path,
    service=None,
):
    if service is None:
        service = FakePDFService()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_pdf_service] = (
        lambda: service
    )
    app.dependency_overrides[get_upload_dir] = (
        lambda: tmp_path
    )
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
