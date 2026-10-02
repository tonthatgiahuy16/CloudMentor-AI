from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.documents import (
    get_document_deletion_service,
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