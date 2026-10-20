from argparse import ArgumentParser

from app.core.database import SessionLocal
from app.repos.document_repository import (
    DocumentRepository,
)
from app.services.local_source_migration_service import (
    LocalSourceToMinioMigrationService,
)
from app.storage.source_storage_factory import (
    create_local_source_storage,
    create_minio_source_storage,
)


def parse_args(
    argv: list[str] | None = None,
):
    parser = ArgumentParser(
        description=(
            "Migrate retained local document sources "
            "to MinIO."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Write verified sources to MinIO and "
            "update PostgreSQL. Without this flag, "
            "only perform a dry run."
        ),
    )

    return parser.parse_args(argv)


def safe_output(value: object) -> str:
    return (
        str(value)
        .encode(
            "ascii",
            errors="backslashreplace",
        )
        .decode("ascii")
    )


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    db = SessionLocal()

    counts = {
        "eligible": 0,
        "already_minio": 0,
        "missing_metadata": 0,
        "applied": 0,
        "failed": 0,
    }

    try:
        document_repo = DocumentRepository(db)
        local_storage = (
            create_local_source_storage()
        )
        minio_storage = (
            create_minio_source_storage()
        )
        migration_service = (
            LocalSourceToMinioMigrationService(
                document_repo=document_repo,
                local_storage=local_storage,
                minio_storage=minio_storage,
            )
        )

        for document in document_repo.list_all():
            metadata = (
                document.source_uri,
                document.content_sha256,
                document.file_size_bytes,
            )

            if any(
                value is None
                for value in metadata
            ):
                counts["missing_metadata"] += 1
                print(
                    "skipped "
                    f"{safe_output(document.document_id)} "
                    "reason=missing_metadata"
                )
                continue

            if document.source_uri.startswith(
                "minio://"
            ):
                counts["already_minio"] += 1
                print(
                    "skipped "
                    f"{safe_output(document.document_id)} "
                    "reason=already_minio"
                )
                continue

            if "://" in document.source_uri:
                counts["failed"] += 1
                print(
                    "failed "
                    f"{safe_output(document.document_id)} "
                    "reason=unsupported_source_uri"
                )
                continue

            try:
                plan = migration_service.plan(
                    document_id=(
                        document.document_id
                    )
                )
                counts["eligible"] += 1

                print(
                    "eligible "
                    "document_id="
                    f"{safe_output(plan.document_id)} "
                    "source="
                    f"{safe_output(plan.current_source_uri)} "
                    "target="
                    f"{safe_output(plan.target_source_uri)}"
                )

                if args.apply:
                    migration_service.apply(plan)
                    counts["applied"] += 1
                    print(
                        "applied "
                        "document_id="
                        f"{safe_output(plan.document_id)}"
                    )

            except (
                OSError,
                RuntimeError,
                ValueError,
            ) as exc:
                counts["failed"] += 1
                print(
                    "failed "
                    "document_id="
                    f"{safe_output(document.document_id)} "
                    f"reason={safe_output(exc)}"
                )

        mode = (
            "apply"
            if args.apply
            else "dry-run"
        )
        print(f"mode={mode}")
        print(
            "counts "
            f"eligible={counts['eligible']} "
            f"already_minio="
            f"{counts['already_minio']} "
            f"missing_metadata="
            f"{counts['missing_metadata']} "
            f"applied={counts['applied']} "
            f"failed={counts['failed']}"
        )

        return 1 if counts["failed"] else 0

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(
            "migration_error="
            f"{safe_output(exc)}"
        )
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
