from typing import Any


class SubjectRestoreService:
    """
    Phục hồi subject từ Trash bằng cách xây lại
    Chroma từ retained source của các document.
    """

    def __init__(
        self,
        subject_repo: Any,
        document_repo: Any,
        pdf_service: Any,
    ):
        self.subject_repo = subject_repo
        self.document_repo = document_repo
        self.pdf_service = pdf_service

    def restore(
        self,
        subject_id: str,
    ) -> dict[str, Any]:
        subject = self.subject_repo.get_by_id(
            subject_id
        )

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status == "ACTIVE":
            return {
                "subject_id": subject_id,
                "status": "ACTIVE",
                "processed_documents": 0,
                "indexed_chunks": 0,
            }

        self.subject_repo.mark_restoring(
            subject_id
        )

        try:
            documents = (
                self.document_repo
                .list_active_by_subject(
                    subject_id
                )
            )

            indexed_chunks = 0

            for document in documents:
                indexed_chunks += (
                    self.pdf_service
                    .rebuild_retained_document(
                        document
                    )
                )

            active_subject = (
                self.subject_repo.mark_active(
                    subject_id
                )
            )
        except Exception as exc:
            self.subject_repo.mark_restore_failed(
                subject_id=subject_id,
                error_message=str(exc),
            )
            raise

        return {
            "subject_id": (
                active_subject.subject_id
            ),
            "status": active_subject.status,
            "processed_documents": len(documents),
            "indexed_chunks": indexed_chunks,
        }
