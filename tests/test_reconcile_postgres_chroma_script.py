from types import SimpleNamespace
from unittest.mock import Mock

from scripts.reconcile_postgres_chroma import main


def test_main_reports_drift_and_returns_nonzero(
    monkeypatch,
    capsys,
):
    report = SimpleNamespace(
        expected_document_count=2,
        actual_chunk_count=6,
        missing_document_ids=("document-2",),
        missing_lineage_chunk_ids=(
            "legacy:0",
            "legacy:1",
        ),
        orphan_chunk_ids=("unknown:0",),
        known_nonexpected_documents=(
            SimpleNamespace(
                document_id="failed-document",
                subject_id="subject-1",
                document_status="FAILED",
                subject_status="ACTIVE",
                chunk_count=2,
            ),
        ),
        subject_mismatches=(
            SimpleNamespace(
                chunk_id="document-1:0",
                document_id="document-1",
                expected_subject_id="subject-1",
                actual_subject_id="wrong-subject",
            ),
        ),
        is_consistent=False,
    )

    db = Mock()
    document_repo = Mock()
    vector_store = Mock()
    service = Mock()
    service.audit.return_value = report

    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.VectorStore",
        Mock(return_value=vector_store),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "PostgresChromaReconciliationService"
        ),
        Mock(return_value=service),
    )

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Expected documents: 2" in output
    assert "Chroma chunks: 6" in output
    assert "Missing indexed documents: 1" in output
    assert "Missing document: document-2" in output
    assert "Missing lineage chunks: 2" in output
    assert "Unknown document chunks: 1" in output
    assert "Known non-expected documents: 1" in output
    assert (
        "Known non-expected document: "
        "failed-document "
        "document_status=FAILED "
        "subject_status=ACTIVE "
        "subject=subject-1 "
        "chunks=2"
        in output
    )
    assert "Subject mismatches: 1" in output
    assert (
        "Subject mismatch: document-1:0"
        in output
    )
    assert "legacy:0" not in output
    assert "unknown:0" not in output
    assert "Drift detected." in output

    service.audit.assert_called_once_with()
    db.close.assert_called_once_with()


def test_main_reports_consistent_stores(
    monkeypatch,
    capsys,
):
    report = SimpleNamespace(
        expected_document_count=2,
        actual_chunk_count=12,
        missing_document_ids=(),
        orphan_chunk_ids=(),
        missing_lineage_chunk_ids=(),
        known_nonexpected_documents=(),
        subject_mismatches=(),
        is_consistent=True,
    )

    db = Mock()
    document_repo = Mock()
    vector_store = Mock()
    service = Mock()
    service.audit.return_value = report

    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.VectorStore",
        Mock(return_value=vector_store),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "PostgresChromaReconciliationService"
        ),
        Mock(return_value=service),
    )

    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Expected documents: 2" in output
    assert "Chroma chunks: 12" in output
    assert "Stores are consistent." in output
    assert "Drift detected." not in output

    service.audit.assert_called_once_with()
    db.close.assert_called_once_with()


def test_main_repair_defaults_to_dry_run_and_logs_plan(
    monkeypatch,
    capsys,
):
    plan = SimpleNamespace(
        delete_orphan_chunk_ids=(
            "orphan-document:0",
        ),
        rebuild_document_ids=(
            "indexed-but-missing",
        ),
        is_empty=False,
    )

    db = Mock()
    document_repo = Mock()
    vector_store = Mock()
    service = Mock()
    service.plan_repair.return_value = plan

    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.VectorStore",
        Mock(return_value=vector_store),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "PostgresChromaReconciliationService"
        ),
        Mock(return_value=service),
    )

    exit_code = main(["--repair"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "repair_mode=dry-run" in output
    assert (
        "repair_action=delete_orphan_chunk "
        "target_id=orphan-document:0 "
        "status=planned"
        in output
    )
    assert (
        "repair_action=rebuild_document "
        "target_id=indexed-but-missing "
        "status=planned"
        in output
    )

    service.plan_repair.assert_called_once_with()
    service.apply_repair.assert_not_called()
    db.close.assert_called_once_with()


def test_main_apply_repair_logs_applied_actions(
    monkeypatch,
    capsys,
):
    result = SimpleNamespace(
        deleted_orphan_chunk_ids=(
            "orphan-document:0",
        ),
        rebuilt_document_ids=(
            "indexed-but-missing",
        ),
        rebuilt_chunk_count=3,
        failed_actions=(),
    )

    db = Mock()
    document_repo = Mock()
    vector_store = Mock()
    service = Mock()
    service.apply_repair.return_value = result

    source_storage = Mock()
    pdf_service = Mock()

    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.VectorStore",
        Mock(return_value=vector_store),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "PostgresChromaReconciliationService"
        ),
        Mock(return_value=service),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.create_source_storage",
        Mock(return_value=source_storage),
        raising=False,
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.PDFService",
        Mock(return_value=pdf_service),
        raising=False,
    )

    exit_code = main(["--repair", "--apply"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "repair_mode=apply" in output
    assert (
        "repair_action=delete_orphan_chunk "
        "target_id=orphan-document:0 "
        "status=applied"
        in output
    )
    assert (
        "repair_action=rebuild_document "
        "target_id=indexed-but-missing "
        "status=applied"
        in output
    )
    assert (
        "repair_summary "
        "deleted_orphan_chunks=1 "
        "rebuilt_documents=1 "
        "rebuilt_chunks=3"
        in output
    )

    service.plan_repair.assert_not_called()
    service.apply_repair.assert_called_once_with(
        document_rebuilder=(
            pdf_service.rebuild_retained_document
        )
    )
    db.close.assert_called_once_with()


def test_main_apply_repair_logs_failed_actions_and_returns_nonzero(
    monkeypatch,
    capsys,
):
    result = SimpleNamespace(
        deleted_orphan_chunk_ids=(),
        rebuilt_document_ids=("rebuild-succeeds",),
        rebuilt_chunk_count=2,
        failed_actions=(
            SimpleNamespace(
                action="rebuild_document",
                target_id="rebuild-fails",
                error_message="retained source unavailable",
            ),
        ),
    )

    db = Mock()
    document_repo = Mock()
    vector_store = Mock()
    service = Mock()
    service.apply_repair.return_value = result
    source_storage = Mock()
    pdf_service = Mock()

    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.SessionLocal",
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.DocumentRepository",
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.VectorStore",
        Mock(return_value=vector_store),
    )
    monkeypatch.setattr(
        (
            "scripts.reconcile_postgres_chroma."
            "PostgresChromaReconciliationService"
        ),
        Mock(return_value=service),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.create_source_storage",
        Mock(return_value=source_storage),
    )
    monkeypatch.setattr(
        "scripts.reconcile_postgres_chroma.PDFService",
        Mock(return_value=pdf_service),
    )

    exit_code = main(["--repair", "--apply"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert (
        "repair_action=rebuild_document "
        "target_id=rebuild-succeeds "
        "status=applied"
        in output
    )
    assert (
        "repair_action=rebuild_document "
        "target_id=rebuild-fails "
        "status=failed "
        "error=retained source unavailable"
        in output
    )

    service.apply_repair.assert_called_once_with(
        document_rebuilder=(
            pdf_service.rebuild_retained_document
        )
    )
    db.close.assert_called_once_with()
