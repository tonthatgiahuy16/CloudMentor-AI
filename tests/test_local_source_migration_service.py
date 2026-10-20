import pytest
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.local_source_migration_service import (
    LocalSourceToMinioMigrationService,
)
from app.storage.source_storage import StoredSource

def test_plan_valid_local_source_without_mutating_state():
    source_data = b"canonical local source"
    document = SimpleNamespace(
        document_id="document-1",
        filename="lesson.txt",
        source_uri=(
            "storage/uploads/"
            "document-1_lesson.txt"
        ),
        content_sha256=(
            sha256(source_data).hexdigest()
        ),
        file_size_bytes=len(source_data),
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = document

    local_storage = Mock()
    local_storage.read_bytes.return_value = (
        source_data
    )

    minio_storage = Mock()
    minio_storage.source_uri_for.return_value = (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )

    service = (
        LocalSourceToMinioMigrationService(
            document_repo=document_repo,
            local_storage=local_storage,
            minio_storage=minio_storage,
        )
    )

    plan = service.plan(
        document_id=document.document_id
    )

    assert plan.document_id == document.document_id
    assert plan.filename == document.filename
    assert (
        plan.current_source_uri
        == document.source_uri
    )
    assert plan.target_source_uri == (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )
    assert (
        plan.content_sha256
        == document.content_sha256
    )
    assert (
        plan.file_size_bytes
        == document.file_size_bytes
    )

    local_storage.read_bytes.assert_called_once_with(
        document.source_uri
    )
    minio_storage.source_uri_for.assert_called_once_with(
        document_id=document.document_id,
        filename=document.filename,
    )

    minio_storage.store.assert_not_called()
    (
        document_repo
        .replace_source_uri_if_matches
        .assert_not_called()
    )


def test_apply_stores_verifies_and_replaces_source_uri():
    source_data = b"canonical local source"
    content_sha256 = (
        sha256(source_data).hexdigest()
    )
    local_uri = (
        "storage/uploads/"
        "document-1_lesson.txt"
    )
    target_uri = (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )

    document = SimpleNamespace(
        document_id="document-1",
        filename="lesson.txt",
        source_uri=local_uri,
        content_sha256=content_sha256,
        file_size_bytes=len(source_data),
    )
    migrated_document = SimpleNamespace(
        document_id=document.document_id,
        source_uri=target_uri,
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = (
        document
    )
    document_repo.replace_source_uri_if_matches.return_value = (
        migrated_document
    )

    local_storage = Mock()
    local_storage.read_bytes.return_value = (
        source_data
    )

    minio_storage = Mock()
    minio_storage.source_uri_for.return_value = (
        target_uri
    )
    minio_storage.store.return_value = StoredSource(
        source_uri=target_uri,
        content_sha256=content_sha256,
        file_size_bytes=len(source_data),
    )
    minio_storage.read_bytes.return_value = (
        source_data
    )

    service = (
        LocalSourceToMinioMigrationService(
            document_repo=document_repo,
            local_storage=local_storage,
            minio_storage=minio_storage,
        )
    )
    plan = service.plan(
        document_id=document.document_id
    )

    document_repo.reset_mock()
    local_storage.reset_mock()
    minio_storage.reset_mock()

    result = service.apply(plan)

    assert result is migrated_document

    document_repo.get_by_id.assert_called_once_with(
        document.document_id
    )
    local_storage.read_bytes.assert_called_once_with(
        local_uri
    )
    minio_storage.store.assert_called_once_with(
        document_id=document.document_id,
        filename=document.filename,
        data=source_data,
    )
    minio_storage.read_bytes.assert_called_once_with(
        target_uri
    )
    (
        document_repo
        .replace_source_uri_if_matches
        .assert_called_once_with(
            document_id=document.document_id,
            expected_source_uri=local_uri,
            expected_content_sha256=content_sha256,
            expected_file_size_bytes=len(
                source_data
            ),
            new_source_uri=target_uri,
        )
    )


def test_apply_rejects_database_change_before_minio_write():
    source_data = b"canonical local source"
    document = SimpleNamespace(
        document_id="document-1",
        filename="lesson.txt",
        source_uri=(
            "storage/uploads/"
            "document-1_lesson.txt"
        ),
        content_sha256=(
            sha256(source_data).hexdigest()
        ),
        file_size_bytes=len(source_data),
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = (
        document
    )

    local_storage = Mock()
    local_storage.read_bytes.return_value = (
        source_data
    )

    minio_storage = Mock()
    minio_storage.source_uri_for.return_value = (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )

    service = (
        LocalSourceToMinioMigrationService(
            document_repo=document_repo,
            local_storage=local_storage,
            minio_storage=minio_storage,
        )
    )
    plan = service.plan(
        document_id=document.document_id
    )

    document.source_uri = (
        "storage/uploads/replaced.txt"
    )

    document_repo.reset_mock()
    local_storage.reset_mock()
    minio_storage.reset_mock()

    with pytest.raises(
        RuntimeError,
        match="Document source changed after planning",
    ):
        service.apply(plan)

    local_storage.read_bytes.assert_not_called()
    minio_storage.store.assert_not_called()
    (
        document_repo
        .replace_source_uri_if_matches
        .assert_not_called()
    )


def test_apply_rejects_local_source_changed_after_plan():
    original_data = b"canonical local source"
    changed_data = b"changed local source"

    document = SimpleNamespace(
        document_id="document-1",
        filename="lesson.txt",
        source_uri=(
            "storage/uploads/"
            "document-1_lesson.txt"
        ),
        content_sha256=(
            sha256(original_data).hexdigest()
        ),
        file_size_bytes=len(original_data),
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = (
        document
    )

    local_storage = Mock()
    local_storage.read_bytes.return_value = (
        original_data
    )

    minio_storage = Mock()
    minio_storage.source_uri_for.return_value = (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )

    service = (
        LocalSourceToMinioMigrationService(
            document_repo=document_repo,
            local_storage=local_storage,
            minio_storage=minio_storage,
        )
    )
    plan = service.plan(
        document_id=document.document_id
    )

    local_storage.reset_mock()
    minio_storage.reset_mock()
    document_repo.reset_mock()

    local_storage.read_bytes.return_value = (
        changed_data
    )

    with pytest.raises(
        RuntimeError,
        match="Local source changed after planning",
    ):
        service.apply(plan)

    minio_storage.store.assert_not_called()
    (
        document_repo
        .replace_source_uri_if_matches
        .assert_not_called()
    )


def test_apply_rejects_failed_minio_readback():
    source_data = b"canonical local source"
    corrupted_data = b"corrupted local source"
    content_sha256 = (
        sha256(source_data).hexdigest()
    )
    local_uri = (
        "storage/uploads/"
        "document-1_lesson.txt"
    )
    target_uri = (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )

    document = SimpleNamespace(
        document_id="document-1",
        filename="lesson.txt",
        source_uri=local_uri,
        content_sha256=content_sha256,
        file_size_bytes=len(source_data),
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = (
        document
    )

    local_storage = Mock()
    local_storage.read_bytes.return_value = (
        source_data
    )

    minio_storage = Mock()
    minio_storage.source_uri_for.return_value = (
        target_uri
    )

    service = (
        LocalSourceToMinioMigrationService(
            document_repo=document_repo,
            local_storage=local_storage,
            minio_storage=minio_storage,
        )
    )
    plan = service.plan(
        document_id=document.document_id
    )

    document_repo.reset_mock()
    local_storage.reset_mock()
    minio_storage.reset_mock()

    minio_storage.store.return_value = StoredSource(
        source_uri=target_uri,
        content_sha256=content_sha256,
        file_size_bytes=len(source_data),
    )
    minio_storage.read_bytes.return_value = (
        corrupted_data
    )

    with pytest.raises(
        RuntimeError,
        match="Stored source verification failed",
    ):
        service.apply(plan)

    minio_storage.store.assert_called_once()
    minio_storage.read_bytes.assert_called_once_with(
        target_uri
    )
    (
        document_repo
        .replace_source_uri_if_matches
        .assert_not_called()
    )
