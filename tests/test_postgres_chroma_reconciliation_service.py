from types import SimpleNamespace
from unittest.mock import Mock, call

from app.services.postgres_chroma_reconciliation_service import (
    PostgresChromaReconciliationService,
    ReconciliationRepairFailure,
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


def test_plan_repair_is_dry_run_for_safe_actions_only():
    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        SimpleNamespace(
            document_id="indexed-but-missing",
            subject_id="subject-1",
        )
    ]
    document_repo.list_reconciliation_records.return_value = []

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

    plan = service.plan_repair()

    assert plan.delete_orphan_chunk_ids == (
        "orphan-document:0",
    )
    assert plan.rebuild_document_ids == (
        "indexed-but-missing",
    )

    vector_store.delete_by_chunk_ids.assert_not_called()


def test_apply_repair_deletes_orphans_and_rebuilds_missing_documents():
    indexed_document = SimpleNamespace(
        document_id="indexed-but-missing",
        subject_id="subject-1",
        status="INDEXED",
    )

    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        indexed_document
    ]
    document_repo.list_reconciliation_records.return_value = []

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "orphan-document:0",
            "document_id": "orphan-document",
            "subject_id": "subject-1",
        }
    ]
    vector_store.delete_by_chunk_ids.return_value = 1

    rebuild_document = Mock(return_value=3)

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    result = service.apply_repair(
        document_rebuilder=rebuild_document,
    )

    vector_store.delete_by_chunk_ids.assert_called_once_with(
        ["orphan-document:0"]
    )
    rebuild_document.assert_called_once_with(
        indexed_document
    )

    assert result.deleted_orphan_chunk_ids == (
        "orphan-document:0",
    )
    assert result.rebuilt_document_ids == (
        "indexed-but-missing",
    )
    assert result.rebuilt_chunk_count == 3


def test_apply_repair_is_no_op_after_drift_is_repaired():
    indexed_document = SimpleNamespace(
        document_id="indexed-but-missing",
        subject_id="subject-1",
        status="INDEXED",
    )

    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        indexed_document
    ]
    document_repo.list_reconciliation_records.return_value = []

    vector_store = Mock()
    vector_store.list_all_records.side_effect = [
        [
            {
                "chunk_id": "orphan-document:0",
                "document_id": "orphan-document",
                "subject_id": "subject-1",
            }
        ],
        [
            {
                "chunk_id": "indexed-but-missing:0",
                "document_id": "indexed-but-missing",
                "subject_id": "subject-1",
            }
        ],
    ]
    vector_store.delete_by_chunk_ids.return_value = 1

    rebuild_document = Mock(return_value=3)

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    first_result = service.apply_repair(
        document_rebuilder=rebuild_document,
    )
    second_result = service.apply_repair(
        document_rebuilder=rebuild_document,
    )

    assert first_result.deleted_orphan_chunk_ids == (
        "orphan-document:0",
    )
    assert first_result.rebuilt_document_ids == (
        "indexed-but-missing",
    )

    assert second_result.deleted_orphan_chunk_ids == ()
    assert second_result.rebuilt_document_ids == ()
    assert second_result.rebuilt_chunk_count == 0

    vector_store.delete_by_chunk_ids.assert_called_once_with(
        ["orphan-document:0"]
    )
    rebuild_document.assert_called_once_with(
        indexed_document
    )


def test_apply_repair_records_failed_rebuild_and_continues():
    failed_document = SimpleNamespace(
        document_id="rebuild-fails",
        subject_id="subject-1",
        status="INDEXED",
    )
    successful_document = SimpleNamespace(
        document_id="rebuild-succeeds",
        subject_id="subject-1",
        status="INDEXED",
    )

    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        failed_document,
        successful_document,
    ]

    vector_store = Mock()
    vector_store.list_all_records.return_value = []

    rebuild_document = Mock(
        side_effect=[
            RuntimeError("retained source unavailable"),
            2,
        ]
    )

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    result = service.apply_repair(
        document_rebuilder=rebuild_document,
    )

    assert result.rebuilt_document_ids == (
        "rebuild-succeeds",
    )
    assert result.rebuilt_chunk_count == 2
    assert result.failed_actions == (
        ReconciliationRepairFailure(
            action="rebuild_document",
            target_id="rebuild-fails",
            error_message="retained source unavailable",
        ),
    )

    assert rebuild_document.call_args_list == [
        call(failed_document),
        call(successful_document),
    ]


def test_apply_repair_records_failed_orphan_delete_and_continues():
    indexed_document = SimpleNamespace(
        document_id="indexed-but-missing",
        subject_id="subject-1",
        status="INDEXED",
    )

    document_repo = Mock()
    document_repo.list_indexed_for_active_subjects.return_value = [
        indexed_document
    ]
    document_repo.list_reconciliation_records.return_value = []

    vector_store = Mock()
    vector_store.list_all_records.return_value = [
        {
            "chunk_id": "orphan-document:0",
            "document_id": "orphan-document",
            "subject_id": "subject-1",
        }
    ]
    vector_store.delete_by_chunk_ids.side_effect = RuntimeError(
        "Chroma unavailable"
    )

    rebuild_document = Mock(return_value=2)

    service = PostgresChromaReconciliationService(
        document_repo=document_repo,
        vector_store=vector_store,
    )

    result = service.apply_repair(
        document_rebuilder=rebuild_document,
    )

    assert result.deleted_orphan_chunk_ids == ()
    assert result.rebuilt_document_ids == (
        "indexed-but-missing",
    )
    assert result.rebuilt_chunk_count == 2
    assert result.failed_actions == (
        ReconciliationRepairFailure(
            action="delete_orphan_chunk",
            target_id="orphan-document:0",
            error_message="Chroma unavailable",
        ),
    )

    vector_store.delete_by_chunk_ids.assert_called_once_with(
        ["orphan-document:0"]
    )
    rebuild_document.assert_called_once_with(indexed_document)
