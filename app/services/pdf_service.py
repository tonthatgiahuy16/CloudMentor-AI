from app.pipeline.extract_pipeline import ExtractPipeline
from app.pipeline.transform_pipeline import TransformPipeline
from app.pipeline.chunk_pipeline import ChunkPipeline
from app.pipeline.embedding_pipeline import EmbeddingPipeline
from app.pipeline.index_pipeline import IndexPipeline


class PDFService:

    def __init__(self):

        self.extract = ExtractPipeline()
        self.transform = TransformPipeline()

        self.chunk = ChunkPipeline()

        self.embedding = EmbeddingPipeline()

        self.index = IndexPipeline()


    def upload(
        self,
        file_path: str
    ):

        # 1 Load PDF
        document = self.extract.run(
            file_path
        )

        # 2 Clean
        cleaned = self.transform.run(
            document
        )

        # 3 Chunk
        chunks = self.chunk.run(
            cleaned
        )

        # 4 Embedding
        embeddings = self.embedding.run(
            chunks
        )

        # 5 Save
        self.index.run(
            chunks,
            embeddings
        )

        return len(chunks)