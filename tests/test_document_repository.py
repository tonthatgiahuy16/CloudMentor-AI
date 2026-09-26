from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models.subject import Subject
from app.repos.document_repository import DocumentRepository


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
