import pytest

from app.rag.retriever import Retriever


class FakeCollection:
    def __init__(self, result):
        self.result = result
        self.kwargs = None

    def query(self, **kwargs):
        self.kwargs = kwargs
        return self.result


class FakeStore:
    def __init__(self, result):
        self.collection = FakeCollection(result)


def test_retriever_maps_vector_store_result():
    store = FakeStore(
        {
            "ids": [["chunk-1"]],
            "documents": [["context"]],
            "metadatas": [[{"page": 3}]],
            "distances": [[0.12345]],
        }
    )

    results = Retriever(store).search([0.2, 0.8], top_k=2)

    assert results == [
        {
            "chunk_id": "chunk-1",
            "document": "context",
            "metadata": {"page": 3},
            "distance": 0.12345,
        }
    ]
    assert store.collection.kwargs["n_results"] == 2


def test_retriever_handles_empty_result():
    store = FakeStore(
        {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    )

    assert Retriever(store).search([1.0]) == []


def test_retriever_rejects_invalid_top_k():
    with pytest.raises(ValueError):
        Retriever(FakeStore({})).search([1.0], top_k=0)
