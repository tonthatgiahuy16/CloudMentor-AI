from typing import Any


class DocumentDeletionService:
    """
    Điều phối việc xóa derived data (dữ liệu phát sinh)
    trong Chroma và soft delete (xóa mềm) trong PostgreSQL.
    """

    def __init__(
        self,
        document_repo: Any,
        vector_store: Any,
    ):
        self.document_repo = document_repo
        self.vector_store = vector_store

    def delete(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        document = self.document_repo.get_by_id(
            document_id
        )

        if document is None:
            raise RuntimeError("Document not found")

        if document.status == "DELETED":
            return {
                "document_id": document_id,
                "status": "DELETED",
                "deleted_chunks": 0,
            }

        deleted_chunks = (
            self.vector_store.delete_by_document_id(
                document_id
            )
        )

        deleted_document = self.document_repo.mark_deleted(
            document_id
        )

        return {
            "document_id": deleted_document.document_id,
            "status": deleted_document.status,
            "deleted_chunks": deleted_chunks,
        }