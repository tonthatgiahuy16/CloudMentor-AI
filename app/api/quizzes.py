from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import SessionLocal
from app.core.demo_mode import require_mutations_enabled
from app.repos.quiz_repository import QuizRepository
from app.schemas.quiz import (
    AttemptResult,
    AttemptStartRequest,
    AttemptStartResponse,
    AttemptSubmitRequest,
    QuizCreate,
    QuizCreateResponse,
    QuizOverview,
    QuizPublic,
    QuizPublishResponse,
    QuizQuestionCreate,
    QuizQuestionPublic,
    QuizSummary,
)
from app.services.quiz_authoring_service import (
    QuizAuthoringService,
)
from app.services.quiz_grading_service import (
    QuizGradingService,
)


router = APIRouter(
    prefix="/quizzes",
    tags=["Quizzes"],
)


def get_quiz_repository():
    db = SessionLocal()

    try:
        yield QuizRepository(db)

    finally:
        db.close()


def get_quiz_authoring_service(
    quiz_repo=Depends(get_quiz_repository),
):
    return QuizAuthoringService(quiz_repo)


def get_quiz_grading_service(
    quiz_repo=Depends(get_quiz_repository),
):
    return QuizGradingService(quiz_repo)


def _not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=message,
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message,
    )


@router.post(
    "/",
    response_model=QuizCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz(
    payload: QuizCreate,
    _=Depends(require_mutations_enabled),
    authoring_service=Depends(get_quiz_authoring_service),
):
    return authoring_service.create_quiz(
        subject_id=payload.subject_id,
        title=payload.title,
    )


@router.get(
    "/",
    response_model=list[QuizSummary],
)
def list_quizzes(
    subject_id: str = Query(min_length=1),
    authoring_service=Depends(get_quiz_authoring_service),
):
    return authoring_service.list_published_quizzes(
        subject_id=subject_id,
    )


@router.post(
    "/{quiz_id}/questions",
    response_model=QuizQuestionPublic,
    status_code=status.HTTP_201_CREATED,
)
def add_question(
    quiz_id: str,
    payload: QuizQuestionCreate,
    _=Depends(require_mutations_enabled),
    authoring_service=Depends(get_quiz_authoring_service),
):
    try:
        return authoring_service.add_question(
            quiz_id=quiz_id,
            prompt=payload.prompt,
            options=[
                {
                    "text": option.text,
                    "is_correct": option.is_correct,
                }
                for option in payload.options
            ],
            source_document_id=(
                payload.source_document_id
            ),
            source_document_version=(
                payload.source_document_version
            ),
        )
    except RuntimeError as exc:
        message = str(exc)
        if message == "Quiz not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.post(
    "/{quiz_id}/publish",
    response_model=QuizPublishResponse,
)
def publish_quiz(
    quiz_id: str,
    _=Depends(require_mutations_enabled),
    authoring_service=Depends(get_quiz_authoring_service),
):
    try:
        return authoring_service.publish_quiz(quiz_id)
    except RuntimeError as exc:
        message = str(exc)
        if message == "Quiz not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.get(
    "/{quiz_id}/overview",
    response_model=QuizOverview,
)
def get_quiz_overview(
    quiz_id: str,
    grading_service=Depends(get_quiz_grading_service),
):
    try:
        return grading_service.get_overview(quiz_id)
    except RuntimeError as exc:
        message = str(exc)
        if message == "Quiz not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.post(
    "/{quiz_id}/attempts",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_attempt(
    quiz_id: str,
    payload: AttemptStartRequest,
    _=Depends(require_mutations_enabled),
    grading_service=Depends(get_quiz_grading_service),
):
    try:
        return grading_service.start_attempt(
            quiz_id=quiz_id,
            employee_id=payload.employee_id,
        )
    except RuntimeError as exc:
        message = str(exc)
        if message == "Quiz not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.get(
    "/{quiz_id}/attempts",
    response_model=list[AttemptResult],
)
def list_attempt_results(
    quiz_id: str,
    grading_service=Depends(get_quiz_grading_service),
):
    try:
        return grading_service.list_attempt_results(quiz_id)
    except RuntimeError as exc:
        message = str(exc)
        if message == "Quiz not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptResult,
)
def get_attempt_result(
    attempt_id: str,
    grading_service=Depends(get_quiz_grading_service),
):
    try:
        return grading_service.get_result(attempt_id)
    except RuntimeError as exc:
        message = str(exc)
        if message == "Attempt not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=AttemptResult,
)
def submit_attempt(
    attempt_id: str,
    payload: AttemptSubmitRequest,
    _=Depends(require_mutations_enabled),
    grading_service=Depends(get_quiz_grading_service),
):
    try:
        return grading_service.submit_attempt(
            attempt_id=attempt_id,
            answers=[
                {
                    "question_id": answer.question_id,
                    "option_id": answer.option_id,
                }
                for answer in payload.answers
            ],
        )
    except RuntimeError as exc:
        message = str(exc)
        if message == "Attempt not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc


@router.get(
    "/{quiz_id}",
    response_model=QuizPublic,
)
def get_quiz(
    quiz_id: str,
    authoring_service=Depends(get_quiz_authoring_service),
):
    try:
        return authoring_service.get_published_quiz(
            quiz_id
        )
    except RuntimeError as exc:
        message = str(exc)
        if message == "Quiz not found":
            raise _not_found(message) from exc
        raise _conflict(message) from exc
