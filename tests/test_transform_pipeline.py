import pytest
from app.models.document import Document
from app.pipeline.transform_pipeline import TransformPipeline


def test_transform_pipeline_cleans_without_mutating_input():
    document = Document(
        document_id="doc-1",
        subject_id="subject-1",
        page=1,
        source="lesson.pdf",
        text="  alpha   beta gamma ",
    )
    pipeline = TransformPipeline()

    transformed = pipeline.run([document])

    assert [item.text for item in transformed] == ["alpha beta gamma"]
    assert document.text == "  alpha   beta gamma "
    assert transformed[0].page == 1
    assert transformed[0].document_id == "doc-1"
    assert transformed[0].subject_id == "subject-1"


@pytest.mark.parametrize(
    "location",
    [
        {
            "line_range": (3, 7),
        },
        {
            "paragraph_range": (2, 4),
        },
    ],
)
def test_transform_pipeline_preserves_source_location(
    location,
):
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson",
        text="  alpha   beta  ",
        **location,
    )

    transformed = TransformPipeline().run(
        [document]
    )

    assert len(transformed) == 1
    assert transformed[0].text == "alpha beta"
    assert (
        transformed[0].page
        == document.page
    )
    assert (
        transformed[0].line_range
        == document.line_range
    )
    assert (
        transformed[0].paragraph_range
        == document.paragraph_range
    )


@pytest.mark.parametrize(
    "location",
    [
        {
            "line_range": (10, 12),
        },
        {
            "paragraph_range": (4, 6),
        },
    ],
)
def test_transform_pipeline_preserves_text_boundaries(
    location,
):
    document = Document(
        document_id="document-1",
        subject_id="subject-1",
        source="lesson",
        text=(
            " first   unit \n"
            " second\tunit\n"
            " third unit "
        ),
        **location,
    )

    transformed = TransformPipeline().run(
        [document]
    )

    assert transformed[0].text == (
        "first unit\n"
        "second unit\n"
        "third unit"
    )
