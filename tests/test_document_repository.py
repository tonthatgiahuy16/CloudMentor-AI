from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db_models.document import Document
from app.core.database import Base
from app.db_models.subject import Subject
from app.repos.document_repository import (
    ActiveDocumentConflictError,
    DocumentRepository,
)
from unittest.mock import Mock


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    db = TestingSession()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def repository(db_session):
    return DocumentRepository(db_session)


@pytest.fixture
def document(db_session, repository):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )

    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)

    return repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
    )


def test_get_by_id_returns_document(repository, document):
    result = repository.get_by_id(
        document.document_id
    )

    assert result is not None
    assert result.document_id == document.document_id
    assert result.filename == "lesson.pdf"


def test_get_by_id_returns_none_when_missing(repository):
    result = repository.get_by_id(
        str(uuid4())
    )

    assert result is None


def test_mark_deleted_updates_status_and_timestamp(
    repository,
    document,
):
    result = repository.mark_deleted(
        document.document_id
    )

    assert result.status == "DELETED"
    assert result.deleted_at is not None


def test_mark_deleted_is_idempotent(
    repository,
    document,
):
    first_result = repository.mark_deleted(
        document.document_id
    )

    first_deleted_at = first_result.deleted_at

    second_result = repository.mark_deleted(
        document.document_id
    )

    assert second_result.status == "DELETED"
    assert second_result.deleted_at == first_deleted_at


def test_mark_deleted_raises_when_document_missing(
    repository,
):
    with pytest.raises(
        RuntimeError,
        match="Document not found",
    ):
        repository.mark_deleted(
            str(uuid4())
        )


def test_list_active_excludes_deleted_documents(
    repository,
    document,
):
    active_document = repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="chapter-2.pdf",
        file_type="pdf",
        chapter=2,
    )

    repository.mark_deleted(
        document.document_id
    )

    results = repository.list_active()

    assert {
        result.document_id
        for result in results
    } == {active_document.document_id}


def test_create_persists_source_metadata(
    db_session,
    repository,
):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )

    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)

    result = repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
        source_uri="storage/uploads/document-id_lesson.pdf",
        content_sha256="a" * 64,
        file_size_bytes=2048,
    )

    assert result.source_uri == (
        "storage/uploads/document-id_lesson.pdf"
    )
    assert result.content_sha256 == "a" * 64
    assert result.file_size_bytes == 2048


def test_attach_source_metadata_to_legacy_document(
    repository,
    document,
):
    result = repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri=(
            "storage/uploads/"
            f"{document.document_id}_lesson.pdf"
        ),
        content_sha256="d" * 64,
        file_size_bytes=1061675,
    )

    assert result.document_id == document.document_id
    assert result.source_uri == (
        "storage/uploads/"
        f"{document.document_id}_lesson.pdf"
    )
    assert result.content_sha256 == "d" * 64
    assert result.file_size_bytes == 1061675


def test_attach_source_metadata_rejects_conflict(
    repository,
    document,
):
    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri="storage/uploads/original.pdf",
        content_sha256="a" * 64,
        file_size_bytes=100,
    )

    with pytest.raises(
        RuntimeError,
        match="Document source metadata conflict",
    ):
        repository.attach_source_metadata(
            document_id=document.document_id,
            source_uri="storage/uploads/different.pdf",
            content_sha256="b" * 64,
            file_size_bytes=200,
        )

    persisted = repository.get_by_id(
        document.document_id
    )

    assert persisted is not None
    assert persisted.source_uri == (
        "storage/uploads/original.pdf"
    )
    assert persisted.content_sha256 == "a" * 64
    assert persisted.file_size_bytes == 100


def test_attach_source_metadata_is_idempotent(
    repository,
    document,
):
    metadata = {
        "document_id": document.document_id,
        "source_uri": "storage/uploads/original.pdf",
        "content_sha256": "a" * 64,
        "file_size_bytes": 100,
    }

    first_result = repository.attach_source_metadata(
        **metadata
    )
    second_result = repository.attach_source_metadata(
        **metadata
    )

    assert first_result.document_id == document.document_id
    assert second_result.document_id == document.document_id
    assert second_result.source_uri == metadata["source_uri"]
    assert (
        second_result.content_sha256
        == metadata["content_sha256"]
    )
    assert (
        second_result.file_size_bytes
        == metadata["file_size_bytes"]
    )


def test_attach_source_metadata_rejects_missing_document(
    repository,
):
    missing_document_id = str(uuid4())

    with pytest.raises(
        RuntimeError,
        match="Document not found",
    ):
        repository.attach_source_metadata(
            document_id=missing_document_id,
            source_uri="storage/uploads/missing.pdf",
            content_sha256="a" * 64,
            file_size_bytes=100,
        )

    assert repository.get_by_id(missing_document_id) is None


def test_replace_source_uri_if_matches_preserves_document_state(
    repository,
    document,
):
    local_uri = (
        "storage/uploads/"
        f"{document.document_id}_lesson.pdf"
    )
    content_sha256 = "a" * 64
    file_size_bytes = 2048

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri=local_uri,
        content_sha256=content_sha256,
        file_size_bytes=file_size_bytes,
    )

    original_status = document.status
    original_chapter = document.chapter

    result = (
        repository.replace_source_uri_if_matches(
            document_id=document.document_id,
            expected_source_uri=local_uri,
            expected_content_sha256=content_sha256,
            expected_file_size_bytes=file_size_bytes,
            new_source_uri=(
                "minio://cloudmentor/"
                f"documents/{document.document_id}/"
                "source.pdf"
            ),
        )
    )

    assert result.document_id == document.document_id
    assert result.source_uri.startswith(
        "minio://cloudmentor/"
    )
    assert result.content_sha256 == content_sha256
    assert result.file_size_bytes == file_size_bytes
    assert result.status == original_status
    assert result.chapter == original_chapter


@pytest.mark.parametrize(
    (
        "mismatched_argument",
        "mismatched_value",
    ),
    [
        (
            "expected_source_uri",
            "storage/uploads/other.pdf",
        ),
        (
            "expected_content_sha256",
            "b" * 64,
        ),
        (
            "expected_file_size_bytes",
            999,
        ),
    ],
)
def test_replace_source_uri_if_matches_rejects_stale_snapshot(
    repository,
    document,
    mismatched_argument,
    mismatched_value,
):
    local_uri = (
        "storage/uploads/"
        f"{document.document_id}_lesson.pdf"
    )
    content_sha256 = "a" * 64
    file_size_bytes = 2048

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri=local_uri,
        content_sha256=content_sha256,
        file_size_bytes=file_size_bytes,
    )

    arguments = {
        "document_id": document.document_id,
        "expected_source_uri": local_uri,
        "expected_content_sha256": content_sha256,
        "expected_file_size_bytes": file_size_bytes,
        "new_source_uri": (
            "minio://cloudmentor/"
            f"documents/{document.document_id}/"
            "source.pdf"
        ),
    }
    arguments[mismatched_argument] = (
        mismatched_value
    )

    with pytest.raises(
        RuntimeError,
        match="Document source changed during migration",
    ):
        repository.replace_source_uri_if_matches(
            **arguments
        )

    persisted = repository.get_by_id(
        document.document_id
    )

    assert persisted is not None
    assert persisted.source_uri == local_uri
    assert persisted.content_sha256 == content_sha256
    assert persisted.file_size_bytes == file_size_bytes


def test_replace_source_uri_rolls_back_when_commit_fails(
    db_session,
    repository,
    document,
    monkeypatch,
):
    local_uri = (
        "storage/uploads/"
        f"{document.document_id}_lesson.pdf"
    )
    content_sha256 = "a" * 64
    file_size_bytes = 2048

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri=local_uri,
        content_sha256=content_sha256,
        file_size_bytes=file_size_bytes,
    )

    rollback = Mock(
        wraps=db_session.rollback
    )
    monkeypatch.setattr(
        db_session,
        "rollback",
        rollback,
    )
    monkeypatch.setattr(
        db_session,
        "commit",
        Mock(
            side_effect=RuntimeError(
                "controlled commit failure"
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="controlled commit failure",
    ):
        repository.replace_source_uri_if_matches(
            document_id=document.document_id,
            expected_source_uri=local_uri,
            expected_content_sha256=content_sha256,
            expected_file_size_bytes=file_size_bytes,
            new_source_uri=(
                "minio://cloudmentor/"
                f"documents/{document.document_id}/"
                "source.pdf"
            ),
        )

    rollback.assert_called_once_with()


def test_get_active_by_subject_and_sha256_returns_match(
    db_session,
    repository,
):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )

    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)

    content_sha256 = "b" * 64

    created = repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
        source_uri="storage/uploads/lesson.pdf",
        content_sha256=content_sha256,
        file_size_bytes=2048,
    )

    result = (
        repository.get_active_by_subject_and_sha256(
            subject_id=subject.subject_id,
            content_sha256=content_sha256,
        )
    )

    assert result is not None
    assert result.document_id == created.document_id


def test_get_active_by_subject_and_sha256_is_subject_scoped(
    db_session,
    repository,
):
    first_subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )
    second_subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )

    db_session.add_all([first_subject, second_subject])
    db_session.commit()

    content_sha256 = "c" * 64

    repository.create(
        document_id=str(uuid4()),
        subject_id=first_subject.subject_id,
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
        source_uri="storage/uploads/lesson.pdf",
        content_sha256=content_sha256,
        file_size_bytes=2048,
    )

    result = repository.get_active_by_subject_and_sha256(
        subject_id=second_subject.subject_id,
        content_sha256=content_sha256,
    )

    assert result is None

def test_get_active_by_subject_and_sha256_excludes_deleted(
    db_session,
    repository,
):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )

    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)

    content_sha256 = "d" * 64

    created = repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
        source_uri="storage/uploads/lesson.pdf",
        content_sha256=content_sha256,
        file_size_bytes=2048,
    )

    repository.mark_deleted(created.document_id)

    result = repository.get_active_by_subject_and_sha256(
        subject_id=subject.subject_id,
        content_sha256=content_sha256,
    )

    assert result is None


def test_get_active_by_subject_and_sha256_requires_matching_hash(
    db_session,
    repository,
):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )

    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)

    repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="lesson.pdf",
        file_type="pdf",
        chapter=1,
        source_uri="storage/uploads/lesson.pdf",
        content_sha256="e" * 64,
        file_size_bytes=2048,
    )

    result = repository.get_active_by_subject_and_sha256(
        subject_id=subject.subject_id,
        content_sha256="f" * 64,
    )

    assert result is None


def test_mark_processing_clears_previous_failure(
    repository,
    document,
):
    repository.mark_failed(
        document_id=document.document_id,
        failed_stage="EXTRACT",
        error_message="Controlled extraction failure",
    )

    result = repository.mark_processing(
        document.document_id
    )

    assert result.status == "PROCESSING"
    assert result.failed_stage is None
    assert result.error_message is None


def test_mark_processing_records_attempt_metadata(
    repository,
    document,
):
    result = repository.mark_processing(
        document.document_id
    )

    assert result.status == "PROCESSING"
    assert result.processing_attempt_count == 1
    assert result.last_processing_started_at is not None
    assert result.last_processing_heartbeat_at is not None


def test_record_processing_heartbeat_updates_current_stage(
    repository,
    document,
):
    processing = repository.mark_processing(
        document.document_id
    )

    previous_heartbeat = (
        processing.last_processing_heartbeat_at
    )

    result = (
        repository.record_processing_heartbeat(
            document_id=document.document_id,
            stage="EXTRACT",
        )
    )

    assert result.status == "PROCESSING"
    assert result.current_stage == "EXTRACT"
    assert (
        result.last_processing_heartbeat_at
        is not None
    )
    assert (
        result.last_processing_heartbeat_at
        >= previous_heartbeat
    )


def test_mark_failed_clears_current_processing_stage(
    repository,
    document,
):
    repository.mark_processing(
        document.document_id
    )
    processing = (
        repository.record_processing_heartbeat(
            document_id=document.document_id,
            stage="TRANSFORM",
        )
    )

    previous_heartbeat = (
        processing.last_processing_heartbeat_at
    )

    result = repository.mark_failed(
        document_id=document.document_id,
        failed_stage="TRANSFORM",
        error_message="Controlled failure",
    )

    assert result.status == "FAILED"
    assert result.current_stage is None
    assert result.failed_stage == "TRANSFORM"
    assert result.error_message == "Controlled failure"
    assert (
        result.last_processing_heartbeat_at
        == previous_heartbeat
    )


def test_mark_indexed_clears_current_processing_stage(
    repository,
    document,
):
    repository.mark_processing(
        document.document_id
    )
    repository.record_processing_heartbeat(
        document_id=document.document_id,
        stage="INDEX",
    )

    result = repository.mark_indexed(
        document.document_id
    )

    assert result.status == "INDEXED"
    assert result.current_stage is None
    assert result.indexed_at is not None
    assert result.failed_stage is None
    assert result.error_message is None


def test_mark_deleted_clears_current_processing_stage(
    repository,
    document,
):
    repository.mark_processing(
        document.document_id
    )
    repository.record_processing_heartbeat(
        document_id=document.document_id,
        stage="CHUNK",
    )

    result = repository.mark_deleted(
        document.document_id
    )

    assert result.status == "DELETED"
    assert result.current_stage is None
    assert result.deleted_at is not None


def test_record_processing_heartbeat_rejects_invalid_stage(
    repository,
    document,
):
    repository.mark_processing(
        document.document_id
    )

    with pytest.raises(
        ValueError,
        match="Invalid processing stage",
    ):
        repository.record_processing_heartbeat(
            document_id=document.document_id,
            stage="LOAD",
        )


def test_record_processing_heartbeat_requires_processing_status(
    repository,
    document,
):
    with pytest.raises(
        RuntimeError,
        match="Document is not processing",
    ):
        repository.record_processing_heartbeat(
            document_id=document.document_id,
            stage="EXTRACT",
        )

    unchanged = repository.get_by_id(
        document.document_id
    )

    assert unchanged.status == "UPLOADED"
    assert unchanged.current_stage is None
    assert (
        unchanged.last_processing_heartbeat_at
        is None
    )


def test_list_stale_ingestions_finds_expired_processing_document(
    db_session,
    repository,
    document,
):
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=15)

    stale_document = repository.mark_processing(
        document.document_id
    )
    stale_document.last_processing_heartbeat_at = (
        now - timedelta(minutes=30)
    )

    fresh_document = repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="fresh.pdf",
        file_type="pdf",
        chapter=2,
    )
    fresh_document = repository.mark_processing(
        fresh_document.document_id
    )
    fresh_document.last_processing_heartbeat_at = (
        now - timedelta(minutes=5)
    )

    db_session.commit()

    result = repository.list_stale_ingestions(
        stale_before=stale_before,
    )

    assert [
        item.document_id
        for item in result
    ] == [stale_document.document_id]


def test_list_stale_ingestions_finds_expired_uploaded_document(
    db_session,
    repository,
    document,
):
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=15)

    document.uploaded_at = (
        now - timedelta(minutes=30)
    )

    fresh_document = repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="fresh-upload.pdf",
        file_type="pdf",
        chapter=2,
    )
    fresh_document.uploaded_at = (
        now - timedelta(minutes=5)
    )

    db_session.commit()

    result = repository.list_stale_ingestions(
        stale_before=stale_before,
    )

    assert [
        item.document_id
        for item in result
    ] == [document.document_id]


def test_list_stale_ingestions_uses_start_time_when_heartbeat_missing(
    db_session,
    repository,
    document,
):
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=15)

    processing = repository.mark_processing(
        document.document_id
    )
    processing.last_processing_started_at = (
        now - timedelta(minutes=30)
    )
    processing.last_processing_heartbeat_at = None

    db_session.commit()

    result = repository.list_stale_ingestions(
        stale_before=stale_before,
    )

    assert [
        item.document_id
        for item in result
    ] == [document.document_id]


@pytest.mark.parametrize(
    "status",
    [
        "FAILED",
        "INDEXED",
        "DELETED",
    ],
)
def test_list_stale_ingestions_excludes_other_statuses(
    db_session,
    repository,
    document,
    status,
):
    now = datetime.now(timezone.utc)

    document.status = status
    document.uploaded_at = (
        now - timedelta(hours=1)
    )
    document.last_processing_started_at = (
        now - timedelta(hours=1)
    )
    document.last_processing_heartbeat_at = (
        now - timedelta(hours=1)
    )

    db_session.commit()

    result = repository.list_stale_ingestions(
        stale_before=(
            now - timedelta(minutes=15)
        ),
    )

    assert result == []


def test_list_active_by_subject_is_scoped_and_excludes_deleted(
    db_session,
    repository,
):
    subject_a = Subject(
        subject_id=str(uuid4()),
        name="Data Engineering",
    )
    subject_b = Subject(
        subject_id=str(uuid4()),
        name="Cloud Computing",
    )

    db_session.add_all([
        subject_a,
        subject_b,
    ])
    db_session.commit()

    active_document = repository.create(
        document_id=str(uuid4()),
        subject_id=subject_a.subject_id,
        filename="active.pdf",
        file_type="pdf",
        chapter=1,
    )
    deleted_document = repository.create(
        document_id=str(uuid4()),
        subject_id=subject_a.subject_id,
        filename="deleted.pdf",
        file_type="pdf",
        chapter=2,
    )
    repository.create(
        document_id=str(uuid4()),
        subject_id=subject_b.subject_id,
        filename="other-subject.pdf",
        file_type="pdf",
        chapter=1,
    )

    repository.mark_deleted(
        deleted_document.document_id
    )

    result = repository.list_active_by_subject(
        subject_a.subject_id
    )

    assert [
        item.document_id
        for item in result
    ] == [active_document.document_id]


def test_list_active_excludes_documents_from_inactive_subjects(
    db_session,
    repository,
    document,
):
    deleted_subject = Subject(
        subject_id=str(uuid4()),
        name="Deleted Subject",
        status="DELETED",
    )

    db_session.add(deleted_subject)
    db_session.commit()

    hidden_document = repository.create(
        document_id=str(uuid4()),
        subject_id=deleted_subject.subject_id,
        filename="hidden.pdf",
        file_type="pdf",
        chapter=1,
    )

    result = repository.list_active()

    result_ids = [
        item.document_id
        for item in result
    ]

    assert document.document_id in result_ids
    assert hidden_document.document_id not in result_ids


def test_get_visible_by_id_requires_active_subject(
    db_session,
    repository,
    document,
):
    deleted_subject = Subject(
        subject_id=str(uuid4()),
        name="Deleted Subject Detail",
        status="DELETED",
    )

    db_session.add(deleted_subject)
    db_session.commit()

    hidden_document = repository.create(
        document_id=str(uuid4()),
        subject_id=deleted_subject.subject_id,
        filename="hidden-detail.pdf",
        file_type="pdf",
        chapter=1,
    )

    visible_result = repository.get_visible_by_id(
        document.document_id
    )
    hidden_result = repository.get_visible_by_id(
        hidden_document.document_id
    )

    assert visible_result is not None
    assert (
        visible_result.document_id
        == document.document_id
    )
    assert hidden_result is None


def test_list_indexed_for_active_subjects_filters_lifecycle(
    db_session,
    repository,
    document,
):
    indexed_active = repository.mark_indexed(
        document.document_id
    )

    repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="uploaded.pdf",
        file_type="pdf",
        chapter=2,
    )

    deleted_document = repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="deleted.pdf",
        file_type="pdf",
        chapter=3,
    )
    repository.mark_indexed(
        deleted_document.document_id
    )
    repository.mark_deleted(
        deleted_document.document_id
    )

    trashed_subject = Subject(
        subject_id=str(uuid4()),
        name=f"Trashed {uuid4()}",
        status="DELETED",
    )
    db_session.add(trashed_subject)
    db_session.commit()

    indexed_in_trash = repository.create(
        document_id=str(uuid4()),
        subject_id=trashed_subject.subject_id,
        filename="trashed.pdf",
        file_type="pdf",
        chapter=1,
    )
    repository.mark_indexed(
        indexed_in_trash.document_id
    )

    results = (
        repository
        .list_indexed_for_active_subjects()
    )

    assert [
        result.document_id
        for result in results
    ] == [indexed_active.document_id]


def test_list_reconciliation_records_includes_all_lifecycle_states(
    db_session,
    repository,
    document,
):
    document.status = "FAILED"

    trashed_subject = Subject(
        subject_id=str(uuid4()),
        name=f"Trashed {uuid4()}",
        status="DELETED",
    )
    db_session.add(trashed_subject)
    db_session.commit()

    indexed_in_trash = repository.create(
        document_id=str(uuid4()),
        subject_id=trashed_subject.subject_id,
        filename="trashed.pdf",
        file_type="pdf",
        chapter=1,
    )
    indexed_in_trash.status = "INDEXED"

    db_session.commit()

    records = (
        repository
        .list_reconciliation_records()
    )

    snapshots = {
        (
            record.document_id,
            record.subject_id,
            record.document_status,
            record.subject_status,
        )
        for record in records
    }

    assert snapshots == {
        (
            document.document_id,
            document.subject_id,
            "FAILED",
            "ACTIVE",
        ),
        (
            indexed_in_trash.document_id,
            trashed_subject.subject_id,
            "INDEXED",
            "DELETED",
        ),
    }


def test_list_all_returns_documents_in_stable_order(
    repository,
    document,
):
    second_document = repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="second.txt",
        file_type="txt",
        chapter=None,
    )

    results = repository.list_all()

    result_ids = [
        item.document_id
        for item in results
    ]

    assert result_ids == sorted(
        [
            document.document_id,
            second_document.document_id,
        ]
    )


def test_database_rejects_duplicate_active_content_for_subject(
    db_session,
    repository,
    document,
):
    content_sha256 = "a" * 64

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri="storage/uploads/first.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )

    duplicate_document = Document(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="renamed-copy.txt",
        file_type="txt",
        chapter=None,
        status="UPLOADED",
        source_uri="storage/uploads/second.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )
    db_session.add(duplicate_document)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    db_session.rollback()


def test_create_translates_active_duplicate_to_domain_error(
    db_session,
    repository,
    document,
):
    content_sha256 = "e" * 64

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri="storage/uploads/original.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )

    with pytest.raises(
        ActiveDocumentConflictError,
    ) as captured_error:
        repository.create(
            document_id=str(uuid4()),
            subject_id=document.subject_id,
            filename="renamed-copy.txt",
            file_type="txt",
            chapter=None,
            source_uri=None,
            content_sha256=content_sha256,
            file_size_bytes=10,
        )

    assert captured_error.value.document.document_id == (
        document.document_id
    )
    assert captured_error.value.document.status == "UPLOADED"

    db_session.rollback()


def test_database_allows_same_content_after_document_deleted(
    repository,
    document,
):
    content_sha256 = "b" * 64

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri="storage/uploads/first.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )
    repository.mark_deleted(document.document_id)

    result = repository.create(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="reuploaded.txt",
        file_type="txt",
        chapter=None,
        source_uri="storage/uploads/reuploaded.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )

    assert result.document_id != document.document_id


def test_database_rejects_new_document_for_failed_content(
    db_session,
    repository,
    document,
):
    content_sha256 = "c" * 64

    repository.attach_source_metadata(
        document_id=document.document_id,
        source_uri="storage/uploads/failed.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )
    document.status = "FAILED"
    db_session.commit()

    duplicate_document = Document(
        document_id=str(uuid4()),
        subject_id=document.subject_id,
        filename="retry-copy.txt",
        file_type="txt",
        chapter=None,
        status="UPLOADED",
        source_uri="storage/uploads/retry-copy.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )
    db_session.add(duplicate_document)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_attach_source_metadata_completes_matching_reservation(
    db_session,
    repository,
):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Subject {uuid4()}",
    )
    db_session.add(subject)
    db_session.commit()

    content_sha256 = "d" * 64

    reserved_document = repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="lesson.txt",
        file_type="txt",
        chapter=None,
        source_uri=None,
        content_sha256=content_sha256,
        file_size_bytes=10,
    )

    result = repository.attach_source_metadata(
        document_id=reserved_document.document_id,
        source_uri="minio://cloudmentor-sources/documents/id/source.txt",
        content_sha256=content_sha256,
        file_size_bytes=10,
    )

    assert result.source_uri == (
        "minio://cloudmentor-sources/documents/id/source.txt"
    )
    assert result.content_sha256 == content_sha256
    assert result.file_size_bytes == 10
