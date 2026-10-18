import pytest

from app.models.document import Document
from app.models.chunk import Chunk

@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (
            {"page": 3},
            (3, None, None),
        ),
        (
            {"line_range": (4, 9)},
            (None, (4, 9), None),
        ),
        (
            {"paragraph_range": (2, 5)},
            (None, None, (2, 5)),
        ),
    ],
)
def test_document_accepts_exactly_one_source_location(
    location,
    expected,
):
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson",
        text="content",
        **location,
    )

    assert (
        document.page,
        document.line_range,
        document.paragraph_range,
    ) == expected


@pytest.mark.parametrize(
    "location",
    [
        {},
        {
            "page": 1,
            "line_range": (1, 2),
        },
        {
            "page": 1,
            "paragraph_range": (1, 2),
        },
        {
            "line_range": (1, 2),
            "paragraph_range": (1, 2),
        },
    ],
)
def test_document_requires_exactly_one_source_location(
    location,
):
    with pytest.raises(
        ValueError,
        match="exactly one source location",
    ):
        Document(
            document_id="document-1",
            subject_id="subject-1",
            source="lesson",
            text="content",
            **location,
        )


@pytest.mark.parametrize(
    "location",
    [
        {"page": 0},
        {"page": -1},
        {"line_range": (0, 2)},
        {"line_range": (4, 3)},
        {"paragraph_range": (0, 2)},
        {"paragraph_range": (4, 3)},
    ],
)
def test_document_rejects_invalid_source_location_bounds(
    location,
):
    with pytest.raises(
        ValueError,
        match=(
            "source locations must use "
            "positive ordered positions"
        ),
    ):
        Document(
            document_id="document-1",
            subject_id="subject-1",
            source="lesson",
            text="content",
            **location,
        )


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (
            {"page": 3},
            (3, None, None),
        ),
        (
            {"line_range": (4, 9)},
            (None, (4, 9), None),
        ),
        (
            {"paragraph_range": (2, 5)},
            (None, None, (2, 5)),
        ),
    ],
)
def test_chunk_accepts_exactly_one_source_location(
    location,
    expected,
):
    chunk = Chunk(
        id="chunk-1",
        document_id="document-1",
        subject_id="subject-1",
        chunk_index=0,
        source="lesson",
        text="content",
        **location,
    )

    assert (
        chunk.page,
        chunk.line_range,
        chunk.paragraph_range,
    ) == expected


@pytest.mark.parametrize(
    "location",
    [
        {},
        {
            "page": 1,
            "line_range": (1, 2),
        },
        {
            "page": 1,
            "paragraph_range": (1, 2),
        },
        {
            "line_range": (1, 2),
            "paragraph_range": (1, 2),
        },
    ],
)
def test_chunk_requires_exactly_one_source_location(
    location,
):
    with pytest.raises(
        ValueError,
        match="exactly one source location",
    ):
        Chunk(
            id="chunk-1",
            document_id="document-1",
            subject_id="subject-1",
            chunk_index=0,
            source="lesson",
            text="content",
            **location,
        )


@pytest.mark.parametrize(
    "location",
    [
        {"page": 0},
        {"page": -1},
        {"line_range": (0, 2)},
        {"line_range": (4, 3)},
        {"paragraph_range": (0, 2)},
        {"paragraph_range": (4, 3)},
    ],
)
def test_chunk_rejects_invalid_source_location_bounds(
    location,
):
    with pytest.raises(
        ValueError,
        match=(
            "source locations must use "
            "positive ordered positions"
        ),
    ):
        Chunk(
            id="chunk-1",
            document_id="document-1",
            subject_id="subject-1",
            chunk_index=0,
            source="lesson",
            text="content",
            **location,
        )
