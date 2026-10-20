import sys

from io import BytesIO, TextIOWrapper

from types import SimpleNamespace
from unittest.mock import Mock

from scripts.migrate_local_sources_to_minio import (
    main,
)


def test_main_defaults_to_dry_run_and_classifies_documents(
    monkeypatch,
    capsys,
):
    local_document = SimpleNamespace(
        document_id="local-1",
        source_uri=(
            "storage/uploads/local-1_lesson.txt"
        ),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )
    minio_document = SimpleNamespace(
        document_id="minio-1",
        source_uri=(
            "minio://cloudmentor/"
            "documents/minio-1/source.pdf"
        ),
        content_sha256="b" * 64,
        file_size_bytes=200,
    )
    legacy_document = SimpleNamespace(
        document_id="legacy-1",
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    )

    plan = SimpleNamespace(
        document_id="local-1",
        filename="lesson.txt",
        current_source_uri=(
            "storage/uploads/local-1_lesson.txt"
        ),
        target_source_uri=(
            "minio://cloudmentor/"
            "documents/local-1/source.txt"
        ),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )

    db = Mock()
    document_repo = Mock()
    document_repo.list_all.return_value = [
        legacy_document,
        local_document,
        minio_document,
    ]

    local_storage = Mock()
    minio_storage = Mock()

    migration_service = Mock()
    migration_service.plan.return_value = plan
    service_factory = Mock(
        return_value=migration_service
    )

    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "SessionLocal"
        ),
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_local_source_storage"
        ),
        Mock(return_value=local_storage),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_minio_source_storage"
        ),
        Mock(return_value=minio_storage),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "LocalSourceToMinioMigrationService"
        ),
        service_factory,
    )

    exit_code = main([])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "mode=dry-run" in output
    assert "eligible=1" in output
    assert "already_minio=1" in output
    assert "missing_metadata=1" in output
    assert "applied=0" in output
    assert "failed=0" in output

    migration_service.plan.assert_called_once_with(
        document_id="local-1"
    )
    migration_service.apply.assert_not_called()

    service_factory.assert_called_once_with(
        document_repo=document_repo,
        local_storage=local_storage,
        minio_storage=minio_storage,
    )
    db.close.assert_called_once_with()


def test_main_applies_eligible_document_when_requested(
    monkeypatch,
    capsys,
):
    document = SimpleNamespace(
        document_id="local-1",
        source_uri=(
            "storage/uploads/local-1_lesson.txt"
        ),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )
    plan = SimpleNamespace(
        document_id="local-1",
        filename="lesson.txt",
        current_source_uri=document.source_uri,
        target_source_uri=(
            "minio://cloudmentor/"
            "documents/local-1/source.txt"
        ),
        content_sha256=document.content_sha256,
        file_size_bytes=document.file_size_bytes,
    )

    db = Mock()
    document_repo = Mock()
    document_repo.list_all.return_value = [
        document
    ]

    migration_service = Mock()
    migration_service.plan.return_value = plan

    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "SessionLocal"
        ),
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_local_source_storage"
        ),
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_minio_source_storage"
        ),
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "LocalSourceToMinioMigrationService"
        ),
        Mock(return_value=migration_service),
    )

    exit_code = main(["--apply"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "mode=apply" in output
    assert "eligible=1" in output
    assert "applied=1" in output
    assert "failed=0" in output

    migration_service.apply.assert_called_once_with(
        plan
    )
    db.close.assert_called_once_with()


def test_main_continues_after_one_apply_failure(
    monkeypatch,
    capsys,
):
    first_document = SimpleNamespace(
        document_id="local-1",
        source_uri=(
            "storage/uploads/local-1_lesson.txt"
        ),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )
    second_document = SimpleNamespace(
        document_id="local-2",
        source_uri=(
            "storage/uploads/local-2_lesson.txt"
        ),
        content_sha256="b" * 64,
        file_size_bytes=200,
    )

    first_plan = SimpleNamespace(
        document_id="local-1",
        filename="lesson.txt",
        current_source_uri=(
            first_document.source_uri
        ),
        target_source_uri=(
            "minio://cloudmentor/"
            "documents/local-1/source.txt"
        ),
        content_sha256=(
            first_document.content_sha256
        ),
        file_size_bytes=(
            first_document.file_size_bytes
        ),
    )
    second_plan = SimpleNamespace(
        document_id="local-2",
        filename="lesson.txt",
        current_source_uri=(
            second_document.source_uri
        ),
        target_source_uri=(
            "minio://cloudmentor/"
            "documents/local-2/source.txt"
        ),
        content_sha256=(
            second_document.content_sha256
        ),
        file_size_bytes=(
            second_document.file_size_bytes
        ),
    )

    db = Mock()
    document_repo = Mock()
    document_repo.list_all.return_value = [
        first_document,
        second_document,
    ]

    migration_service = Mock()
    migration_service.plan.side_effect = [
        first_plan,
        second_plan,
    ]
    migration_service.apply.side_effect = [
        RuntimeError("controlled failure"),
        SimpleNamespace(
            document_id="local-2"
        ),
    ]

    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "SessionLocal"
        ),
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_local_source_storage"
        ),
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_minio_source_storage"
        ),
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "LocalSourceToMinioMigrationService"
        ),
        Mock(return_value=migration_service),
    )

    exit_code = main(["--apply"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "eligible=2" in output
    assert "applied=1" in output
    assert "failed=1" in output
    assert "document_id=local-1" in output
    assert "controlled failure" in output

    assert migration_service.apply.call_count == 2
    assert [
        item.args[0]
        for item
        in migration_service.apply.call_args_list
    ] == [
        first_plan,
        second_plan,
    ]
    db.close.assert_called_once_with()


def test_main_escapes_unicode_paths_for_limited_stdout(
    monkeypatch,
):
    source_uri = (
        "storage/uploads/"
        "document-1_Chương 5.pdf"
    )
    document = SimpleNamespace(
        document_id="local-1",
        source_uri=source_uri,
        content_sha256="a" * 64,
        file_size_bytes=100,
    )
    plan = SimpleNamespace(
        document_id="local-1",
        filename="Chương 5.pdf",
        current_source_uri=source_uri,
        target_source_uri=(
            "minio://cloudmentor/"
            "documents/local-1/source.pdf"
        ),
        content_sha256="a" * 64,
        file_size_bytes=100,
    )

    db = Mock()
    document_repo = Mock()
    document_repo.list_all.return_value = [
        document
    ]

    migration_service = Mock()
    migration_service.plan.return_value = plan

    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "SessionLocal"
        ),
        Mock(return_value=db),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "DocumentRepository"
        ),
        Mock(return_value=document_repo),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_local_source_storage"
        ),
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "create_minio_source_storage"
        ),
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        (
            "scripts.migrate_local_sources_to_minio."
            "LocalSourceToMinioMigrationService"
        ),
        Mock(return_value=migration_service),
    )

    output_buffer = BytesIO()
    limited_stdout = TextIOWrapper(
        output_buffer,
        encoding="cp1252",
        errors="strict",
    )
    monkeypatch.setattr(
        sys,
        "stdout",
        limited_stdout,
    )

    exit_code = main([])
    limited_stdout.flush()

    output = output_buffer.getvalue().decode(
        "cp1252"
    )

    assert exit_code == 0
    assert (
        r"source=storage/uploads/"
        r"document-1_Ch\u01b0\u01a1ng 5.pdf"
        in output
    )
    assert "eligible=1" in output
    assert "failed=0" in output
    migration_service.apply.assert_not_called()
