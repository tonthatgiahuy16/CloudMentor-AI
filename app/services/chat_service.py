from typing import Any

from app.core.logger import logger
from app.models.source_location import (
    validate_source_location,
)


def parse_source_location(
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], str] | None:
    page = metadata.get("page")

    line_range = None
    if (
        metadata.get("line_start") is not None
        and metadata.get("line_end") is not None
    ):
        line_range = (
            metadata["line_start"],
            metadata["line_end"],
        )

    paragraph_range = None
    if (
        metadata.get("paragraph_start")
        is not None
        and metadata.get("paragraph_end")
        is not None
    ):
        paragraph_range = (
            metadata["paragraph_start"],
            metadata["paragraph_end"],
        )

    try:
        validate_source_location(
            owner="Retrieved chunk",
            page=page,
            line_range=line_range,
            paragraph_range=paragraph_range,
        )
    except ValueError:
        return None

    fields = {
        "page": page,
        "line_range": line_range,
        "paragraph_range": paragraph_range,
    }

    if page is not None:
        label = f"Page: {page}"
    elif line_range is not None:
        label = (
            f"Lines: {line_range[0]}-"
            f"{line_range[1]}"
        )
    else:
        label = (
            "Paragraphs: "
            f"{paragraph_range[0]}-"
            f"{paragraph_range[1]}"
        )

    return fields, label


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

    def ask(self, question: str, subject_id: str | None = None) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question must not be empty")

        logger.info("Question received")
        query_vector = self.embedder.embed_query(normalized_question)
        results = self.retriever.search(
            query_vector,
            subject_id=subject_id,
        )

        if not results:
            logger.info(
                "No relevant context found"
            )

            return {
                "question": normalized_question,
                "answer": (
                    "Tôi không tìm thấy thông tin "
                    "trong tài liệu."
                ),
                "sources": [],
            }

        contexts = []
        sources = []
        for item in results:
            metadata = item.get("metadata") or {}

            document_id = metadata.get(
                "document_id"
            )

            if not document_id:
                logger.warning(
                    "Skipping chunk without document lineage: %s",
                    item.get("chunk_id"),
                )
                continue

            parsed_location = (
                parse_source_location(metadata)
            )

            if parsed_location is None:
                logger.warning(
                    "Skipping chunk without valid "
                    "source location: %s",
                    item.get("chunk_id"),
                )
                continue

            (
                source_location,
                source_location_label,
            ) = parsed_location

            contexts.append(
                "\n".join(
                    [
                        f"Source: {metadata.get('source')}",
                        source_location_label,
                        f"Content: {item.get('document', '')}",
                    ]
                )
            )
            sources.append(
                {
                    "chunk_id": item["chunk_id"],
                    "document_id": document_id,
                    "chunk_index": metadata.get("chunk_index"),
                    "source": metadata.get("source"),
                    **source_location,
                    "distance": round(item["distance"], 3),
                }
            )

        if not contexts:
            return {
                "question": normalized_question,
                "answer": (
                    "Tôi không tìm thấy thông tin "
                    "trong tài liệu."
                ),
                "sources": [],
            }

        logger.info("Retrieved %s contexts", len(contexts))
        answer = self.generator.generate(normalized_question, contexts)
        return {
            "question": normalized_question,
            "answer": answer,
            "sources": sources,
        }
