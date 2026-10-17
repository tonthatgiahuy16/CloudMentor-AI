from datetime import datetime
from typing import Any


class IngestionRecoveryService:

    def __init__(
        self,
        document_repo: Any,
        pdf_service: Any,
    ):
        self.document_repo = document_repo
        self.pdf_service = pdf_service

    def recover(
        self,
        stale_before: datetime,
    ) -> dict[str, Any]:
        documents = (
            self.document_repo
            .list_stale_ingestions(
                stale_before=stale_before,
            )
        )

        recovered = 0
        failures = []

        for document in documents:
            try:
                self.pdf_service.recover_stale_document(
                    document
                )
            except Exception as exc:
                failures.append(
                    {
                        "document_id": (
                            document.document_id
                        ),
                        "error_message": str(exc),
                    }
                )
            else:
                recovered += 1

        return {
            "discovered": len(documents),
            "recovered": recovered,
            "failed": len(failures),
            "failures": failures,
        }
