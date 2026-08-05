from app.rag.loader import PDFLoader
from app.rag.chunker import TextChunker
from app.rag.embedder import EmbeddingService


loader = PDFLoader()

documents = loader.load(
    "../data/slides/Ch1 - Tong quan DTDM.pdf"
)


chunker = TextChunker()

chunks = chunker.split(documents)


embedder = EmbeddingService()


vectors = embedder.embed(chunks)


print("===================")

print(
    "Number of vectors:",
    len(vectors)
)


print(
    "Vector dimension:",
    len(vectors[0])
)


print("===================")

print(vectors[0][:10])