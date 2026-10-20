import pytest
from types import SimpleNamespace
from unittest.mock import Mock, call

from app.services.subject_restore_service import (
    SubjectRestoreService,
)

from app.storage.source_storage import (
    SourceUnavailableError,
)

def test_restore_rebuilds_documents_then_marks_subject_active():
    call_log = []

    subject = SimpleNamespace(
        subject_id="subject-1",
        status="DELETED",
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

    subject_repo.mark_restoring.side_effect = (
        lambda subject_id: (
            call_log.append("subject:restoring")
            or subject
        )
    )

    active_subject = SimpleNamespace(
        subject_id="subject-1",
        status="ACTIVE",
    )
    subject_repo.mark_active.side_effect = (
        lambda subject_id: (
            call_log.append("subject:active")
            or active_subject
        )
    )

    document_repo = Mock()
    document_repo.list_active_by_subject.return_value = (
        documents
    )

    pdf_service = Mock()

    def rebuild(document):
        call_log.append(
            f"rebuild:{document.document_id}"
        )

        return {
            "document-1": 3,
            "document-2": 2,
        }[document.document_id]

    pdf_service.rebuild_retained_document.side_effect = (
        rebuild
    )

    service = SubjectRestoreService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    result = service.restore("subject-1")

    assert result == {
        "subject_id": "subject-1",
        "status": "ACTIVE",
        "processed_documents": 2,
        "indexed_chunks": 5,
    }

    subject_repo.get_by_id.assert_called_once_with(
        "subject-1"
    )
    subject_repo.mark_restoring.assert_called_once_with(
        "subject-1"
    )
    document_repo.list_active_by_subject.assert_called_once_with(
        "subject-1"
    )
    assert (
        pdf_service
        .rebuild_retained_document
        .call_args_list
    ) == [
        call(documents[0]),
        call(documents[1]),
    ]
    subject_repo.mark_active.assert_called_once_with(
        "subject-1"
    )

    assert call_log == [
        "subject:restoring",
        "rebuild:document-1",
        "rebuild:document-2",
        "subject:active",
    ]


def test_restore_records_failure_when_document_rebuild_fails():
    subject = SimpleNamespace(
        subject_id="subject-1",
        status="DELETED",
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

    pdf_service = Mock()
    pdf_service.rebuild_retained_document.side_effect = (
        RuntimeError("Retained source is missing")
    )

    service = SubjectRestoreService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    with pytest.raises(
        RuntimeError,
        match="Retained source is missing",
    ):
        service.restore("subject-1")

    subject_repo.mark_restoring.assert_called_once_with(
        "subject-1"
    )
    subject_repo.mark_restore_failed.assert_called_once_with(
        subject_id="subject-1",
        error_message="Retained source is missing",
    )
    subject_repo.mark_active.assert_not_called()


def test_restore_is_idempotent_when_subject_already_active():
    subject = SimpleNamespace(
        subject_id="subject-1",
        status="ACTIVE",
    )

    subject_repo = Mock()
    subject_repo.get_by_id.return_value = subject

    document_repo = Mock()
    pdf_service = Mock()

    service = SubjectRestoreService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    result = service.restore("subject-1")

    assert result == {
        "subject_id": "subject-1",
        "status": "ACTIVE",
        "processed_documents": 0,
        "indexed_chunks": 0,
    }

    subject_repo.mark_restoring.assert_not_called()
    subject_repo.mark_active.assert_not_called()
    subject_repo.mark_restore_failed.assert_not_called()
    document_repo.list_active_by_subject.assert_not_called()
    pdf_service.rebuild_retained_document.assert_not_called()


def test_restore_raises_when_subject_missing():
    subject_repo = Mock()
    subject_repo.get_by_id.return_value = None

    document_repo = Mock()
    pdf_service = Mock()

    service = SubjectRestoreService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    with pytest.raises(
        RuntimeError,
        match="Subject not found",
    ):
        service.restore("missing-subject")

    subject_repo.mark_restoring.assert_not_called()
    subject_repo.mark_active.assert_not_called()
    subject_repo.mark_restore_failed.assert_not_called()
    document_repo.list_active_by_subject.assert_not_called()
    pdf_service.rebuild_retained_document.assert_not_called()


def test_restore_retries_after_temporary_storage_failure():
    deleted_subject = SimpleNamespace(
        subject_id="subject-1",
        status="DELETED",
    )
    restore_failed_subject = SimpleNamespace(
        subject_id="subject-1",
        status="RESTORE_FAILED",
    )
    active_subject = SimpleNamespace(
        subject_id="subject-1",
        status="ACTIVE",
    )
    document = SimpleNamespace(
        document_id="document-1",
    )

    subject_repo = Mock()
    subject_repo.get_by_id.side_effect = [
        deleted_subject,
        restore_failed_subject,
    ]
    subject_repo.mark_active.return_value = (
        active_subject
    )

    document_repo = Mock()
    document_repo.list_active_by_subject.return_value = [
        document
    ]

    pdf_service = Mock()
    pdf_service.rebuild_retained_document.side_effect = [
        SourceUnavailableError(
            "Source storage is temporarily unavailable"
        ),
        2,
    ]

    service = SubjectRestoreService(
        subject_repo=subject_repo,
        document_repo=document_repo,
        pdf_service=pdf_service,
    )

    with pytest.raises(
        SourceUnavailableError,
        match="temporarily unavailable",
    ):
        service.restore("subject-1")

    subject_repo.mark_restore_failed.assert_called_once_with(
        subject_id="subject-1",
        error_message=(
            "Source storage is temporarily unavailable"
        ),
    )

    result = service.restore("subject-1")

    assert result == {
        "subject_id": "subject-1",
        "status": "ACTIVE",
        "processed_documents": 1,
        "indexed_chunks": 2,
    }
    assert (
        pdf_service.rebuild_retained_document.call_args_list
        == [
            call(document),
            call(document),
        ]
    )
    subject_repo.mark_active.assert_called_once_with(
        "subject-1"
    )
