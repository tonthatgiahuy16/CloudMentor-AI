from app.core.database import SessionLocal
from app.rag.vector_store import VectorStore
from app.repos.document_repository import (
    DocumentRepository,
)
from app.services.postgres_chroma_reconciliation_service import (
    PostgresChromaReconciliationService,
)


def print_report(report) -> None:
    print(
        "Expected documents: "
        f"{report.expected_document_count}"
    )
    print(
        f"Chroma chunks: {report.actual_chunk_count}"
    )

    print(
        "Missing indexed documents: "
        f"{len(report.missing_document_ids)}"
    )

    for document_id in (
        report.missing_document_ids
    ):
        print(
            f"Missing document: {document_id}"
        )

    print(
        "Missing lineage chunks: "
        f"{len(report.missing_lineage_chunk_ids)}"
    )

    print(
        "Unknown document chunks: "
        f"{len(report.orphan_chunk_ids)}"
    )

    print(
        "Known non-expected documents: "
        f"{len(report.known_nonexpected_documents)}"
    )

    for document in (
        report.known_nonexpected_documents
    ):
        print(
            "Known non-expected document: "
            f"{document.document_id} "
            "document_status="
            f"{document.document_status} "
            "subject_status="
            f"{document.subject_status} "
            f"subject={document.subject_id} "
            f"chunks={document.chunk_count}"
        )

    print(
        "Subject mismatches: "
        f"{len(report.subject_mismatches)}"
    )

    for mismatch in report.subject_mismatches:
        print(
            "Subject mismatch: "
            f"{mismatch.chunk_id} "
            f"document={mismatch.document_id} "
            f"expected={mismatch.expected_subject_id} "
            f"actual={mismatch.actual_subject_id}"
        )


def main() -> int:
    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)
        vector_store = VectorStore()

        service = (
            PostgresChromaReconciliationService(
                document_repo=document_repo,
                vector_store=vector_store,
            )
        )

        report = service.audit()
        print_report(report)

        if report.is_consistent:
            print("Stores are consistent.")
            return 0

        print("Drift detected.")
        return 1

    except Exception as exc:
        print(f"Reconciliation audit failed: {exc}")
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
