from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import (
    get_chat_service,
    router,
)


class FakeChatService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def ask(self, question):
        self.calls.append(question)
        return self.result


def make_client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[
        get_chat_service
    ] = lambda: service

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
        },
    )

    assert response.status_code == 200
    assert response.json() == service.result
    assert service.calls == [
        "Cloud computing là gì?"
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