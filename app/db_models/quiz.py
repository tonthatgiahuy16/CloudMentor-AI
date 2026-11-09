from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


QUIZ_STATUSES = ("DRAFT", "PUBLISHED", "ARCHIVED")
ATTEMPT_STATUSES = ("IN_PROGRESS", "GRADED")


class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    subject_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("subjects.subject_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="DRAFT",
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    published_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name="chk_quizzes_status",
        ),
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    question_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    quiz_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("quizzes.quiz_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Source references stay nullable and unconstrained by a foreign key so
    # this module is independent of the policy-version work. MVP 1 will fill
    # these once document/version identity is confirmed.
    source_document_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_document_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="chk_quiz_questions_position",
        ),
        UniqueConstraint(
            "quiz_id",
            "position",
            name="uq_quiz_questions_quiz_position",
        ),
    )


class QuizOption(Base):
    __tablename__ = "quiz_options"

    option_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    question_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey(
            "quiz_questions.question_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # The approved answer key lives on the server. It must never be exposed
    # through employee-facing read models.
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    __table_args__ = (
        CheckConstraint(
            "position >= 0",
            name="chk_quiz_options_position",
        ),
        UniqueConstraint(
            "question_id",
            "position",
            name="uq_quiz_options_question_position",
        ),
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    attempt_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    quiz_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("quizzes.quiz_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    employee_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="IN_PROGRESS",
    )

    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    correct_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_questions: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    started_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    graded_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'GRADED')",
            name="chk_quiz_attempts_status",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="chk_quiz_attempts_score",
        ),
        CheckConstraint(
            "correct_count IS NULL OR correct_count >= 0",
            name="chk_quiz_attempts_correct_count",
        ),
        CheckConstraint(
            "total_questions IS NULL OR total_questions > 0",
            name="chk_quiz_attempts_total_questions",
        ),
    )


class QuizAttemptAnswer(Base):
    __tablename__ = "quiz_attempt_answers"

    answer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    attempt_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey(
            "quiz_attempts.attempt_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey(
            "quiz_questions.question_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    selected_option_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey(
            "quiz_options.option_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    answered_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_quiz_attempt_answers_attempt_question",
        ),
    )
