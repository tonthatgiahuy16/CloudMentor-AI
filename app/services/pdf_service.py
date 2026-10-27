from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.storage.source_storage import (
    LocalSourceStorage,
    SourceNotFoundError,
    SourceStorage,
)


class RetainedSourceValidationError(
    RuntimeError
):
    pass


class PDFService:
    def __init__(
        self,
        document_repo,
        source_storage: SourceStorage | None = None,
    ):
        from app.pipeline.chunk_pipeline import (
            ChunkPipeline,
        )
        from app.pipeline.embedding_pipeline import (
            EmbeddingPipeline,
        )
        from app.pipeline.extract_pipeline import (
            ExtractPipeline,
        )
        from app.pipeline.index_pipeline import (
            IndexPipeline,
        )
        from app.pipeline.transform_pipeline import (
            TransformPipeline,
        )

        self.extract = ExtractPipeline()
        self.transform = TransformPipeline()
        self.chunk = ChunkPipeline()
        self.embedding = EmbeddingPipeline()
        self.index = IndexPipeline()
        self.document_repo = document_repo

        if source_storage is None:
            source_storage = LocalSourceStorage(
                root=Path("."),
            )

        self.source_storage = source_storage


    def find_active_duplicate(
        self,
        *,
        subject_id: str,
        content_sha256: str,
    ):
        return (
            self.document_repo
            .get_active_by_subject_and_sha256(
                subject_id=subject_id,
                content_sha256=content_sha256,
            )
        )

    def retry_failed_document(
        self,
        document,
    ) -> int:
        if document.status != "FAILED":
            raise RuntimeError(
                "Only failed documents can be retried"
            )

        return self._reprocess_retained_document(
            document
        )


    def recover_stale_document(
        self,
        document,
    ) -> int:
        if document.status not in {
            "UPLOADED",
            "PROCESSING",
        }:
            raise RuntimeError(
                "Only stale uploaded or processing "
                "documents can be recovered"
            )

        try:
            return self._reprocess_retained_document(
                document
            )
        except RetainedSourceValidationError as exc:
            self.document_repo.mark_failed(
                document_id=document.document_id,
                failed_stage="EXTRACT",
                error_message=str(exc),
            )
            raise


    def rebuild_retained_document(
        self,
        document,
    ) -> int:
        if document.status not in {
            "UPLOADED",
            "PROCESSING",
            "FAILED",
            "INDEXED",
        }:
            raise RuntimeError(
                "Document cannot be rebuilt "
                "from its current status"
            )

        try:
            return self._reprocess_retained_document(
                document
            )
        except RetainedSourceValidationError as exc:
            self.document_repo.mark_failed(
                document_id=document.document_id,
                failed_stage="EXTRACT",
                error_message=str(exc),
            )
            raise


    def _reprocess_retained_document(
        self,
        document,
    ) -> int:
        source_data = (
            self._validate_retained_source(
                document
            )
        )

        self.index.delete_by_document_id(
            document.document_id
        )

        return self._process_document(
            source_data=source_data,
            filename=document.filename,
            file_type=document.file_type,
            document_id=document.document_id,
            subject_id=document.subject_id,
        )


    def _validate_retained_source(
        self,
        document,
    ) -> bytes:
        if (
            document.source_uri is None
            or document.content_sha256 is None
            or document.file_size_bytes is None
        ):
            raise RetainedSourceValidationError(
                "Document source metadata is incomplete"
            )

        try:
            source_data = (
                self.source_storage.read_bytes(
                    document.source_uri
                )
            )
        except (
            FileNotFoundError,
            IsADirectoryError,
            SourceNotFoundError,
        ) as exc:
            raise RetainedSourceValidationError(
                "Retained source file is missing"
            ) from exc

        if len(source_data) != document.file_size_bytes:
            raise RetainedSourceValidationError(
                "Retained source file size does not match"
            )

        if (
            sha256(source_data).hexdigest()
            != document.content_sha256
        ):
            raise RetainedSourceValidationError(
                "Retained source checksum does not match"
            )

        return source_data


    def upload(
        self,
        *,
        source_data: bytes,
        subject_id: str,
        chapter: int | None = None,
        document_id: str | None = None,
        original_filename: str | None = None,
        content_sha256: str | None = None,
        file_size_bytes: int | None = None,
    ):
        if document_id is None:
            document_id = str(uuid4())

        if original_filename is None:
            raise ValueError(
                "Original filename is required"
            )

        filename = original_filename
        file_type = (
            Path(filename)
            .suffix
            .lstrip(".")
            .lower()
        )

        self.document_repo.create(
            document_id=document_id,
            subject_id=subject_id,
            filename=filename,
            file_type=file_type,
            chapter=chapter,
            source_uri=None,
            content_sha256=content_sha256,
            file_size_bytes=file_size_bytes,
        )

        stored_source = self.source_storage.store(
            document_id=document_id,
            filename=filename,
            data=source_data,
        )

        self.document_repo.attach_source_metadata(
            document_id=document_id,
            source_uri=stored_source.source_uri,
            content_sha256=stored_source.content_sha256,
            file_size_bytes=stored_source.file_size_bytes,
        )

        return self._process_document(
            source_data=source_data,
            filename=filename,
            file_type=file_type,
            document_id=document_id,
            subject_id=subject_id,
        )


    def _process_document(
        self,
        *,
        source_data: bytes,
        filename: str,
        file_type: str,
        document_id: str,
        subject_id: str,
    ) -> int:
        self.document_repo.mark_processing(
            document_id
        )

        try:
            stage = "EXTRACT"
            self.document_repo.record_processing_heartbeat(
                document_id=document_id,
                stage=stage,
            )
            documents = self.extract.run(
                source_data=source_data,
                filename=filename,
                file_type=file_type,
                document_id=document_id,
                subject_id=subject_id,
            )

            stage = "TRANSFORM"
            self.document_repo.record_processing_heartbeat(
                document_id=document_id,
                stage=stage,
            )
            cleaned = self.transform.run(
                documents
            )

            stage = "CHUNK"
            self.document_repo.record_processing_heartbeat(
                document_id=document_id,
                stage=stage,
            )
            chunks = self.chunk.run(
                cleaned
            )

            stage = "EMBEDDING"
            self.document_repo.record_processing_heartbeat(
                document_id=document_id,
                stage=stage,
            )
            embeddings = self.embedding.run(
                chunks
            )

            stage = "INDEX"
            self.document_repo.record_processing_heartbeat(
                document_id=document_id,
                stage=stage,
            )
            self.index.run(
                chunks,
                embeddings,
            )

            self.document_repo.mark_indexed(
                document_id
            )

            return len(chunks)

        except Exception as exc:
            cleanup_error = None

            try:
                self.index.delete_by_document_id(
                    document_id
                )
            except Exception as deletion_exc:
                cleanup_error = deletion_exc

            error_message = str(exc)

            if cleanup_error is not None:
                error_message = (
                    f"{error_message}; derived vector cleanup "
                    f"failed: {cleanup_error}"
                )

            self.document_repo.mark_failed(
                document_id=document_id,
                failed_stage=stage,
                error_message=error_message,
            )
            raise
