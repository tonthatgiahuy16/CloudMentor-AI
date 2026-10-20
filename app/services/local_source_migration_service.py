from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class LocalSourceMigrationPlan:
    document_id: str
    filename: str
    current_source_uri: str
    target_source_uri: str
    content_sha256: str
    file_size_bytes: int


class LocalSourceToMinioMigrationService:
    def __init__(
        self,
        *,
        document_repo,
        local_storage,
        minio_storage,
    ):
        self.document_repo = document_repo
        self.local_storage = local_storage
        self.minio_storage = minio_storage

    def plan(
        self,
        *,
        document_id: str,
    ) -> LocalSourceMigrationPlan:
        document = self.document_repo.get_by_id(
            document_id
        )

        if document is None:
            raise RuntimeError("Document not found")

        if (
            document.source_uri is None
            or document.content_sha256 is None
            or document.file_size_bytes is None
        ):
            raise RuntimeError(
                "Document source metadata is incomplete"
            )

        if document.source_uri.startswith(
            "minio://"
        ):
            raise RuntimeError(
                "Document source is already in MinIO"
            )

        if "://" in document.source_uri:
            raise RuntimeError(
                "Document source URI is unsupported"
            )

        source_data = self.local_storage.read_bytes(
            document.source_uri
        )

        if (
            sha256(source_data).hexdigest()
            != document.content_sha256
        ):
            raise RuntimeError(
                "Local source hash mismatch"
            )

        if (
            len(source_data)
            != document.file_size_bytes
        ):
            raise RuntimeError(
                "Local source size mismatch"
            )

        target_source_uri = (
            self.minio_storage.source_uri_for(
                document_id=document.document_id,
                filename=document.filename,
            )
        )

        return LocalSourceMigrationPlan(
            document_id=document.document_id,
            filename=document.filename,
            current_source_uri=document.source_uri,
            target_source_uri=target_source_uri,
            content_sha256=(
                document.content_sha256
            ),
            file_size_bytes=(
                document.file_size_bytes
            ),
        )

    def apply(
        self,
        plan: LocalSourceMigrationPlan,
    ):
        document = self.document_repo.get_by_id(
            plan.document_id
        )

        if document is None:
            raise RuntimeError("Document not found")

        current_snapshot = (
            document.filename,
            document.source_uri,
            document.content_sha256,
            document.file_size_bytes,
        )
        planned_snapshot = (
            plan.filename,
            plan.current_source_uri,
            plan.content_sha256,
            plan.file_size_bytes,
        )

        if current_snapshot != planned_snapshot:
            raise RuntimeError(
                "Document source changed after planning"
            )

        source_data = self.local_storage.read_bytes(
            plan.current_source_uri
        )

        if (
            sha256(source_data).hexdigest()
            != plan.content_sha256
            or len(source_data)
            != plan.file_size_bytes
        ):
            raise RuntimeError(
                "Local source changed after planning"
            )

        stored_source = self.minio_storage.store(
            document_id=plan.document_id,
            filename=plan.filename,
            data=source_data,
        )

        stored_metadata = (
            stored_source.source_uri,
            stored_source.content_sha256,
            stored_source.file_size_bytes,
        )
        expected_metadata = (
            plan.target_source_uri,
            plan.content_sha256,
            plan.file_size_bytes,
        )

        if stored_metadata != expected_metadata:
            raise RuntimeError(
                "Stored source metadata mismatch"
            )

        retained_data = (
            self.minio_storage.read_bytes(
                stored_source.source_uri
            )
        )

        if (
            sha256(retained_data).hexdigest()
            != plan.content_sha256
            or len(retained_data)
            != plan.file_size_bytes
        ):
            raise RuntimeError(
                "Stored source verification failed"
            )

        return (
            self.document_repo
            .replace_source_uri_if_matches(
                document_id=plan.document_id,
                expected_source_uri=(
                    plan.current_source_uri
                ),
                expected_content_sha256=(
                    plan.content_sha256
                ),
                expected_file_size_bytes=(
                    plan.file_size_bytes
                ),
                new_source_uri=(
                    stored_source.source_uri
                ),
            )
        )