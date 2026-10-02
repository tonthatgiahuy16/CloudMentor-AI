from types import SimpleNamespace

import pytest

from app.services.document_deletion_service import (
    DocumentDeletionService,
)


class FakeDocumentRepository:
    def __init__(self, document, call_log):
        self.document = document
        self.call_log = call_log
        self.mark_deleted_calls = []

    def get_by_id(self, document_id):
        if self.document is None:
            return None

        if self.document.document_id != document_id:
            return None

        return self.document

    def mark_deleted(self, document_id):
        self.call_log.append("postgresql")
        self.mark_deleted_calls.append(document_id)
        self.document.status = "DELETED"
        return self.document


class FakeVectorStore:
    def __init__(
        self,
        call_log,
        deleted_chunks=0,
        error=None,
    ):
        self.call_log = call_log
        self.deleted_chunks = deleted_chunks
        self.error = error
        self.delete_calls = []

    def delete_by_document_id(self, document_id):
        self.call_log.append("chroma")
        self.delete_calls.append(document_id)

        if self.error is not None:
            raise self.error

        return self.deleted_chunks


def make_document(status="INDEXED"):
    return SimpleNamespace(
        document_id="document-1",
        status=status,
    )


def test_delete_removes_chunks_then_marks_document_deleted():
    call_log = []
    document = make_document()
    repository = FakeDocumentRepository(
        document,
        call_log,
    )
    vector_store = FakeVectorStore(
        call_log,
        deleted_chunks=7
    )

    service = DocumentDeletionService(
        document_repo=repository,
        vector_store=vector_store,
    )

    result = service.delete("document-1")

    assert result == {
        "document_id": "document-1",
        "status": "DELETED",
        "deleted_chunks": 7,
    }
    assert vector_store.delete_calls == ["document-1"]
    assert repository.mark_deleted_calls == ["document-1"]
    assert call_log == ["chroma", "postgresql"]


def test_delete_raises_when_document_is_missing():
    call_log = []
    repository = FakeDocumentRepository(
        None,
        call_log,
    )
    vector_store = FakeVectorStore(
        call_log,
    )

    service = DocumentDeletionService(
        document_repo=repository,
        vector_store=vector_store,
    )

    with pytest.raises(
        RuntimeError,
        match="Document not found",
    ):
        service.delete("missing-document")

    assert vector_store.delete_calls == []
    assert repository.mark_deleted_calls == []
    assert call_log == []


def test_delete_is_idempotent_when_document_is_already_deleted():
    call_log = []
    document = make_document(status="DELETED")
    repository = FakeDocumentRepository(
        document,
        call_log,
    )
    vector_store = FakeVectorStore(call_log)

    service = DocumentDeletionService(
        document_repo=repository,
        vector_store=vector_store,
    )

    result = service.delete("document-1")

    assert result == {
        "document_id": "document-1",
        "status": "DELETED",
        "deleted_chunks": 0,
    }
    assert vector_store.delete_calls == []
    assert repository.mark_deleted_calls == []
    assert call_log == []


def test_delete_does_not_mark_postgresql_deleted_when_chroma_fails():
    call_log = []
    document = make_document()
    repository = FakeDocumentRepository(
        document,
        call_log,
    )
    vector_store = FakeVectorStore(
        call_log,
        error=RuntimeError("Chroma unavailable")
    )

    service = DocumentDeletionService(
        document_repo=repository,
        vector_store=vector_store,
    )

    with pytest.raises(
        RuntimeError,
        match="Chroma unavailable",
    ):
        service.delete("document-1")

    assert repository.mark_deleted_calls == []
    assert document.status == "INDEXED"
    assert call_log == ["chroma"]