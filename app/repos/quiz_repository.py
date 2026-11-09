from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_models.quiz import (
    Quiz,
    QuizAttempt,
    QuizAttemptAnswer,
    QuizOption,
    QuizQuestion,
)


class QuizRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Quiz definitions
    # ------------------------------------------------------------------
    def create_quiz(
        self,
        *,
        subject_id: str,
        title: str,
    ) -> Quiz:
        quiz = Quiz(
            subject_id=subject_id,
            title=title,
            status="DRAFT",
        )
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    def get_quiz(self, quiz_id: str) -> Quiz | None:
        return (
            self.db.query(Quiz)
            .filter(Quiz.quiz_id == quiz_id)
            .first()
        )

    def list_quizzes_by_subject(
        self,
        subject_id: str,
    ) -> list[Quiz]:
        return (
            self.db.query(Quiz)
            .filter(Quiz.subject_id == subject_id)
            .order_by(Quiz.created_at.desc())
            .all()
        )

    def list_published_by_subject(
        self,
        subject_id: str,
    ) -> list[Quiz]:
        return (
            self.db.query(Quiz)
            .filter(
                Quiz.subject_id == subject_id,
                Quiz.status == "PUBLISHED",
            )
            .order_by(Quiz.published_at.desc())
            .all()
        )

    def publish_quiz(self, quiz_id: str) -> Quiz:
        quiz = self.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        if quiz.status == "PUBLISHED":
            return quiz

        quiz.status = "PUBLISHED"
        quiz.published_at = func.now()

        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    # ------------------------------------------------------------------
    # Questions and options
    # ------------------------------------------------------------------
    def add_question(
        self,
        *,
        quiz_id: str,
        prompt: str,
        position: int,
        source_document_id: str | None = None,
        source_document_version: str | None = None,
    ) -> QuizQuestion:
        question = QuizQuestion(
            quiz_id=quiz_id,
            prompt=prompt,
            position=position,
            source_document_id=source_document_id,
            source_document_version=source_document_version,
        )
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def add_option(
        self,
        *,
        question_id: str,
        text: str,
        position: int,
        is_correct: bool,
    ) -> QuizOption:
        option = QuizOption(
            question_id=question_id,
            text=text,
            position=position,
            is_correct=is_correct,
        )
        self.db.add(option)
        self.db.commit()
        self.db.refresh(option)
        return option

    def get_questions(self, quiz_id: str) -> list[QuizQuestion]:
        return (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.position.asc())
            .all()
        )

    def get_options_for_questions(
        self,
        question_ids: list[str],
    ) -> dict[str, list[QuizOption]]:
        if not question_ids:
            return {}

        options = (
            self.db.query(QuizOption)
            .filter(QuizOption.question_id.in_(question_ids))
            .order_by(
                QuizOption.question_id.asc(),
                QuizOption.position.asc(),
            )
            .all()
        )

        grouped: dict[str, list[QuizOption]] = {
            question_id: [] for question_id in question_ids
        }
        for option in options:
            grouped.setdefault(
                option.question_id,
                [],
            ).append(option)

        return grouped

    def get_correct_options(
        self,
        question_ids: list[str],
    ) -> dict[str, QuizOption]:
        if not question_ids:
            return {}

        correct_options = (
            self.db.query(QuizOption)
            .filter(
                QuizOption.question_id.in_(question_ids),
                QuizOption.is_correct.is_(True),
            )
            .all()
        )

        return {
            option.question_id: option
            for option in correct_options
        }

    def count_questions(self, quiz_id: str) -> int:
        return (
            self.db.query(func.count(QuizQuestion.question_id))
            .filter(QuizQuestion.quiz_id == quiz_id)
            .scalar()
            or 0
        )

    # ------------------------------------------------------------------
    # Attempts
    # ------------------------------------------------------------------
    def create_attempt(
        self,
        *,
        quiz_id: str,
        employee_id: str,
    ) -> QuizAttempt:
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            employee_id=employee_id,
            status="IN_PROGRESS",
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_attempt(
        self,
        attempt_id: str,
    ) -> QuizAttempt | None:
        return (
            self.db.query(QuizAttempt)
            .filter(QuizAttempt.attempt_id == attempt_id)
            .first()
        )

    def list_attempts(
        self,
        quiz_id: str,
    ) -> list[QuizAttempt]:
        return (
            self.db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.started_at.asc())
            .all()
        )

    def get_attempt_answers(
        self,
        attempt_id: str,
    ) -> list[QuizAttemptAnswer]:
        return (
            self.db.query(QuizAttemptAnswer)
            .filter(
                QuizAttemptAnswer.attempt_id == attempt_id
            )
            .all()
        )

    def get_answers_for_attempts(
        self,
        attempt_ids: list[str],
    ) -> dict[str, list[QuizAttemptAnswer]]:
        if not attempt_ids:
            return {}

        answers = (
            self.db.query(QuizAttemptAnswer)
            .filter(
                QuizAttemptAnswer.attempt_id.in_(attempt_ids)
            )
            .order_by(
                QuizAttemptAnswer.attempt_id.asc(),
                QuizAttemptAnswer.answered_at.asc(),
            )
            .all()
        )

        grouped: dict[str, list[QuizAttemptAnswer]] = {
            attempt_id: [] for attempt_id in attempt_ids
        }
        for answer in answers:
            grouped.setdefault(
                answer.attempt_id,
                [],
            ).append(answer)

        return grouped

    def finalize_attempt(
        self,
        *,
        attempt_id: str,
        correct_count: int,
        total_questions: int,
        score: float,
        answers: list[dict],
    ) -> QuizAttempt:
        try:
            attempt = self.get_attempt(attempt_id)

            if attempt is None:
                raise RuntimeError("Attempt not found")

            for answer in answers:
                self.db.add(
                    QuizAttemptAnswer(
                        attempt_id=attempt_id,
                        question_id=answer["question_id"],
                        selected_option_id=(
                            answer["selected_option_id"]
                        ),
                        is_correct=answer["is_correct"],
                    )
                )

            attempt.status = "GRADED"
            attempt.correct_count = correct_count
            attempt.total_questions = total_questions
            attempt.score = score
            attempt.graded_at = func.now()

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(attempt)
        return attempt
