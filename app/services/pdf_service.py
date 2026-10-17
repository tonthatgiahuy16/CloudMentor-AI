from hashlib import sha256
from pathlib import Path
from uuid import uuid4


class RetainedSourceValidationError(
    RuntimeError
):
    pass


class PDFService:
    def __init__(self, document_repo):
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
        self._validate_retained_source(document)

        self.index.delete_by_document_id(
            document.document_id
        )

        return self._process_document(
            file_path=document.source_uri,
            document_id=document.document_id,
            subject_id=document.subject_id,
        )


    def _validate_retained_source(
        self,
        document,
    ) -> None:
        if (
            document.source_uri is None
            or document.content_sha256 is None
            or document.file_size_bytes is None
        ):
            raise RetainedSourceValidationError(
                "Document source metadata is incomplete"
            )

        source_path = Path(document.source_uri)

        if not source_path.is_file():
            raise RetainedSourceValidationError(
                "Retained source file is missing"
            )

        source_data = source_path.read_bytes()

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


    def upload(
        self,
        file_path: str,
        subject_id: str,
        chapter: int | None = None,
        document_id: str | None = None,
        original_filename: str | None = None,
        source_uri: str | None = None,
        content_sha256: str | None = None,
        file_size_bytes: int | None = None,
        ):

        if document_id is None:
            document_id = str(uuid4())

        path = Path(file_path)
        filename = original_filename or path.name
        file_type = path.suffix.lstrip(".").lower()

        self.document_repo.create(
            document_id=document_id,
            subject_id=subject_id,
            filename=filename,
            file_type=file_type,
            chapter=chapter,
            source_uri=source_uri,
            content_sha256=content_sha256,
            file_size_bytes=file_size_bytes,
        )
        return self._process_document(
            file_path=file_path,
            document_id=document_id,
            subject_id=subject_id,
        )


    def _process_document(
        self,
        *,
        file_path: str,
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
                file_path,
                document_id,
                subject_id,
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
            self.document_repo.mark_failed(
                document_id=document_id,
                failed_stage=stage,
                error_message=str(exc),
            )
            raise
