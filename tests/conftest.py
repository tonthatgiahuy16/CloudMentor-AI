import os
from uuid import uuid4


os.environ.setdefault("DATABASE_URL", "sqlite:///./cloudmentor-test.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db_models  # noqa: E402,F401 - register tables on Base.metadata
from app.core.database import Base
from app.db_models.subject import Subject


@pytest.fixture
def quiz_db_session():
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
def quiz_subject(quiz_db_session):
    subject = Subject(
        subject_id=str(uuid4()),
        name="Cloud Computing",
    )
    quiz_db_session.add(subject)
    quiz_db_session.commit()
    quiz_db_session.refresh(subject)
    return subject
