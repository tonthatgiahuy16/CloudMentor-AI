from app.rag.loader import PDFLoader
from app.rag.chunker import TextChunker
from app.rag.embedder import EmbeddingService
from app.rag.vector_store import VectorStore


# Load PDF

loader = PDFLoader()

documents = loader.load(
    "../data/slides/Ch1 - Tong quan DTDM.pdf"
)


# Chunk

chunker = TextChunker()

chunks = chunker.split(documents)


# Embedding

embedder = EmbeddingService()

vectors = embedder.embed(chunks)


# Store

vector_store = VectorStore()

vector_store.add(
    chunks,
    vectors
)


print("DONE")