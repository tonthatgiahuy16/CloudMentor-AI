from datetime import date
from types import SimpleNamespace

import pytest

from app.services.policy_version_service import (
    PolicyVersionService,
)


class FakeDocumentRepository:
    def __init__(self, document=None):
        self.document = document
        self.get_calls = []
        self.activate_calls = []

    def get_by_id(self, document_id):
        self.get_calls.append(document_id)
        return self.document

    def activate_policy_version(self, **kwargs):
        self.activate_calls.append(kwargs)
        return SimpleNamespace(
            document_id=kwargs["document_id"],
            effective_from=kwargs["effective_from"],
            supersedes_document_id=kwargs[
                "supersedes_document_id"
            ],
        )


class FakeVectorStore:
    def __init__(self, chunk_count=0, error=None):
        self.chunk_count = chunk_count
        self.error = error
        self.count_calls = []

    def count_by_document_id(self, document_id):
        self.count_calls.append(document_id)

        if self.error is not None:
            raise self.error

        return self.chunk_count


def make_document(
    *,
    status="INDEXED",
    indexed_chunk_count=3,
):
    return SimpleNamespace(
        document_id="document-1",
        status=status,
        indexed_chunk_count=indexed_chunk_count,
    )


def make_service(document=None, chunk_count=3, error=None):
    repository = FakeDocumentRepository(document)
    vector_store = FakeVectorStore(
        chunk_count=chunk_count,
        error=error,
    )
    return (
        PolicyVersionService(
            document_repo=repository,
            vector_store=vector_store,
        ),
        repository,
        vector_store,
    )


def test_activate_succeeds_when_chunk_count_matches():
    service, repository, vector_store = make_service(
        document=make_document(indexed_chunk_count=3),
        chunk_count=3,
    )
    effective_from = date(2026, 11, 10)

    result = service.activate(
        document_id="document-1",
        effective_from=effective_from,
        supersedes_document_id="document-0",
    )

    assert result.document_id == "document-1"
    assert result.effective_from == effective_from
    assert vector_store.count_calls == ["document-1"]
    assert repository.activate_calls == [
        {
            "document_id": "document-1",
            "effective_from": effective_from,
            "supersedes_document_id": "document-0",
        }
    ]


def test_activate_passes_none_for_optional_supersedes():
    service, repository, _ = make_service(
        document=make_document(indexed_chunk_count=3),
        chunk_count=3,
    )

    service.activate(
        document_id="document-1",
        effective_from=date(2026, 11, 10),
    )

    assert repository.activate_calls[0][
        "supersedes_document_id"
    ] is None


def test_activate_rejects_missing_document_before_reading_chroma():
    service, repository, vector_store = make_service(
        document=None,
    )

    with pytest.raises(
        RuntimeError,
        match="Document not found",
    ):
        service.activate(
            document_id="missing-document",
            effective_from=date(2026, 11, 10),
        )

    assert vector_store.count_calls == []
    assert repository.activate_calls == []


def test_activate_rejects_document_not_indexed():
    service, repository, vector_store = make_service(
        document=make_document(status="UPLOADED"),
    )

    with pytest.raises(
        RuntimeError,
        match="Only indexed documents can be activated",
    ):
        service.activate(
            document_id="document-1",
            effective_from=date(2026, 11, 10),
        )

    assert vector_store.count_calls == []
    assert repository.activate_calls == []


def test_activate_rejects_unverified_chunk_count():
    service, repository, vector_store = make_service(
        document=make_document(indexed_chunk_count=None),
    )

    with pytest.raises(
        RuntimeError,
        match="Document index has not been verified",
    ):
        service.activate(
            document_id="document-1",
            effective_from=date(2026, 11, 10),
        )

    assert vector_store.count_calls == []
    assert repository.activate_calls == []


@pytest.mark.parametrize("chroma_chunk_count", [0, 1, 2, 4])
def test_activate_rejects_chunk_count_mismatch(
    chroma_chunk_count,
):
    service, repository, _ = make_service(
        document=make_document(indexed_chunk_count=3),
        chunk_count=chroma_chunk_count,
    )

    with pytest.raises(
        RuntimeError,
        match="Indexed chunk count does not match PostgreSQL",
    ):
        service.activate(
            document_id="document-1",
            effective_from=date(2026, 11, 10),
        )

    assert repository.activate_calls == []


def test_activate_propagates_chroma_lineage_error():
    service, repository, _ = make_service(
        document=make_document(indexed_chunk_count=3),
        error=RuntimeError(
            "Vector index document lineage verification failed"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="lineage verification failed",
    ):
        service.activate(
            document_id="document-1",
            effective_from=date(2026, 11, 10),
        )

    assert repository.activate_calls == []
