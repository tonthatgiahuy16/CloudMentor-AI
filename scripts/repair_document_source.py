import os
from argparse import ArgumentParser
from pathlib import Path

from app.core.database import SessionLocal
from app.repos.document_repository import (
    DocumentRepository,
)
from app.services.document_source_repair_service import (
    DocumentSourceRepairService,
)


def parse_args(
    argv: list[str] | None = None,
):
    parser = ArgumentParser(
        description=(
            "Attach a retained source file to a legacy "
            "document record."
        )
    )
    parser.add_argument(
        "--document-id",
        required=True,
        help="Existing PostgreSQL document identifier.",
    )
    parser.add_argument(
        "--source-path",
        required=True,
        type=Path,
        help="Path to the original PDF source.",
    )
    parser.add_argument(
        "--upload-dir",
        type=Path,
        default=Path(
            os.getenv(
                "CLOUDMENTOR_UPLOAD_DIR",
                "storage/uploads",
            )
        ),
        help=(
            "Canonical upload directory. "
            "Default: storage/uploads."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Copy the source and attach metadata. "
            "Without this flag, only show a preview."
        ),
    )

    return parser.parse_args(argv)


def print_plan(plan) -> None:
    print(f"Document ID: {plan.document_id}")
    print(f"Source: {plan.source_path}")
    print(f"Target: {plan.target_path}")
    print(f"Source URI: {plan.source_uri}")
    print(f"SHA-256: {plan.content_sha256}")
    print(
        f"File size: {plan.file_size_bytes} bytes"
    )


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)
        repair_service = (
            DocumentSourceRepairService(
                document_repo=document_repo,
                upload_dir=args.upload_dir,
            )
        )

        plan = repair_service.plan(
            document_id=args.document_id,
            source_path=args.source_path,
        )

        print_plan(plan)

        if not args.apply:
            print(
                "Dry run only. Re-run with --apply "
                "to repair this document."
            )
            return 0

        repair_service.apply(plan)

        print(
            "Document source repair completed."
        )
        return 0

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"Repair failed: {exc}")
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
