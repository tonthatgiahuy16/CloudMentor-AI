from app.rag.vector_store import VectorStore


store = VectorStore()


print("====================")

count = store.collection.count()

print(
    "Total vectors:",
    count
)

print("====================")


data = store.collection.get(
    limit=5
)


print("IDs:")

print(data["ids"])


print("====================")

print("Documents:")


for i, doc in enumerate(data["documents"]):

    print("--------------------")

    print(
        "Document:",
        i + 1
    )

    print(doc[:500])