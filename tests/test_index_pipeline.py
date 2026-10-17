from unittest.mock import Mock

from app.pipeline.index_pipeline import IndexPipeline



def test_delete_by_document_id_delegates_to_vector_store():
    pipeline = IndexPipeline.__new__(
        IndexPipeline
    )
    pipeline.vector_store = Mock()
    pipeline.vector_store.delete_by_document_id.return_value = 3

    result = pipeline.delete_by_document_id(
        "document-id"
    )

    assert result == 3
    (
        pipeline.vector_store
        .delete_by_document_id
        .assert_called_once_with("document-id")
    )
