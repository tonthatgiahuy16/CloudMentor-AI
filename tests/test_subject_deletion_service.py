import pytest
from types import SimpleNamespace
from unittest.mock import Mock, call

from app.services.subject_deletion_service import (
    SubjectDeletionService,
)


def test_delete_removes_subject_vectors_then_marks_deleted():
    call_log = []

    subject = SimpleNamespace(
        subject_id="subject-1",
        status="ACTIVE",
    )
    documents = [
        SimpleNamespace(
            document_id="document-1"
        ),
        SimpleNamespace(
            document_id="document-2"
        ),
    ]

    subject_repo = Mock()
    subject_repo.get_by_id.return_value = subject

    subject_repo.mark_deleting.side_effect = (
        lambda subject_id: (
            call_log.append("subject:deleting")
            or subject
        )
    )

    deleted_subject = SimpleNamespace(
        subject_id="subject-1",
        status="DELETED",
    )
    subject_repo.mark_deleted.side_effect = (
        lambda subject_id: (
            call_log.append("subject:deleted")
            or deleted_subject
        )
    )

    document_repo = Mock()
    document_repo.list_active_by_subject.return_value = (
        documents
    )

    vector_store = Mock()

    def delete_vectors(document_id):
        call_log.append(
            f"chroma:{document_id}"
        )

        return {
            "document-1": 3,
            "document-2": 2,
        }[document_id]

    vector_store.delete_by_document_id.side_effect = (
        delete_vectors
    )

    service = SubjectDeletionService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        vector_store=vector_store,
    )

    result = service.delete("subject-1")

    assert result == {
        "subject_id": "subject-1",
        "status": "DELETED",
        "processed_documents": 2,
        "deleted_chunks": 5,
    }

    subject_repo.get_by_id.assert_called_once_with(
        "subject-1"
    )
    subject_repo.mark_deleting.assert_called_once_with(
        "subject-1"
    )
    document_repo.list_active_by_subject.assert_called_once_with(
        "subject-1"
    )
    assert (
        vector_store
        .delete_by_document_id
        .call_args_list
    ) == [
        call("document-1"),
        call("document-2"),
    ]
    subject_repo.mark_deleted.assert_called_once_with(
        "subject-1"
    )

    assert call_log == [
        "subject:deleting",
        "chroma:document-1",
        "chroma:document-2",
        "subject:deleted",
    ]

def test_delete_records_failure_when_chroma_fails():
    subject = SimpleNamespace(
        subject_id="subject-1",
        status="ACTIVE",
    )
    document = SimpleNamespace(
        document_id="document-1"
    )

    subject_repo = Mock()
    subject_repo.get_by_id.return_value = subject

    document_repo = Mock()
    document_repo.list_active_by_subject.return_value = [
        document
    ]

    vector_store = Mock()
    vector_store.delete_by_document_id.side_effect = (
        RuntimeError("Chroma unavailable")
    )

    service = SubjectDeletionService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        vector_store=vector_store,
    )

    with pytest.raises(
        RuntimeError,
        match="Chroma unavailable",
    ):
        service.delete("subject-1")

    subject_repo.mark_deleting.assert_called_once_with(
        "subject-1"
    )
    subject_repo.mark_delete_failed.assert_called_once_with(
        subject_id="subject-1",
        error_message="Chroma unavailable",
    )
    subject_repo.mark_deleted.assert_not_called()


def test_delete_is_idempotent_when_subject_already_deleted():
    subject = SimpleNamespace(
        subject_id="subject-1",
        status="DELETED",
    )

    subject_repo = Mock()
    subject_repo.get_by_id.return_value = subject

    document_repo = Mock()
    vector_store = Mock()

    service = SubjectDeletionService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        vector_store=vector_store,
    )

    result = service.delete("subject-1")

    assert result == {
        "subject_id": "subject-1",
        "status": "DELETED",
        "processed_documents": 0,
        "deleted_chunks": 0,
    }

    subject_repo.mark_deleting.assert_not_called()
    subject_repo.mark_deleted.assert_not_called()
    subject_repo.mark_delete_failed.assert_not_called()
    document_repo.list_active_by_subject.assert_not_called()
    vector_store.delete_by_document_id.assert_not_called()


def test_delete_raises_when_subject_missing():
    subject_repo = Mock()
    subject_repo.get_by_id.return_value = None

    document_repo = Mock()
    vector_store = Mock()

    service = SubjectDeletionService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        vector_store=vector_store,
    )

    with pytest.raises(
        RuntimeError,
        match="Subject not found",
    ):
        service.delete("missing-subject")

    subject_repo.mark_deleting.assert_not_called()
    subject_repo.mark_deleted.assert_not_called()
    subject_repo.mark_delete_failed.assert_not_called()
    document_repo.list_active_by_subject.assert_not_called()
    vector_store.delete_by_document_id.assert_not_called()
