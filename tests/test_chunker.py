from app.rag.loader import PDFLoader
from app.rag.chunker import TextChunker


loader = PDFLoader()

documents = loader.load("../data/slides/Ch1 - Tong quan DTDM.pdf")

chunker = TextChunker()

chunks = chunker.split(documents)

print("=" * 50)
print(f"Documents: {len(documents)}")
print(f"Chunks: {len(chunks)}")

print("=" * 50)

print(chunks[0])

print("=" * 50)

print(chunks[1])
for doc in documents[:10]:
    print(
        "Page:",
        doc.page,
        "Length:",
        len(doc.text)
    )