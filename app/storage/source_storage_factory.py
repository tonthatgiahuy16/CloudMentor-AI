import os
from pathlib import Path

from app.storage.source_storage import (
    LocalSourceStorage,
    SourceStorage,
)

from minio import Minio

from app.storage.minio_source_storage import (
    MinioSourceStorage,
)


def create_source_storage() -> SourceStorage:
    backend = os.getenv(
        "CLOUDMENTOR_SOURCE_STORAGE",
        "local",
    ).strip().lower()

    if backend == "local":
        return LocalSourceStorage(
            root=Path(
                os.getenv(
                    "CLOUDMENTOR_UPLOAD_DIR",
                    "storage/uploads",
                )
            )
        )

    if backend == "minio":
        endpoint = os.getenv(
            "CLOUDMENTOR_MINIO_ENDPOINT"
        )
        access_key = os.getenv(
            "CLOUDMENTOR_MINIO_ACCESS_KEY"
        )
        secret_key = os.getenv(
            "CLOUDMENTOR_MINIO_SECRET_KEY"
        )
        bucket_name = os.getenv(
            "CLOUDMENTOR_MINIO_BUCKET",
            "cloudmentor-sources",
        )
        secure = (
            os.getenv(
                "CLOUDMENTOR_MINIO_SECURE",
                "false",
            )
            .strip()
            .lower()
            == "true"
        )

        if not all(
            (
                endpoint,
                access_key,
                secret_key,
                bucket_name,
            )
        ):
            raise RuntimeError(
                "MinIO storage configuration "
                "is incomplete"
            )

        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        return MinioSourceStorage(
            client=client,
            bucket_name=bucket_name,
        )

    raise RuntimeError(
        f"Unsupported source storage: {backend}"
    )
