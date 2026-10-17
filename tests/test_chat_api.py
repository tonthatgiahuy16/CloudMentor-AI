from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace
from app.api.chat import (
    get_chat_service,
    get_chat_subject_repository,
    router,
)


class FakeChatService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def ask(
        self,
        question,
        subject_id=None,
        ):
        self.calls.append((question, subject_id))
        return self.result


DEFAULT_SUBJECT = object()


class FakeSubjectRepository:
    def __init__(self, subject):
        self.subject = subject
        self.calls = []

    def get_by_id(self, subject_id):
        self.calls.append(subject_id)
        return self.subject


def make_client(
    service,
    subject=DEFAULT_SUBJECT,
):
    if subject is DEFAULT_SUBJECT:
        subject = SimpleNamespace(
            subject_id="subject-1",
            status="ACTIVE",
        )

    subject_repo = FakeSubjectRepository(
        subject
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[
        get_chat_service
    ] = lambda: service
    app.dependency_overrides[
        get_chat_subject_repository
    ] = lambda: subject_repo

    return TestClient(app)


def test_chat_returns_answer_and_sources():
    service = FakeChatService(
        result={
            "question": "Cloud computing là gì?",
            "answer": "Cloud computing cung cấp tài nguyên qua Internet.",
            "sources": [
                {
                    "chunk_id": "chunk-1",
                    "document_id": "document-1",
                    "chunk_index": 0,
                    "source": "chapter-1.pdf",
                    "page": 4,
                    "distance": 0.123,
                }
            ],
        }
    )
    client = make_client(service)

    response = client.post(
        "/chat/",
        json={
            "question": "Cloud computing là gì?",
            "subject_id": "subject-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == service.result
    assert service.calls == [
        ("Cloud computing là gì?",
         "subject-1",
        )
    ]


def test_chat_rejects_blank_question():
    service = FakeChatService(
        result={
            "question": "",
            "answer": "",
            "sources": [],
        }
    )
    client = make_client(service)

    response = client.post(
        "/chat/",
        json={
            "question": "   ",
        },
    )

    assert response.status_code == 422
    assert service.calls == []

def test_chat_service_is_reused(monkeypatch):
    from app.services import chat_service

    created = []

    class FakeService:
        def __init__(self):
            created.append(self)

    monkeypatch.setattr(chat_service, "ChatService", FakeService)
    get_chat_service.cache_clear()

    try:
        first = get_chat_service()
        second = get_chat_service()

        assert first is second
        assert len(created) == 1
    finally:
        get_chat_service.cache_clear()

def test_chat_passes_subject_id_to_service():
    service = FakeChatService(
        result={
            "question": "AWS là gì?",
            "answer": "AWS là nền tảng cloud.",
            "sources": [],
        }
    )
    client = make_client(service)

    response = client.post(
        "/chat/",
        json={
            "question": "AWS là gì?",
            "subject_id": "subject-1",
        },
    )

    assert response.status_code == 200
    assert service.calls == [
        ("AWS là gì?", "subject-1"),
    ]


def test_chat_requires_subject_id():
    service = FakeChatService(
        result={
            "question": "Cloud là gì?",
            "answer": "Answer",
            "sources": [],
        }
    )
    client = make_client(service)

    response = client.post(
        "/chat/",
        json={
            "question": "Cloud là gì?"
        },
    )

    assert response.status_code == 422
    assert service.calls == []


def test_chat_rejects_subject_in_trash_before_retrieval():
    service = FakeChatService(
        result={
            "question": "Cloud là gì?",
            "answer": "Answer",
            "sources": [],
        }
    )
    subject = SimpleNamespace(
        subject_id="subject-deleted",
        status="DELETED",
    )
    client = make_client(
        service,
        subject=subject,
    )

    response = client.post(
        "/chat/",
        json={
            "question": "Cloud là gì?",
            "subject_id": "subject-deleted",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Subject is not active"
    }
    assert service.calls == []


def test_chat_rejects_missing_subject_before_retrieval():
    service = FakeChatService(
        result={
            "question": "Cloud là gì?",
            "answer": "Answer",
            "sources": [],
        }
    )
    client = make_client(
        service,
        subject=None,
    )

    response = client.post(
        "/chat/",
        json={
            "question": "Cloud là gì?",
            "subject_id": "missing-subject",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Subject not found"
    }
    assert service.calls == []
