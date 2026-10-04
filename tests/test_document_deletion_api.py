from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.api.documents import (
    get_document_deletion_service,
    get_document_repository,
    router,
)


class FakeDocumentDeletionService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.delete_calls = []

    def delete(self, document_id):
        self.delete_calls.append(document_id)

        if self.error is not None:
            raise self.error

        return self.result


def make_client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[
        get_document_deletion_service
    ] = lambda: service

    return TestClient(app)


def test_delete_document_returns_service_result():
    service = FakeDocumentDeletionService(
        result={
            "document_id": "document-1",
            "status": "DELETED",
            "deleted_chunks": 7,
        }
    )
    client = make_client(service)

    response = client.delete("/documents/document-1")

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "document-1",
        "status": "DELETED",
        "deleted_chunks": 7,
    }
    assert service.delete_calls == ["document-1"]


def test_delete_document_returns_404_when_missing():
    service = FakeDocumentDeletionService(
        error=RuntimeError("Document not found")
    )
    client = make_client(service)

    response = client.delete("/documents/missing-document")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document not found",
    }
    assert service.delete_calls == ["missing-document"]


def test_delete_document_returns_500_when_deletion_fails():
    service = FakeDocumentDeletionService(
        error=RuntimeError("Chroma unavailable")
    )
    client = make_client(service)

    response = client.delete("/documents/document-1")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Document deletion failed",
    }
    assert service.delete_calls == ["document-1"]


class FakeDocumentRepository:
    def __init__(self, documents):
        self.documents = documents

    def list_active(self):
        return [
            document
            for document in self.documents
            if document.status != "DELETED"
        ]

    def get_by_id(self, document_id):
        for document in self.documents:
            if document.document_id == document_id:
                return document

        return None


def make_document(
    document_id="document-1",
    status="INDEXED",
):
    return SimpleNamespace(
        document_id=document_id,
        subject_id="subject-1",
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
        status=status,
        uploaded_at="2026-10-04T10:00:00Z",
        indexed_at="2026-10-04T10:01:00Z",
    )


def make_query_client(document_repo):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[
        get_document_repository
    ] = lambda: document_repo

    return TestClient(app)


def test_list_documents_returns_active_documents():
    active_document = make_document()
    deleted_document = make_document(
        document_id="document-2",
        status="DELETED",
    )
    repository = FakeDocumentRepository(
        [active_document, deleted_document]
    )
    client = make_query_client(repository)

    response = client.get("/documents/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "document_id": "document-1",
            "subject_id": "subject-1",
            "filename": "lesson.pdf",
            "file_type": "pdf",
            "chapter": 1,
            "status": "INDEXED",
            "uploaded_at": "2026-10-04T10:00:00Z",
            "indexed_at": "2026-10-04T10:01:00Z",
        }
    ]


def test_get_document_returns_document_details():
    document = make_document()
    repository = FakeDocumentRepository([document])
    client = make_query_client(repository)

    response = client.get("/documents/document-1")

    assert response.status_code == 200
    assert response.json()["document_id"] == "document-1"
    assert response.json()["status"] == "INDEXED"
    assert response.json()["filename"] == "lesson.pdf"


def test_get_document_returns_404_when_missing_or_deleted():
    deleted_document = make_document(
        status="DELETED",
    )
    repository = FakeDocumentRepository(
        [deleted_document]
    )
    client = make_query_client(repository)

    missing_response = client.get(
        "/documents/missing-document"
    )
    deleted_response = client.get(
        "/documents/document-1"
    )

    assert missing_response.status_code == 404
    assert deleted_response.status_code == 404