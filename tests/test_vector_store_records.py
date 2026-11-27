from unittest.mock import Mock, call

import pytest

from app.rag.vector_store import VectorStore
from app.models.chunk import Chunk

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


def test_add_serializes_source_locations_without_null_metadata():
    vector_store = VectorStore.__new__(
        VectorStore
    )
    vector_store.collection = Mock()

    embeddings = Mock()
    embeddings.tolist.return_value = [
        [0.1],
        [0.2],
        [0.3],
    ]

    chunks = [
        Chunk(
            id="pdf-chunk",
            document_id="pdf-document",
            subject_id="subject-1",
            chunk_index=0,
            source="lesson.pdf",
            text="PDF content",
            page=2,
        ),
        Chunk(
            id="txt-chunk",
            document_id="txt-document",
            subject_id="subject-1",
            chunk_index=0,
            source="lesson.txt",
            text="TXT content",
            line_range=(3, 7),
        ),
        Chunk(
            id="docx-chunk",
            document_id="docx-document",
            subject_id="subject-1",
            chunk_index=0,
            source="lesson.docx",
            text="DOCX content",
            paragraph_range=(4, 6),
        ),
    ]

    vector_store.add(
        chunks,
        embeddings,
    )

    call_kwargs = (
        vector_store.collection
        .add.call_args.kwargs
    )

    assert call_kwargs["ids"] == [
        "pdf-chunk",
        "txt-chunk",
        "docx-chunk",
    ]
    assert call_kwargs["metadatas"] == [
        {
            "chunk_index": 0,
            "document_id": "pdf-document",
            "subject_id": "subject-1",
            "source": "lesson.pdf",
            "page": 2,
        },
        {
            "chunk_index": 0,
            "document_id": "txt-document",
            "subject_id": "subject-1",
            "source": "lesson.txt",
            "line_start": 3,
            "line_end": 7,
        },
        {
            "chunk_index": 0,
            "document_id": "docx-document",
            "subject_id": "subject-1",
            "source": "lesson.docx",
            "paragraph_start": 4,
            "paragraph_end": 6,
        },
    ]
    assert call_kwargs["embeddings"] == [
        [0.1],
        [0.2],
        [0.3],
    ]


def test_delete_by_chunk_ids_deletes_existing_ids_once():
    vector_store = VectorStore.__new__(VectorStore)
    vector_store.collection = Mock()

    vector_store.collection.get.side_effect = [
        {
            "ids": [
                "orphan-document:0",
                "orphan-document:1",
            ]
        },
        {"ids": []},
    ]

    first_count = vector_store.delete_by_chunk_ids(
        [
            "orphan-document:0",
            "orphan-document:1",
        ]
    )
    second_count = vector_store.delete_by_chunk_ids(
        [
            "orphan-document:0",
            "orphan-document:1",
        ]
    )

    assert first_count == 2
    assert second_count == 0

    vector_store.collection.get.assert_has_calls(
        [
            call(
                ids=[
                    "orphan-document:0",
                    "orphan-document:1",
                ]
            ),
            call(
                ids=[
                    "orphan-document:0",
                    "orphan-document:1",
                ]
            ),
        ]
    )
    vector_store.collection.delete.assert_called_once_with(
        ids=[
            "orphan-document:0",
            "orphan-document:1",
        ]
    )


def test_vector_store_init_rejects_mismatched_collection_space(monkeypatch):
    fake_collection = Mock()
    fake_collection.metadata = {"hnsw:space": "l2"}
    fake_client = Mock()
    fake_client.get_or_create_collection.return_value = fake_collection

    monkeypatch.setattr(
        "app.rag.vector_store.chromadb.PersistentClient",
        lambda path: fake_client,
    )

    with pytest.raises(RuntimeError, match="rebuild_vector_collection"):
        VectorStore(collection_name="cloudmentor")


def test_vector_store_init_accepts_matching_cosine_space(monkeypatch):
    fake_collection = Mock()
    fake_collection.metadata = {"hnsw:space": "cosine"}
    fake_client = Mock()
    fake_client.get_or_create_collection.return_value = fake_collection

    monkeypatch.setattr(
        "app.rag.vector_store.chromadb.PersistentClient",
        lambda path: fake_client,
    )

    store = VectorStore(collection_name="cloudmentor")
    assert store.collection is fake_collection
