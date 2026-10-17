from types import SimpleNamespace
from unittest.mock import Mock

from app.services.postgres_chroma_reconciliation_service import (
    PostgresChromaReconciliationService,
)


def test_audit_reports_consistent_stores():
    documents = [
        SimpleNamespace(
            document_id="document-1",
            subject_id="subject-1",
        ),
        SimpleNamespace(
            document_id="document-2",
            subject_id="subject-2",
        ),
    ]

    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = (
        documents
    )

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "document-1:0",
            "document_id": "document-1",
            "subject_id": "subject-1",
        },
        {
            "chunk_id": "document-1:1",
            "document_id": "document-1",
            "subject_id": "subject-1",
        },
        {
            "chunk_id": "document-2:0",
            "document_id": "document-2",
            "subject_id": "subject-2",
        },
    ]

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    report = service.audit()

    assert report.expected_document_count == 2
    assert report.actual_chunk_count == 3
    assert report.missing_document_ids == ()
    assert report.orphan_chunk_ids == ()
    assert report.subject_mismatches == ()
    assert report.is_consistent is True


def test_audit_detects_document_missing_from_chroma():
    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        SimpleNamespace(
            document_id="document-1",
            subject_id="subject-1",
        )
    ]

    vector_store = Mock()
    vector_store.list_all_records.return_value = []

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    report = service.audit()

    assert report.expected_document_count == 1
    assert report.actual_chunk_count == 0
    assert report.missing_document_ids == (
        "document-1",
    )
    assert report.orphan_chunk_ids == ()
    assert report.subject_mismatches == ()
    assert report.is_consistent is False


def test_audit_detects_orphan_chroma_chunk():
    document_repo = Mock()
    document_repo.list_reconciliation_records.return_value = []
    document_repo.list_indexed_for_active_subjects.return_value = []

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "orphan-document:0",
            "document_id": "orphan-document",
            "subject_id": "subject-1",
        }
    ]

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    report = service.audit()

    assert report.expected_document_count == 0
    assert report.actual_chunk_count == 1
    assert report.missing_document_ids == ()
    assert report.orphan_chunk_ids == (
        "orphan-document:0",
    )
    assert report.subject_mismatches == ()
    assert report.is_consistent is False


def test_audit_detects_subject_mismatch():
    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        SimpleNamespace(
            document_id="document-1",
            subject_id="expected-subject",
        )
    ]

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "document-1:0",
            "document_id": "document-1",
            "subject_id": "wrong-subject",
        }
    ]

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    report = service.audit()

    assert report.missing_document_ids == ()
    assert report.orphan_chunk_ids == ()
    assert len(report.subject_mismatches) == 1

    mismatch = report.subject_mismatches[0]

    assert mismatch.chunk_id == "document-1:0"
    assert mismatch.document_id == "document-1"
    assert (
        mismatch.expected_subject_id
        == "expected-subject"
    )
    assert (
        mismatch.actual_subject_id
        == "wrong-subject"
    )
    assert report.is_consistent is False


def test_audit_classifies_chunk_without_document_id_as_missing_lineage():
    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = []

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "legacy-chunk-1",
            "source": "Ch1 - Tong quan DTDM.pdf",
        }
    ]

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    report = service.audit()

    assert report.missing_lineage_chunk_ids == (
        "legacy-chunk-1",
    )
    assert report.orphan_chunk_ids == ()
    assert report.is_consistent is False


def test_audit_groups_chunks_for_known_but_nonexpected_document():
    document_repo = Mock()

    document_repo.list_indexed_for_active_subjects.return_value = []

    document_repo.list_reconciliation_records.return_value = [
        SimpleNamespace(
            document_id="failed-document",
            subject_id="subject-1",
            document_status="FAILED",
            subject_status="ACTIVE",
        )
    ]

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "failed-document:0",
            "document_id": "failed-document",
            "subject_id": "subject-1",
        },
        {
            "chunk_id": "failed-document:1",
            "document_id": "failed-document",
            "subject_id": "subject-1",
        },
    ]

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    report = service.audit()

    assert report.orphan_chunk_ids == ()
    assert len(
        report.known_nonexpected_documents
    ) == 1

    unexpected = (
        report.known_nonexpected_documents[0]
    )

    assert (
        unexpected.document_id
        == "failed-document"
    )
    assert unexpected.subject_id == "subject-1"
    assert unexpected.document_status == "FAILED"
    assert unexpected.subject_status == "ACTIVE"
    assert unexpected.chunk_count == 2
    assert report.is_consistent is False
