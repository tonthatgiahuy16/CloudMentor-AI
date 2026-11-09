from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db_models  # noqa: F401 - register all tables
from app.api.documents import (
    get_policy_version_service,
    router,
)
from app.core.database import Base
from app.db_models.subject import Subject
from app.repos.document_repository import DocumentRepository
from app.services.policy_version_service import (
    PolicyVersionService,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
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
def subject(db_session):
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Policy {uuid4()}",
    )
    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)
    return subject


@pytest.fixture
def repository(db_session):
    return DocumentRepository(db_session)


def create_indexed_document(
    repository,
    subject,
    *,
    indexed_chunk_count=3,
    source_uri="minio://policies/default.pdf",
):
    document = repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="policy.pdf",
        file_type="pdf",
        chapter=1,
        source_uri=source_uri,
    )

    if indexed_chunk_count is None:
        repository.mark_indexed(document.document_id)
    else:
        repository.mark_indexed(
            document.document_id,
            indexed_chunk_count=indexed_chunk_count,
        )

    return repository.get_by_id(document.document_id)


# ---------------------------------------------------------------------------
# DocumentRepository.activate_policy_version - business rules
# ---------------------------------------------------------------------------
def test_repository_activate_sets_effective_from(
    db_session,
    repository,
    subject,
):
    document = create_indexed_document(repository, subject)
    effective_from = date(2026, 11, 10)

    result = repository.activate_policy_version(
        document_id=document.document_id,
        effective_from=effective_from,
    )

    assert result.effective_from == effective_from
    assert result.effective_until is None
    db_session.refresh(document)
    assert document.effective_from == effective_from


def test_repository_activate_is_idempotent_for_same_date(
    repository,
    subject,
):
    document = create_indexed_document(repository, subject)
    effective_from = date(2026, 11, 10)
    repository.activate_policy_version(
        document_id=document.document_id,
        effective_from=effective_from,
    )

    result = repository.activate_policy_version(
        document_id=document.document_id,
        effective_from=effective_from,
    )

    assert result.effective_from == effective_from


def test_repository_activate_rejects_missing_document(repository):
    with pytest.raises(
        RuntimeError,
        match="Document not found",
    ):
        repository.activate_policy_version(
            document_id=str(uuid4()),
            effective_from=date(2026, 11, 10),
        )


def test_repository_activate_rejects_document_not_indexed(
    repository,
    subject,
):
    document = repository.create(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="policy.pdf",
        file_type="pdf",
        chapter=1,
        source_uri="minio://policies/default.pdf",
    )

    with pytest.raises(
        RuntimeError,
        match="Only indexed documents can be activated",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 11, 10),
        )


def test_repository_activate_rejects_missing_retained_source(
    repository,
    subject,
):
    document = create_indexed_document(
        repository,
        subject,
        source_uri=None,
    )

    with pytest.raises(
        RuntimeError,
        match="Document has no retained source",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 11, 10),
        )


def test_repository_activate_rejects_unverified_chunk_count(
    repository,
    subject,
):
    document = create_indexed_document(
        repository,
        subject,
        indexed_chunk_count=None,
    )

    with pytest.raises(
        RuntimeError,
        match="Document index has not been verified",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 11, 10),
        )


def test_repository_activate_rejects_already_activated_document(
    repository,
    subject,
):
    document = create_indexed_document(repository, subject)
    repository.activate_policy_version(
        document_id=document.document_id,
        effective_from=date(2026, 1, 1),
    )

    with pytest.raises(
        RuntimeError,
        match="Document version is already activated",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 6, 1),
        )


def test_repository_activate_rejects_inactive_subject(
    db_session,
    repository,
    subject,
):
    document = create_indexed_document(repository, subject)
    subject.status = "DELETED"
    db_session.commit()

    with pytest.raises(
        RuntimeError,
        match="Subject is not active",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 11, 10),
        )


def test_repository_activate_rejects_self_supersede(
    repository,
    subject,
):
    document = create_indexed_document(repository, subject)

    with pytest.raises(
        RuntimeError,
        match="A document cannot supersede itself",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 11, 10),
            supersedes_document_id=document.document_id,
        )


def test_repository_activate_rejects_missing_superseded_document(
    repository,
    subject,
):
    document = create_indexed_document(repository, subject)

    with pytest.raises(
        RuntimeError,
        match="Superseded document not found",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 11, 10),
            supersedes_document_id=str(uuid4()),
        )


def test_repository_activate_rejects_supersede_across_subjects(
    db_session,
    repository,
    subject,
):
    other_subject = Subject(
        subject_id=str(uuid4()),
        name=f"Other {uuid4()}",
    )
    db_session.add(other_subject)
    db_session.commit()

    replaced = create_indexed_document(repository, other_subject)
    repository.activate_policy_version(
        document_id=replaced.document_id,
        effective_from=date(2026, 1, 1),
    )
    document = create_indexed_document(repository, subject)

    with pytest.raises(
        RuntimeError,
        match="Documents must belong to the same category",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 6, 1),
            supersedes_document_id=replaced.document_id,
        )


def test_repository_activate_rejects_non_applicable_supersede_target(
    repository,
    subject,
):
    replaced = create_indexed_document(repository, subject)
    document = create_indexed_document(repository, subject)

    with pytest.raises(
        RuntimeError,
        match="Only an applicable indexed document can be superseded",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 6, 1),
            supersedes_document_id=replaced.document_id,
        )


def test_repository_activate_rejects_replacement_not_after_existing(
    repository,
    subject,
):
    replaced = create_indexed_document(repository, subject)
    repository.activate_policy_version(
        document_id=replaced.document_id,
        effective_from=date(2026, 6, 1),
    )
    document = create_indexed_document(repository, subject)

    with pytest.raises(
        RuntimeError,
        match="Replacement must start after the existing version",
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 6, 1),
            supersedes_document_id=replaced.document_id,
        )


def test_repository_activate_rejects_target_not_applicable_on_date(
    db_session,
    repository,
    subject,
):
    replaced = create_indexed_document(repository, subject)
    repository.activate_policy_version(
        document_id=replaced.document_id,
        effective_from=date(2026, 1, 1),
    )
    replaced.effective_until = date(2026, 3, 1)
    db_session.commit()
    document = create_indexed_document(repository, subject)

    with pytest.raises(
        RuntimeError,
        match=(
            "The selected document is not applicable "
            "on the replacement date"
        ),
    ):
        repository.activate_policy_version(
            document_id=document.document_id,
            effective_from=date(2026, 6, 1),
            supersedes_document_id=replaced.document_id,
        )


def test_repository_activate_supersede_closes_existing_window(
    db_session,
    repository,
    subject,
):
    replaced = create_indexed_document(repository, subject)
    repository.activate_policy_version(
        document_id=replaced.document_id,
        effective_from=date(2026, 1, 1),
    )
    document = create_indexed_document(repository, subject)

    result = repository.activate_policy_version(
        document_id=document.document_id,
        effective_from=date(2026, 6, 1),
        supersedes_document_id=replaced.document_id,
    )

    db_session.refresh(replaced)
    assert result.effective_from == date(2026, 6, 1)
    assert replaced.effective_until == date(2026, 6, 1)


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/activate - HTTP mapping
# ---------------------------------------------------------------------------
class FakeActivationRepository:
    def __init__(self, document=None, error=None):
        self.document = document
        self.error = error

    def get_by_id(self, document_id):
        return self.document

    def activate_policy_version(self, **kwargs):
        if self.error is not None:
            raise self.error
        self.document.effective_from = kwargs["effective_from"]
        self.document.supersedes_document_id = kwargs[
            "supersedes_document_id"
        ]
        return self.document


class FakeVectorStore:
    def __init__(self, chunk_count=3):
        self.chunk_count = chunk_count

    def count_by_document_id(self, document_id):
        return self.chunk_count


def make_api_document(
    *,
    status="INDEXED",
    indexed_chunk_count=3,
    effective_from=None,
):
    return SimpleNamespace(
        document_id="document-1",
        subject_id="subject-1",
        filename="policy.pdf",
        file_type="pdf",
        chapter=1,
        status=status,
        uploaded_at=datetime(
            2026,
            10,
            1,
            tzinfo=timezone.utc,
        ),
        indexed_at=datetime(
            2026,
            10,
            2,
            tzinfo=timezone.utc,
        ),
        effective_from=effective_from,
        effective_until=None,
        indexed_chunk_count=indexed_chunk_count,
    )


def make_client(
    *,
    document=None,
    chunk_count=3,
    error=None,
):
    app = FastAPI()
    app.include_router(router)

    service = PolicyVersionService(
        document_repo=FakeActivationRepository(
            document=document,
            error=error,
        ),
        vector_store=FakeVectorStore(chunk_count=chunk_count),
    )
    app.dependency_overrides[
        get_policy_version_service
    ] = lambda: service

    return TestClient(app)


def test_api_activate_returns_serialized_document():
    client = make_client(document=make_api_document())

    response = client.post(
        "/documents/document-1/activate",
        json={"effective_from": "2026-11-10"},
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == "document-1"
    assert response.json()["effective_from"] == "2026-11-10"
    assert response.json()["effective_date"] == "2026-11-10"


def test_api_activate_maps_missing_document_to_404():
    client = make_client(document=None)

    response = client.post(
        "/documents/missing/activate",
        json={"effective_from": "2026-11-10"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_api_activate_maps_chunk_mismatch_to_409():
    client = make_client(
        document=make_api_document(indexed_chunk_count=3),
        chunk_count=2,
    )

    response = client.post(
        "/documents/document-1/activate",
        json={"effective_from": "2026-11-10"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Indexed chunk count does not match PostgreSQL"
        )
    }


def test_api_activate_maps_missing_superseded_to_404():
    client = make_client(
        document=make_api_document(),
        error=RuntimeError("Superseded document not found"),
    )

    response = client.post(
        "/documents/document-1/activate",
        json={
            "effective_from": "2026-11-10",
            "supersedes_document_id": "missing",
        },
    )

    assert response.status_code == 404


def test_api_activate_maps_invalid_date_to_409():
    client = make_client(
        document=make_api_document(),
        error=RuntimeError(
            "Replacement must start after the existing version"
        ),
    )

    response = client.post(
        "/documents/document-1/activate",
        json={"effective_from": "2026-11-10"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Replacement must start after the existing version"
        )
    }
