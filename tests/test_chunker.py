import pytest

from app.models.document import Document
from app.rag.chunker import TextChunker


def test_chunker_preserves_metadata_and_overlap():
    chunker = TextChunker(chunk_size=10, overlap=3)
    document = Document(
        document_id="doc-1", page=2, source="lesson.pdf", text="abcdefghijklmnop", subject_id="subject-1",
    )

    chunks = chunker.split([document])

    assert [chunk.text for chunk in chunks] == ["abcdefghij", "hijklmnop"]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert all(chunk.page == 2 for chunk in chunks)
    assert all(chunk.document_id == "doc-1" for chunk in chunks)
    assert all(chunk.subject_id == "subject-1" for chunk in chunks)


def test_chunk_indices_reset_for_each_document():
    chunker = TextChunker(chunk_size=5, overlap=0)

    chunks = chunker.split(
        [
            Document(
                document_id="a",
                subject_id="subject-a",
                page=1,
                source="a.pdf",
                text="abcdef",
            ),
            Document(
                document_id="b",
                subject_id="subject-b",
                page=1,
                source="b.pdf",
                text="ghijkl",
            ),
        ]
    )

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 0, 1]
    assert [chunk.subject_id for chunk in chunks] == [
        "subject-a",
        "subject-a",
        "subject-b",
        "subject-b",
    ]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_chunker_rejects_invalid_configuration(chunk_size, overlap):
    with pytest.raises(ValueError):
        TextChunker(chunk_size=chunk_size, overlap=overlap)
