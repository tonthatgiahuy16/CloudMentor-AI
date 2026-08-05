from app.rag.loader import PDFLoader


loader = PDFLoader()

documents = loader.load("../data/slides/Ch1 - Tong quan DTDM.pdf")

print(f"Tổng số trang: {len(documents)}")

for doc in documents:
    print("=" * 50)
    print(f"Page: {doc.page}")
    print(f"Source: {doc.source}")
    print(doc.text[:300])