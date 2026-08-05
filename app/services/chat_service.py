from app.rag.embedder import EmbeddingService
from app.rag.vector_store import VectorStore
from app.rag.retriever import Retriever

from app.llm.generator import AnswerGenerator


class ChatService:

    def __init__(self):

        self.vector_store = VectorStore()

        self.embedder = EmbeddingService()

        self.retriever = Retriever(
            self.vector_store
        )

        self.generator = AnswerGenerator()


    def ask(
        self,
        question: str
    ):

        question = question.strip()


        # 1. Embedding câu hỏi
        query_vector = self.embedder.embed_query(
            question
        )


        # 2. Retrieve context
        results = self.retriever.search(
            query_vector,
            top_k=3
        )


        contexts = []
        sources = []


        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]


        for doc, metadata, distance in zip(
            documents,
            metadatas,
            distances
        ):

            contexts.append(
                f"""
Source:
{metadata}

Content:
{doc}
"""
            )


            sources.append(
                {
                    "source": metadata.get("source"),
                    "page": metadata.get("page"),
                    "distance": distance
                }
            )


        # 3. Generate answer
        answer = self.generator.generate(
            question,
            contexts
        )


        # 4. Response
        return {
            "question": question,
            "answer": answer,
            "sources": sources
        }