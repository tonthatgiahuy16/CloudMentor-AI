"""create quiz, question, option, attempt, and attempt answer tables

Revision ID: c4f1a9b2d7e5
Revises: 7a2d5f1c9b31
Create Date: 2026-11-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f1a9b2d7e5"
down_revision: Union[str, Sequence[str], None] = "7a2d5f1c9b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column(
            "quiz_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')",
            name="chk_quizzes_status",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.subject_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("quiz_id"),
    )
    op.create_index(
        op.f("ix_quizzes_subject_id"),
        "quizzes",
        ["subject_id"],
        unique=False,
    )

    op.create_table(
        "quiz_questions",
        sa.Column(
            "question_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "quiz_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "source_document_id",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "source_document_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="chk_quiz_questions_position",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.quiz_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("question_id"),
        sa.UniqueConstraint(
            "quiz_id",
            "position",
            name="uq_quiz_questions_quiz_position",
        ),
    )
    op.create_index(
        op.f("ix_quiz_questions_quiz_id"),
        "quiz_questions",
        ["quiz_id"],
        unique=False,
    )

    op.create_table(
        "quiz_options",
        sa.Column(
            "option_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_correct",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="chk_quiz_options_position",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["quiz_questions.question_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("option_id"),
        sa.UniqueConstraint(
            "question_id",
            "position",
            name="uq_quiz_options_question_position",
        ),
    )
    op.create_index(
        op.f("ix_quiz_options_question_id"),
        "quiz_options",
        ["question_id"],
        unique=False,
    )

    op.create_table(
        "quiz_attempts",
        sa.Column(
            "attempt_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "quiz_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="IN_PROGRESS",
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "correct_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "total_questions",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "graded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'GRADED')",
            name="chk_quiz_attempts_status",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="chk_quiz_attempts_score",
        ),
        sa.CheckConstraint(
            "correct_count IS NULL OR correct_count >= 0",
            name="chk_quiz_attempts_correct_count",
        ),
        sa.CheckConstraint(
            "total_questions IS NULL OR total_questions > 0",
            name="chk_quiz_attempts_total_questions",
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.quiz_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    op.create_index(
        op.f("ix_quiz_attempts_quiz_id"),
        "quiz_attempts",
        ["quiz_id"],
        unique=False,
    )

    op.create_table(
        "quiz_attempt_answers",
        sa.Column(
            "answer_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "attempt_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "selected_option_id",
            sa.UUID(as_uuid=False),
            nullable=True,
        ),
        sa.Column(
            "is_correct",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "answered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["quiz_attempts.attempt_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["quiz_questions.question_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_option_id"],
            ["quiz_options.option_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("answer_id"),
        sa.UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_quiz_attempt_answers_attempt_question",
        ),
    )
    op.create_index(
        op.f("ix_quiz_attempt_answers_attempt_id"),
        "quiz_attempt_answers",
        ["attempt_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_quiz_attempt_answers_attempt_id"),
        table_name="quiz_attempt_answers",
    )
    op.drop_table("quiz_attempt_answers")
    op.drop_index(
        op.f("ix_quiz_attempts_quiz_id"),
        table_name="quiz_attempts",
    )
    op.drop_table("quiz_attempts")
    op.drop_index(
        op.f("ix_quiz_options_question_id"),
        table_name="quiz_options",
    )
    op.drop_table("quiz_options")
    op.drop_index(
        op.f("ix_quiz_questions_quiz_id"),
        table_name="quiz_questions",
    )
    op.drop_table("quiz_questions")
    op.drop_index(
        op.f("ix_quizzes_subject_id"),
        table_name="quizzes",
    )
    op.drop_table("quizzes")
