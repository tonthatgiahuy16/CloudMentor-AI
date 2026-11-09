from typing import Any

from app.repos.quiz_repository import QuizRepository


class QuizGradingService:
    """
    Chấm điểm quiz phía server.

    Client chỉ gửi lựa chọn của mình; answer key đọc từ PostgreSQL.
    Không bao giờ tin điểm hay đáp án do client cung cấp.
    """

    def __init__(self, quiz_repo: QuizRepository):
        self.quiz_repo = quiz_repo

    def start_attempt(
        self,
        *,
        quiz_id: str,
        employee_id: str,
    ) -> dict[str, Any]:
        quiz = self.quiz_repo.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        if quiz.status != "PUBLISHED":
            raise RuntimeError("Quiz is not published")

        attempt = self.quiz_repo.create_attempt(
            quiz_id=quiz_id,
            employee_id=employee_id,
        )

        return {
            "attempt_id": attempt.attempt_id,
            "quiz_id": attempt.quiz_id,
            "employee_id": attempt.employee_id,
            "status": attempt.status,
        }

    def submit_attempt(
        self,
        *,
        attempt_id: str,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        attempt = self.quiz_repo.get_attempt(attempt_id)

        if attempt is None:
            raise RuntimeError("Attempt not found")

        if attempt.status != "IN_PROGRESS":
            raise RuntimeError("Attempt already submitted")

        questions = self.quiz_repo.get_questions(
            attempt.quiz_id
        )

        if not questions:
            raise RuntimeError("Quiz has no questions")

        question_ids = [
            question.question_id for question in questions
        ]
        question_id_set = set(question_ids)

        selected_by_question: dict[str, str | None] = {}

        for answer in answers:
            question_id = answer["question_id"]

            if question_id not in question_id_set:
                raise RuntimeError(
                    "Answer references a question outside the quiz"
                )

            if question_id in selected_by_question:
                raise RuntimeError(
                    "Duplicate answer for a question"
                )

            selected_by_question[question_id] = (
                answer.get("option_id")
            )

        options_by_question = (
            self.quiz_repo.get_options_for_questions(
                question_ids
            )
        )

        for question_id, option_id in (
            selected_by_question.items()
        ):
            if option_id is None:
                continue

            valid_option_ids = {
                option.option_id
                for option in options_by_question.get(
                    question_id,
                    [],
                )
            }

            if option_id not in valid_option_ids:
                raise RuntimeError(
                    "Selected option does not belong to the question"
                )

        correct_options = self.quiz_repo.get_correct_options(
            question_ids
        )

        graded_answers: list[dict[str, Any]] = []
        correct_count = 0

        for question in questions:
            correct_option = correct_options.get(
                question.question_id
            )

            if correct_option is None:
                raise RuntimeError(
                    "Question has no approved answer key"
                )

            selected_option_id = (
                selected_by_question.get(question.question_id)
            )
            is_correct = (
                selected_option_id
                == correct_option.option_id
            )

            if is_correct:
                correct_count += 1

            graded_answers.append(
                {
                    "question_id": question.question_id,
                    "selected_option_id": (
                        selected_option_id
                    ),
                    "correct_option_id": (
                        correct_option.option_id
                    ),
                    "is_correct": is_correct,
                }
            )

        total_questions = len(questions)
        score = correct_count / total_questions

        attempt = self.quiz_repo.finalize_attempt(
            attempt_id=attempt_id,
            correct_count=correct_count,
            total_questions=total_questions,
            score=score,
            answers=[
                {
                    "question_id": answer["question_id"],
                    "selected_option_id": (
                        answer["selected_option_id"]
                    ),
                    "is_correct": answer["is_correct"],
                }
                for answer in graded_answers
            ],
        )

        return self._serialize_result(
            attempt,
            graded_answers,
        )

    def get_result(
        self,
        attempt_id: str,
    ) -> dict[str, Any]:
        attempt = self.quiz_repo.get_attempt(attempt_id)

        if attempt is None:
            raise RuntimeError("Attempt not found")

        if attempt.status != "GRADED":
            raise RuntimeError("Attempt is not graded")

        stored_answers = self.quiz_repo.get_attempt_answers(
            attempt_id
        )
        correct_options = self.quiz_repo.get_correct_options(
            [
                answer.question_id
                for answer in stored_answers
            ]
        )

        graded_answers = [
            {
                "question_id": answer.question_id,
                "selected_option_id": (
                    answer.selected_option_id
                ),
                "correct_option_id": (
                    correct_options[answer.question_id].option_id
                ),
                "is_correct": answer.is_correct,
            }
            for answer in stored_answers
        ]

        return self._serialize_result(
            attempt,
            graded_answers,
        )

    def get_overview(
        self,
        quiz_id: str,
    ) -> dict[str, Any]:
        quiz = self.quiz_repo.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        attempts = self.quiz_repo.list_attempts(quiz_id)
        graded_attempts = [
            attempt
            for attempt in attempts
            if attempt.status == "GRADED"
            and attempt.score is not None
        ]

        average_score = None
        if graded_attempts:
            average_score = sum(
                attempt.score
                for attempt in graded_attempts
            ) / len(graded_attempts)

        return {
            "quiz_id": quiz.quiz_id,
            "attempt_count": len(attempts),
            "graded_attempt_count": len(graded_attempts),
            "average_score": average_score,
        }

    def list_attempt_results(
        self,
        quiz_id: str,
    ) -> list[dict[str, Any]]:
        """
        Trả về lịch sử các lượt đã chấm của một quiz.

        Dữ liệu đọc từ PostgreSQL, sắp xếp mới nhất trước. Chỉ trả về
        các lượt GRADED vì lượt đang làm chưa có điểm để hiển thị.
        """
        quiz = self.quiz_repo.get_quiz(quiz_id)

        if quiz is None:
            raise RuntimeError("Quiz not found")

        graded_attempts = [
            attempt
            for attempt in self.quiz_repo.list_attempts(quiz_id)
            if attempt.status == "GRADED"
        ]

        graded_attempts.sort(
            key=lambda attempt: (
                attempt.graded_at is not None,
                attempt.graded_at,
                attempt.started_at,
            ),
            reverse=True,
        )

        answers_by_attempt = (
            self.quiz_repo.get_answers_for_attempts(
                [
                    attempt.attempt_id
                    for attempt in graded_attempts
                ]
            )
        )

        all_question_ids = sorted(
            {
                answer.question_id
                for answers in answers_by_attempt.values()
                for answer in answers
            }
        )
        correct_options = self.quiz_repo.get_correct_options(
            all_question_ids
        )

        results: list[dict[str, Any]] = []

        for attempt in graded_attempts:
            stored_answers = answers_by_attempt.get(
                attempt.attempt_id,
                [],
            )

            graded_answers = [
                {
                    "question_id": answer.question_id,
                    "selected_option_id": (
                        answer.selected_option_id
                    ),
                    "correct_option_id": (
                        correct_options[
                            answer.question_id
                        ].option_id
                        if answer.question_id in correct_options
                        else ""
                    ),
                    "is_correct": answer.is_correct,
                }
                for answer in stored_answers
            ]

            results.append(
                self._serialize_result(
                    attempt,
                    graded_answers,
                )
            )

        return results

    @staticmethod
    def _serialize_result(
        attempt: Any,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "attempt_id": attempt.attempt_id,
            "quiz_id": attempt.quiz_id,
            "employee_id": attempt.employee_id,
            "status": attempt.status,
            "score": attempt.score,
            "correct_count": attempt.correct_count,
            "total_questions": attempt.total_questions,
            "graded_at": attempt.graded_at,
            "answers": answers,
        }
