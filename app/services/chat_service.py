from app.rag.embedder import EmbeddingService
from app.rag.vector_store import VectorStore
from app.rag.retriever import Retriever

from app.llm.generator import AnswerGenerator

from app.core.logger import logger


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
    ) -> dict:

        question = question.strip()

        logger.info(
            f"Question: {question}"
        )

        # 1. Sinh embedding
        query_vector = self.embedder.embed_query(
            question
        )

        # 2. Retrieve
        results = self.retriever.search(
            query_vector,
            top_k=3
        )

        contexts = []
        sources = []

        for item in results:

            metadata = item["metadata"]

            contexts.append(
                f"""
Source:
{metadata.get("source")}

Page:
{metadata.get("page")}

Content:
{item["document"]}
"""
            )

            sources.append(
                {
                    "source": metadata.get("source"),
                    "page": metadata.get("page"),
                    "distance": round(item["distance"], 3)
                }
            )

        logger.info(
            f"Retrieved {len(contexts)} contexts"
        )

        # 3. Generate answer
        answer = self.generator.generate(
            question,
            contexts
        )

        logger.info(
            "Answer generated successfully"
        )

        # 4. Return
        return {
            "question": question,
            "answer": answer,
            "sources": sources
        }