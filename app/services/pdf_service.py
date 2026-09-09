from app.pipeline.extract_pipeline import ExtractPipeline
from app.pipeline.transform_pipeline import TransformPipeline
from app.pipeline.chunk_pipeline import ChunkPipeline
from app.pipeline.embedding_pipeline import EmbeddingPipeline
from app.pipeline.index_pipeline import IndexPipeline
from uuid import uuid4
from pathlib import Path

class PDFService:
    def __init__(self, document_repo):
        self.extract = ExtractPipeline()
        self.transform = TransformPipeline()

        self.chunk = ChunkPipeline()

        self.embedding = EmbeddingPipeline()

        self.index = IndexPipeline()
        self.document_repo = document_repo


    def upload(
        self,
        file_path: str,
        subject_id: str,
        chapter: int | None = None,
        document_id: str | None = None,
        ):
        if document_id is None:
            document_id = str(uuid4())

        path = Path(file_path)
        filename = path.name
        file_type = path.suffix.lstrip(".").lower()

        self.document_repo.create(
            document_id=document_id,
            subject_id=subject_id,
            filename=filename,
            file_type=file_type,
            chapter=chapter
        )
        self.document_repo.mark_processing(document_id)

        try:
            stage = "EXTRACT"

            documents = self.extract.run(
                file_path,
                document_id
            )

            stage = "TRANSFORM"

            cleaned = self.transform.run(
                documents
            )

            stage = "CHUNK"

            chunks = self.chunk.run(
                cleaned
            )

            stage = "EMBEDDING"

            embeddings = self.embedding.run(
                chunks
            )

            stage = "INDEX"

            self.index.run(
                chunks,
                embeddings
            )
            self.document_repo.mark_indexed(document_id)

            return len(chunks)

        except Exception as exc:
            self.document_repo.mark_failed(
                document_id=document_id,
                failed_stage=stage,
                error_message=str(exc))
            raise
