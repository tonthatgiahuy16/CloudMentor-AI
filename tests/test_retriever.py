from app.rag.vector_store import VectorStore
from app.rag.query_encoder import QueryEncoder
from app.rag.retriever import Retriever


vector_store = VectorStore()


encoder = QueryEncoder()


query = "Điện toán đâm mây là gì?"


query_vector = encoder.encode(query)


retriever = Retriever(vector_store)


results = retriever.search(
    query_vector,
    top_k=10
)
print(results)

print("====================")

for i, doc in enumerate(results["documents"][0]):
    print("====================")
    print(
        "Result:",
        i+1,
    )

    print(
        "Distance:", results["distances"][0][i],      
    )

    print(doc[:500])