from typing import Any


class SubjectDeletionService:
    """
    Đưa môn học vào Trash, xóa dữ liệu dẫn xuất
    khỏi Chroma nhưng giữ metadata và source files.
    """

    def __init__(
        self,
        subject_repo: Any,
        document_repo: Any,
        vector_store: Any,
    ):
        self.subject_repo = subject_repo
        self.document_repo = document_repo
        self.vector_store = vector_store

    def delete(
        self,
        subject_id: str,
    ) -> dict[str, Any]:
        subject = self.subject_repo.get_by_id(
            subject_id
        )

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status == "DELETED":
            return {
                "subject_id": subject_id,
                "status": "DELETED",
                "processed_documents": 0,
                "deleted_chunks": 0,
            }

        self.subject_repo.mark_deleting(
            subject_id
        )

        try:
            documents = (
                self.document_repo
                .list_active_by_subject(
                    subject_id
                )
            )

            deleted_chunks = 0

            for document in documents:
                deleted_chunks += (
                    self.vector_store
                    .delete_by_document_id(
                        document.document_id
                    )
                )

            deleted_subject = (
                self.subject_repo.mark_deleted(
                    subject_id
                )
            )
        except Exception as exc:
            self.subject_repo.mark_delete_failed(
                subject_id=subject_id,
                error_message=str(exc),
            )
            raise

        return {
            "subject_id": (
                deleted_subject.subject_id
            ),
            "status": deleted_subject.status,
            "processed_documents": len(documents),
            "deleted_chunks": deleted_chunks,
        }
