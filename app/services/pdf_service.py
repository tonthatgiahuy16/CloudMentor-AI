from app.rag.loader import PDFLoader
from app.rag.cleaner import TextCleaner
from app.rag.chunker import TextChunker
from app.rag.embedder import EmbeddingService
from app.rag.vector_store import VectorStore


class PDFService:

    def __init__(self):

        self.loader = PDFLoader()

        self.cleaner = TextCleaner()

        self.chunker = TextChunker()

        self.embedder = EmbeddingService()

        self.vector_store = VectorStore()


    def upload(
        self,
        file_path: str
    ):

        # 1 Load PDF
        document = self.loader.load(
            file_path
        )

        # 2 Clean
        cleaned = self.cleaner.clean(
            document
        )

        # 3 Chunk
        chunks = self.chunker.chunk(
            cleaned
        )

        # 4 Embedding
        embeddings = self.embedder.embed(
            chunks
        )

        # 5 Save
        self.vector_store.add(
            chunks,
            embeddings
        )

        return len(chunks)