import pytest

from app.services.chat_service import ChatService


class FakeEmbedder:
    def embed_query(self, question):
        assert question == "What is cloud computing?"
        return [0.1, 0.2]


class FakeRetriever:
    def search(self, vector):
        assert vector == [0.1, 0.2]
        return [
            {
                "chunk_id": "chunk-1",
                "document": "Cloud computing provides on-demand resources.",
                "metadata": {
                    "document_id": "doc-1",
                    "chunk_index": 0,
                    "source": "lesson.pdf",
                    "page": 4,
                },
                "distance": 0.12345,
            }
        ]


class FakeGenerator:
    def generate(self, question, contexts):
        assert question == "What is cloud computing?"
        assert "lesson.pdf" in contexts[0]
        return "An on-demand computing model."


def test_chat_service_orchestrates_dependencies_and_sources():
    service = ChatService(
        embedder=FakeEmbedder(),
        retriever=FakeRetriever(),
        generator=FakeGenerator(),
    )

    result = service.ask("  What is cloud computing?  ")

    assert result["answer"] == "An on-demand computing model."
    assert result["question"] == "What is cloud computing?"
    assert result["sources"][0]["distance"] == 0.123
    assert result["sources"][0]["page"] == 4


def test_chat_service_rejects_blank_question():
    service = ChatService(
        embedder=FakeEmbedder(),
        retriever=FakeRetriever(),
        generator=FakeGenerator(),
    )

    with pytest.raises(ValueError):
        service.ask("   ")


class EmptyRetriever:
    def search(self, vector):
        assert vector == [0.1, 0.2]
        return []


class GeneratorMustNotBeCalled:
    def generate(self, question, contexts):
        raise AssertionError(
            "Generator must not be called without context"
        )


def test_chat_service_does_not_generate_without_context():
    service = ChatService(
        embedder=FakeEmbedder(),
        retriever=EmptyRetriever(),
        generator=GeneratorMustNotBeCalled(),
    )

    result = service.ask(
        "What is cloud computing?"
    )

    assert result == {
        "question": "What is cloud computing?",
        "answer": (
            "Tôi không tìm thấy thông tin "
            "trong tài liệu."
        ),
        "sources": [],
    }

class RetrieverWithMissingLineage:
    def search(self, vector):
        assert vector == [0.1, 0.2]

        return [
            {
                "chunk_id": "legacy-chunk",
                "document": "Legacy document content.",
                "metadata": {
                    "chunk_index": 0,
                    "source": "legacy.pdf",
                    "page": 1,
                },
                "distance": 0.2,
            }
        ]


def test_chat_service_ignores_chunks_without_lineage():
    service = ChatService(
        embedder=FakeEmbedder(),
        retriever=RetrieverWithMissingLineage(),
        generator=GeneratorMustNotBeCalled(),
    )

    result = service.ask(
        "What is cloud computing?"
    )

    assert result == {
        "question": "What is cloud computing?",
        "answer": (
            "Tôi không tìm thấy thông tin "
            "trong tài liệu."
        ),
        "sources": [],
    }