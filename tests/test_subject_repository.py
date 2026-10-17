from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models.subject import Subject
from app.repos.subject_repository import SubjectRepository


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


def test_list_all_returns_subjects_sorted_by_name(
    db_session,
):
    db_session.add_all(
        [
            Subject(
                subject_id=str(uuid4()),
                name="Data Engineering",
            ),
            Subject(
                subject_id=str(uuid4()),
                name="Cloud Computing",
            ),
        ]
    )
    db_session.commit()

    repository = SubjectRepository(db_session)

    results = repository.list_all()

    assert [
        subject.name
        for subject in results
    ] == [
        "Cloud Computing",
        "Data Engineering",
    ]


def test_list_all_returns_empty_list(
    db_session,
):
    repository = SubjectRepository(db_session)

    assert repository.list_all() == []


def test_create_persists_subject(db_session):
    repository = SubjectRepository(db_session)

    subject = repository.create(name="Data Engineering")

    assert subject.subject_id is not None
    assert subject.name == "Data Engineering"
    assert db_session.query(Subject).one().subject_id == subject.subject_id


def test_create_rolls_back_when_name_already_exists(db_session):
    repository = SubjectRepository(db_session)
    repository.create(name="Data Engineering")

    with pytest.raises(IntegrityError):
        repository.create(name="Data Engineering")

    assert [
        subject.name
        for subject in repository.list_all()
    ] == ["Data Engineering"]


def test_create_sets_active_lifecycle_defaults(
    db_session,
):
    repository = SubjectRepository(db_session)

    subject = repository.create(
        name="Data Engineering"
    )

    assert subject.status == "ACTIVE"
    assert subject.deleted_at is None
    assert subject.lifecycle_error is None


def test_list_active_excludes_non_active_subjects(
    db_session,
):
    db_session.add_all(
        [
            Subject(
                subject_id=str(uuid4()),
                name="Active Subject",
                status="ACTIVE",
            ),
            Subject(
                subject_id=str(uuid4()),
                name="Deleting Subject",
                status="DELETING",
            ),
            Subject(
                subject_id=str(uuid4()),
                name="Deleted Subject",
                status="DELETED",
            ),
            Subject(
                subject_id=str(uuid4()),
                name="Delete Failed Subject",
                status="DELETE_FAILED",
            ),
            Subject(
                subject_id=str(uuid4()),
                name="Restoring Subject",
                status="RESTORING",
            ),
            Subject(
                subject_id=str(uuid4()),
                name="Restore Failed Subject",
                status="RESTORE_FAILED",
            ),
        ]
    )
    db_session.commit()

    repository = SubjectRepository(db_session)

    results = repository.list_active()

    assert [
        subject.name
        for subject in results
    ] == ["Active Subject"]


def test_list_trash_returns_non_active_subjects_sorted_by_name(
    db_session,
):
    inactive_subjects = [
        Subject(
            subject_id=str(uuid4()),
            name="Deleting Subject",
            status="DELETING",
        ),
        Subject(
            subject_id=str(uuid4()),
            name="Deleted Subject",
            status="DELETED",
        ),
        Subject(
            subject_id=str(uuid4()),
            name="Delete Failed Subject",
            status="DELETE_FAILED",
        ),
        Subject(
            subject_id=str(uuid4()),
            name="Restoring Subject",
            status="RESTORING",
        ),
        Subject(
            subject_id=str(uuid4()),
            name="Restore Failed Subject",
            status="RESTORE_FAILED",
        ),
    ]

    db_session.add(
        Subject(
            subject_id=str(uuid4()),
            name="Active Subject",
            status="ACTIVE",
        )
    )
    db_session.add_all(inactive_subjects)
    db_session.commit()

    repository = SubjectRepository(db_session)

    results = repository.list_trash()

    expected_names = [
        subject.name
        for subject in inactive_subjects
    ]

    assert [
        subject.name
        for subject in results
    ] == sorted(expected_names)
    assert all(
        subject.status != "ACTIVE"
        for subject in results
    )


def test_delete_lifecycle_transitions_subject_to_deleted(
    db_session,
):
    repository = SubjectRepository(db_session)
    subject = repository.create(
        name="Cloud Computing"
    )

    deleting = repository.mark_deleting(
        subject.subject_id
    )

    assert deleting.status == "DELETING"
    assert deleting.deleted_at is None
    assert deleting.lifecycle_error is None

    deleted = repository.mark_deleted(
        subject.subject_id
    )

    assert deleted.status == "DELETED"
    assert deleted.deleted_at is not None
    assert deleted.lifecycle_error is None


def test_delete_failure_is_recorded_and_can_be_retried(
    db_session,
):
    repository = SubjectRepository(db_session)
    subject = repository.create(
        name="Cloud Computing"
    )

    repository.mark_deleting(
        subject.subject_id
    )

    failed = repository.mark_delete_failed(
        subject_id=subject.subject_id,
        error_message="Chroma unavailable",
    )

    assert failed.status == "DELETE_FAILED"
    assert failed.deleted_at is None
    assert (
        failed.lifecycle_error
        == "Chroma unavailable"
    )

    retried = repository.mark_deleting(
        subject.subject_id
    )

    assert retried.status == "DELETING"
    assert retried.lifecycle_error is None


def test_restore_lifecycle_transitions_subject_to_active(
    db_session,
):
    repository = SubjectRepository(db_session)
    subject = repository.create(
        name="Cloud Computing"
    )

    repository.mark_deleting(
        subject.subject_id
    )
    deleted = repository.mark_deleted(
        subject.subject_id
    )

    deleted_at = deleted.deleted_at

    restoring = repository.mark_restoring(
        subject.subject_id
    )

    assert restoring.status == "RESTORING"
    assert restoring.deleted_at == deleted_at
    assert restoring.lifecycle_error is None

    restored = repository.mark_active(
        subject.subject_id
    )

    assert restored.status == "ACTIVE"
    assert restored.deleted_at is None
    assert restored.lifecycle_error is None


def test_restore_failure_is_recorded_and_can_be_retried(
    db_session,
):
    repository = SubjectRepository(db_session)
    subject = repository.create(
        name="Data Engineering"
    )

    repository.mark_deleting(
        subject.subject_id
    )
    repository.mark_deleted(
        subject.subject_id
    )
    repository.mark_restoring(
        subject.subject_id
    )

    failed = repository.mark_restore_failed(
        subject_id=subject.subject_id,
        error_message="Chroma rebuild failed",
    )

    assert failed.status == "RESTORE_FAILED"
    assert failed.deleted_at is not None
    assert (
        failed.lifecycle_error
        == "Chroma rebuild failed"
    )

    retried = repository.mark_restoring(
        subject.subject_id
    )

    assert retried.status == "RESTORING"
    assert retried.deleted_at is not None
    assert retried.lifecycle_error is None
