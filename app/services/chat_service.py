from typing import Any

from app.core.logger import logger


class ChatService:
    """Coordinate query embedding, retrieval, and answer generation."""

    def __init__(
        self,
        *,
        embedder: Any | None = None,
        retriever: Any | None = None,
        generator: Any | None = None,
    ):
        if embedder is None or retriever is None or generator is None:
            from app.llm.generator import AnswerGenerator
            from app.rag.embedder import EmbeddingService
            from app.rag.retriever import Retriever
            from app.rag.vector_store import VectorStore

            vector_store = VectorStore()
            embedder = embedder or EmbeddingService()
            retriever = retriever or Retriever(vector_store)
            generator = generator or AnswerGenerator()

        self.embedder = embedder
        self.retriever = retriever
        self.generator = generator

    def ask(self, question: str) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question must not be empty")

        logger.info("Question received")
        query_vector = self.embedder.embed_query(normalized_question)
        results = self.retriever.search(query_vector)

        contexts = []
        sources = []
        for item in results:
            metadata = item.get("metadata") or {}
            contexts.append(
                "\n".join(
                    [
                        f"Source: {metadata.get('source')}",
                        f"Page: {metadata.get('page')}",
                        f"Content: {item.get('document', '')}",
                    ]
                )
            )
            sources.append(
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index"),
                    "source": metadata.get("source"),
                    "page": metadata.get("page"),
                    "distance": round(item["distance"], 3),
                }
            )

        logger.info("Retrieved %s contexts", len(contexts))
        answer = self.generator.generate(normalized_question, contexts)
        return {
            "question": normalized_question,
            "answer": answer,
            "sources": sources,
        }
