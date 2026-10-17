from unittest.mock import Mock

from app.rag.vector_store import VectorStore


def test_list_all_records_combines_ids_and_metadata():
    vector_store = VectorStore.__new__(
        VectorStore
    )
    vector_store.collection = Mock()
    vector_store.collection.get.return_value = {
        "ids": [
            "document-1:0",
            "orphan:0",
        ],
        "metadatas": [
            {
                "document_id": "document-1",
                "subject_id": "subject-1",
            },
            None,
        ],
    }

    records = vector_store.list_all_records()

    assert records == [
        {
            "chunk_id": "document-1:0",
            "document_id": "document-1",
            "subject_id": "subject-1",
        },
        {
            "chunk_id": "orphan:0",
        },
    ]
    vector_store.collection.get.assert_called_once_with(
        include=["metadatas"],
    )
