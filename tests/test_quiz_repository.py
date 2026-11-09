from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db_models  # noqa: F401 - register all tables on Base.metadata
from app.core.database import Base
from app.db_models.subject import Subject
from app.repos.quiz_repository import QuizRepository


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
        name="Cloud Computing",
    )
    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)
    return subject


def test_create_quiz_starts_as_draft(db_session, subject):
    repository = QuizRepository(db_session)

    quiz = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Cloud Security",
    )

    assert quiz.status == "DRAFT"
    assert quiz.published_at is None
    assert repository.get_quiz(quiz.quiz_id).quiz_id == quiz.quiz_id


def test_list_published_excludes_draft_quizzes(
    db_session,
    subject,
):
    repository = QuizRepository(db_session)
    draft = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Draft",
    )
    published = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Published",
    )
    repository.publish_quiz(published.quiz_id)

    results = repository.list_published_by_subject(
        subject.subject_id
    )

    assert [quiz.quiz_id for quiz in results] == [
        published.quiz_id
    ]
    assert draft.quiz_id not in {
        quiz.quiz_id for quiz in results
    }


def test_publish_quiz_sets_status_and_timestamp(
    db_session,
    subject,
):
    repository = QuizRepository(db_session)
    quiz = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Cloud Security",
    )

    published = repository.publish_quiz(quiz.quiz_id)

    assert published.status == "PUBLISHED"
    assert published.published_at is not None


def test_questions_and_options_keep_input_order(
    db_session,
    subject,
):
    repository = QuizRepository(db_session)
    quiz = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Cloud Security",
    )
    question = repository.add_question(
        quiz_id=quiz.quiz_id,
        prompt="IAM là gì?",
        position=0,
        source_document_id="document-1",
        source_document_version="2",
    )
    repository.add_option(
        question_id=question.question_id,
        text="Sai",
        position=1,
        is_correct=False,
    )
    correct = repository.add_option(
        question_id=question.question_id,
        text="Đúng",
        position=0,
        is_correct=True,
    )

    options = repository.get_options_for_questions(
        [question.question_id]
    )[question.question_id]
    correct_options = repository.get_correct_options(
        [question.question_id]
    )

    assert [option.text for option in options] == [
        "Đúng",
        "Sai",
    ]
    assert correct_options[question.question_id].option_id == (
        correct.option_id
    )
    assert repository.count_questions(quiz.quiz_id) == 1


def test_finalize_attempt_persists_grade_and_answers(
    db_session,
    subject,
):
    repository = QuizRepository(db_session)
    quiz = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Cloud Security",
    )
    question = repository.add_question(
        quiz_id=quiz.quiz_id,
        prompt="IAM là gì?",
        position=0,
    )
    option = repository.add_option(
        question_id=question.question_id,
        text="Identity and Access Management",
        position=0,
        is_correct=True,
    )
    attempt = repository.create_attempt(
        quiz_id=quiz.quiz_id,
        employee_id="new-hire-1",
    )

    finalized = repository.finalize_attempt(
        attempt_id=attempt.attempt_id,
        correct_count=1,
        total_questions=1,
        score=1.0,
        answers=[
            {
                "question_id": question.question_id,
                "selected_option_id": option.option_id,
                "is_correct": True,
            }
        ],
    )

    assert finalized.status == "GRADED"
    assert finalized.score == 1.0
    assert finalized.correct_count == 1
    assert finalized.total_questions == 1
    assert finalized.graded_at is not None

    stored_answers = repository.get_attempt_answers(
        attempt.attempt_id
    )
    assert len(stored_answers) == 1
    assert (
        stored_answers[0].selected_option_id
        == option.option_id
    )
    assert stored_answers[0].is_correct is True


def test_list_attempts_scoped_to_quiz(db_session, subject):
    repository = QuizRepository(db_session)
    quiz_one = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Quiz one",
    )
    quiz_two = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Quiz two",
    )
    first = repository.create_attempt(
        quiz_id=quiz_one.quiz_id,
        employee_id="new-hire-1",
    )
    second = repository.create_attempt(
        quiz_id=quiz_two.quiz_id,
        employee_id="new-hire-2",
    )

    attempts = repository.list_attempts(quiz_one.quiz_id)

    assert [attempt.attempt_id for attempt in attempts] == [
        first.attempt_id
    ]
    assert second.attempt_id not in {
        attempt.attempt_id for attempt in attempts
    }


def test_get_answers_for_attempts_groups_by_attempt(
    db_session,
    subject,
):
    repository = QuizRepository(db_session)
    quiz = repository.create_quiz(
        subject_id=subject.subject_id,
        title="Cloud Security",
    )
    option = repository.add_option(
        question_id=repository.add_question(
            quiz_id=quiz.quiz_id,
            prompt="IAM là gì?",
            position=0,
        ).question_id,
        text="Identity and Access Management",
        position=0,
        is_correct=True,
    )
    first = repository.create_attempt(
        quiz_id=quiz.quiz_id,
        employee_id="new-hire-1",
    )
    second = repository.create_attempt(
        quiz_id=quiz.quiz_id,
        employee_id="new-hire-2",
    )
    question = repository.get_questions(quiz.quiz_id)[0]

    repository.finalize_attempt(
        attempt_id=first.attempt_id,
        correct_count=0,
        total_questions=1,
        score=0.0,
        answers=[
            {
                "question_id": question.question_id,
                "selected_option_id": None,
                "is_correct": False,
            }
        ],
    )
    repository.finalize_attempt(
        attempt_id=second.attempt_id,
        correct_count=1,
        total_questions=1,
        score=1.0,
        answers=[
            {
                "question_id": question.question_id,
                "selected_option_id": option.option_id,
                "is_correct": True,
            }
        ],
    )

    grouped = repository.get_answers_for_attempts(
        [first.attempt_id, second.attempt_id]
    )

    assert set(grouped) == {first.attempt_id, second.attempt_id}
    assert grouped[first.attempt_id][0].selected_option_id is None
    assert (
        grouped[second.attempt_id][0].selected_option_id
        == option.option_id
    )


def test_get_answers_for_attempts_handles_empty_list(db_session):
    repository = QuizRepository(db_session)

    assert repository.get_answers_for_attempts([]) == {}
