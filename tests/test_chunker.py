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


def test_chunk_ids_are_deterministic_for_same_input():
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson.txt",
        text="abcdefghijklmno",
        line_range=(1, 1),
    )

    chunker = TextChunker(
        chunk_size=8,
        overlap=3,
    )

    first_run = chunker.split([document])
    second_run = chunker.split([document])

    first_ids = [chunk.id for chunk in first_run]
    second_ids = [chunk.id for chunk in second_run]

    assert first_ids == second_ids
    assert len(set(first_ids)) == len(first_ids)


def test_chunk_id_changes_with_content_or_chunking_config():
    original = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson.txt",
        text="abcdefgh",
        line_range=(1, 1),
    )
    changed_content = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson.txt",
        text="abcdXfgh",
        line_range=(1, 1),
    )

    original_chunk = TextChunker(
        chunk_size=8,
        overlap=0,
    ).split([original])[0]

    changed_content_chunk = TextChunker(
        chunk_size=8,
        overlap=0,
    ).split([changed_content])[0]

    changed_config_chunk = TextChunker(
        chunk_size=10,
        overlap=0,
    ).split([original])[0]

    assert original_chunk.id != changed_content_chunk.id
    assert original_chunk.id != changed_config_chunk.id


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


@pytest.mark.parametrize(
    "location",
    [
        {
            "line_range": (3, 3),
        },
        {
            "paragraph_range": (2, 2),
        },
    ],
)
def test_chunker_preserves_non_page_source_location(
    location,
):
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson",
        text="abcdefgh",
        **location,
    )

    chunks = TextChunker(
        chunk_size=5,
        overlap=1,
    ).split([document])

    assert len(chunks) == 2

    for chunk in chunks:
        assert chunk.page == document.page
        assert (
            chunk.line_range
            == document.line_range
        )
        assert (
            chunk.paragraph_range
            == document.paragraph_range
        )


@pytest.mark.parametrize(
    (
        "location",
        "expected_line_ranges",
        "expected_paragraph_ranges",
    ),
    [
        (
            {
                "line_range": (10, 12),
            },
            [
                (10, 11),
                (11, 12),
                (12, 12),
            ],
            [None, None, None],
        ),
        (
            {
                "paragraph_range": (4, 6),
            },
            [None, None, None],
            [
                (4, 5),
                (5, 6),
                (6, 6),
            ],
        ),
    ],
)
def test_chunker_calculates_exact_source_ranges(
    location,
    expected_line_ranges,
    expected_paragraph_ranges,
):
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson",
        text="aaaa\nbbbb\ncccc",
        **location,
    )

    chunks = TextChunker(
        chunk_size=6,
        overlap=0,
    ).split([document])

    assert [
        chunk.text
        for chunk in chunks
    ] == [
        "aaaa\nb",
        "bbb\ncc",
        "cc",
    ]
    assert [
        chunk.line_range
        for chunk in chunks
    ] == expected_line_ranges
    assert [
        chunk.paragraph_range
        for chunk in chunks
    ] == expected_paragraph_ranges

@pytest.mark.parametrize(
    "location",
    [
        {
            "line_range": (3, 4),
        },
        {
            "paragraph_range": (2, 3),
        },
    ],
)
def test_chunker_rejects_source_range_that_does_not_match_text(
    location,
):
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson",
        text="only one unit",
        **location,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Source range does not match "
            "text boundaries"
        ),
    ):
        TextChunker(
            chunk_size=10,
            overlap=0,
        ).split([document])


def test_chunker_calculates_ranges_with_overlap():
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson.txt",
        text="1111\n2222\n3333",
        line_range=(10, 12),
    )

    chunks = TextChunker(
        chunk_size=8,
        overlap=3,
    ).split([document])

    assert [
        chunk.text
        for chunk in chunks
    ] == [
        "1111\n222",
        "2222\n333",
        "3333",
    ]
    assert [
        chunk.line_range
        for chunk in chunks
    ] == [
        (10, 11),
        (11, 12),
        (12, 12),
    ]


def test_chunker_does_not_claim_next_unit_at_newline_boundary():
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson.txt",
        text="aaaa\nbbbb",
        line_range=(10, 11),
    )

    chunks = TextChunker(
        chunk_size=5,
        overlap=0,
    ).split([document])

    assert [
        chunk.text
        for chunk in chunks
    ] == [
        "aaaa\n",
        "bbbb",
    ]
    assert [
        chunk.line_range
        for chunk in chunks
    ] == [
        (10, 10),
        (11, 11),
    ]
