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
