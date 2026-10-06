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
