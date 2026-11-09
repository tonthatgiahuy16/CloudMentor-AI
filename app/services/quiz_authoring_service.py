from typing import Any

from app.repos.quiz_repository import QuizRepository


class QuizAuthoringService:
    """
    Quản lý việc soạn và xuất bản quiz.

    Chỉ quiz ở trạng thái PUBLISHED mới được trả về cho nhân viên.
    Đáp án đúng (answer key) chỉ lưu ở server và không nằm trong read model.
    """

    def __init__(self, quiz_repo: QuizRepository):
        self.quiz_repo = quiz_repo

    def create_quiz(
        self,
        *,
        subject_id: str,
        title: str,
    ) -> dict[str, Any]:
        quiz = self.quiz_repo.create_quiz(
            subject_id=subject_id,
            title=title,
        )

        return self._serialize_summary(
            quiz,
            question_count=0,
        )

    def add_question(
        self,
        *,
        quiz_id: str,
        prompt: str,
        options: list[dict[str, Any]],
        source_document_id: str | None = None,
        source_document_version: str | None = None,
    ) -> dict[str, Any]:
        quiz = self.quiz_repo.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        if quiz.status != "DRAFT":
            raise RuntimeError(
                "Only draft quizzes can be edited"
            )

        correct_count = sum(
            1 for option in options if option.get("is_correct")
        )
        if correct_count != 1:
            raise RuntimeError(
                "A question must have exactly one correct option"
            )

        position = self.quiz_repo.count_questions(quiz_id)

        question = self.quiz_repo.add_question(
            quiz_id=quiz_id,
            prompt=prompt,
            position=position,
            source_document_id=source_document_id,
            source_document_version=source_document_version,
        )

        created_options = [
            self.quiz_repo.add_option(
                question_id=question.question_id,
                text=option["text"],
                position=index,
                is_correct=bool(option.get("is_correct")),
            )
            for index, option in enumerate(options)
        ]

        return {
            "question_id": question.question_id,
            "prompt": question.prompt,
            "position": question.position,
            "source_document_id": (
                question.source_document_id
            ),
            "source_document_version": (
                question.source_document_version
            ),
            "options": [
                {
                    "option_id": option.option_id,
                    "text": option.text,
                    "position": option.position,
                }
                for option in created_options
            ],
        }

    def publish_quiz(self, quiz_id: str) -> dict[str, Any]:
        quiz = self.quiz_repo.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        if quiz.status == "PUBLISHED":
            return {
                "quiz_id": quiz.quiz_id,
                "status": "PUBLISHED",
                "question_count": (
                    self.quiz_repo.count_questions(quiz_id)
                ),
            }

        if quiz.status != "DRAFT":
            raise RuntimeError(
                "Only draft quizzes can be published"
            )

        questions = self.quiz_repo.get_questions(quiz_id)

        if not questions:
            raise RuntimeError(
                "Quiz must have at least one question"
            )

        question_ids = [
            question.question_id for question in questions
        ]
        correct_options = self.quiz_repo.get_correct_options(
            question_ids
        )
        options_by_question = (
            self.quiz_repo.get_options_for_questions(
                question_ids
            )
        )

        for question in questions:
            if len(options_by_question.get(
                question.question_id,
                [],
            )) < 2:
                raise RuntimeError(
                    "Every question must have at least two options"
                )

            if question.question_id not in correct_options:
                raise RuntimeError(
                    "Every question must have an approved answer key"
                )

        published_quiz = self.quiz_repo.publish_quiz(quiz_id)

        return {
            "quiz_id": published_quiz.quiz_id,
            "status": "PUBLISHED",
            "question_count": len(questions),
        }

    def list_published_quizzes(
        self,
        *,
        subject_id: str,
    ) -> list[dict[str, Any]]:
        quizzes = self.quiz_repo.list_published_by_subject(
            subject_id
        )

        return [
            self._serialize_summary(
                quiz,
                question_count=(
                    self.quiz_repo.count_questions(
                        quiz.quiz_id
                    )
                ),
            )
            for quiz in quizzes
        ]

    def get_published_quiz(
        self,
        quiz_id: str,
    ) -> dict[str, Any]:
        quiz = self.quiz_repo.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        if quiz.status != "PUBLISHED":
            raise RuntimeError("Quiz is not published")

        questions = self.quiz_repo.get_questions(quiz_id)
        question_ids = [
            question.question_id for question in questions
        ]
        options_by_question = (
            self.quiz_repo.get_options_for_questions(
                question_ids
            )
        )

        return {
            "quiz_id": quiz.quiz_id,
            "subject_id": quiz.subject_id,
            "title": quiz.title,
            "status": "PUBLISHED",
            "question_count": len(questions),
            "questions": [
                {
                    "question_id": question.question_id,
                    "prompt": question.prompt,
                    "position": question.position,
                    "source_document_id": (
                        question.source_document_id
                    ),
                    "source_document_version": (
                        question.source_document_version
                    ),
                    "options": [
                        {
                            "option_id": option.option_id,
                            "text": option.text,
                            "position": option.position,
                        }
                        for option in options_by_question.get(
                            question.question_id,
                            [],
                        )
                    ],
                }
                for question in questions
            ],
        }

    @staticmethod
    def _serialize_summary(
        quiz: Any,
        *,
        question_count: int,
    ) -> dict[str, Any]:
        return {
            "quiz_id": quiz.quiz_id,
            "subject_id": quiz.subject_id,
            "title": quiz.title,
            "status": quiz.status,
            "question_count": question_count,
        }
