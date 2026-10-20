import argparse
import sys
from app.core.database import SessionLocal
from app.rag.vector_store import VectorStore
from app.repos.document_repository import (
    DocumentRepository,
)
from app.services.postgres_chroma_reconciliation_service import (
    PostgresChromaReconciliationService,
)
from app.services.pdf_service import PDFService
from app.storage.source_storage_factory import (
    create_source_storage,
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


def print_repair_plan(plan) -> None:
    print("repair_mode=dry-run")

    for chunk_id in plan.delete_orphan_chunk_ids:
        print(
            "repair_action=delete_orphan_chunk "
            f"target_id={chunk_id} "
            "status=planned"
        )

    for document_id in plan.rebuild_document_ids:
        print(
            "repair_action=rebuild_document "
            f"target_id={document_id} "
            "status=planned"
        )


def print_repair_result(result) -> None:
    print("repair_mode=apply")

    for chunk_id in result.deleted_orphan_chunk_ids:
        print(
            "repair_action=delete_orphan_chunk "
            f"target_id={chunk_id} "
            "status=applied"
        )

    for document_id in result.rebuilt_document_ids:
        print(
            "repair_action=rebuild_document "
            f"target_id={document_id} "
            "status=applied"
        )

    for failure in result.failed_actions:
        print(
            f"repair_action={failure.action} "
            f"target_id={failure.target_id} "
            "status=failed "
            f"error={failure.error_message}"
        )

    print(
        "repair_summary "
        "deleted_orphan_chunks="
        f"{len(result.deleted_orphan_chunk_ids)} "
        "rebuilt_documents="
        f"{len(result.rebuilt_document_ids)} "
        "rebuilt_chunks="
        f"{result.rebuilt_chunk_count} "
        "failed_actions="
        f"{len(result.failed_actions)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repair",
        action="store_true",
        help="Print a controlled reconciliation repair plan",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply a reconciliation repair plan",
    )

    args = parser.parse_args([] if argv is None else argv)

    if args.apply and not args.repair:
        parser.error("--apply requires --repair")

    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)
        vector_store = VectorStore()

        service = PostgresChromaReconciliationService(
            document_repo=document_repo,
            vector_store=vector_store,
        )

        if args.repair and not args.apply:
            plan = service.plan_repair()
            print_repair_plan(plan)

            if plan.is_empty:
                print("Repair plan is empty.")
                return 0

            return 1

        if args.repair and args.apply:
            pdf_service = PDFService(
                document_repo,
                source_storage=create_source_storage(),
            )

            result = service.apply_repair(
                document_rebuilder=(
                    pdf_service.rebuild_retained_document
                )
            )
            print_repair_result(result)
            return 0 if not result.failed_actions else 1

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
    raise SystemExit(main(sys.argv[1:]))
