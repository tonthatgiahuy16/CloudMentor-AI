import os
from pathlib import Path

from app.storage.source_storage import (
    LocalSourceStorage,
)

from argparse import (
    ArgumentParser,
    ArgumentTypeError,
)
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.repos.document_repository import (
    DocumentRepository,
)
from app.services.ingestion_recovery_service import (
    IngestionRecoveryService,
)
from app.services.pdf_service import PDFService


def get_source_storage() -> LocalSourceStorage:
    return LocalSourceStorage(
        root=Path(
            os.getenv(
                "CLOUDMENTOR_UPLOAD_DIR",
                "storage/uploads",
            )
        )
    )


def positive_minutes(value: str) -> int:
    minutes = int(value)

    if minutes <= 0:
        raise ArgumentTypeError(
            "stale-after-minutes must be greater than zero"
        )

    return minutes


def parse_args():
    parser = ArgumentParser(
        description=(
            "Find and recover stale document ingestions."
        )
    )
    parser.add_argument(
        "--stale-after-minutes",
        type=positive_minutes,
        default=60,
        help=(
            "Treat an inactive ingestion as stale after "
            "this many minutes. Default: 60."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Recover matching documents. Without this "
            "flag, only display a dry-run preview."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    stale_before = (
        datetime.now(timezone.utc)
        - timedelta(
            minutes=args.stale_after_minutes
        )
    )

    db = SessionLocal()

    try:
        document_repo = DocumentRepository(db)

        documents = (
            document_repo.list_stale_ingestions(
                stale_before=stale_before,
            )
        )

        print(
            "Stale cutoff: "
            f"{stale_before.isoformat()}"
        )
        print(
            f"Candidates: {len(documents)}"
        )

        for document in documents:
            print(
                "- "
                f"{document.document_id} "
                f"status={document.status} "
                f"stage={document.current_stage}"
            )

        if not args.apply:
            print(
                "Dry run only. Re-run with --apply "
                "to recover these documents."
            )
            return 0

        source_storage = get_source_storage()

        recovery_service = (
            IngestionRecoveryService(
                document_repo=document_repo,
                pdf_service=PDFService(
                    document_repo,
                    source_storage=source_storage,
                ),
            )
        )

        result = recovery_service.recover(
            stale_before=stale_before,
        )

        print(
            "Recovery complete: "
            f"discovered={result['discovered']}, "
            f"recovered={result['recovered']}, "
            f"failed={result['failed']}"
        )

        for failure in result["failures"]:
            print(
                "- recovery failed: "
                f"{failure['document_id']}: "
                f"{failure['error_message']}"
            )

        if result["failed"] > 0:
            return 1

        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
