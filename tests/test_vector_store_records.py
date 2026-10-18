from unittest.mock import Mock

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
