from typing import List

import chromadb
from app.core import config

from app.models.chunk import Chunk
from app.core.logger import logger


class VectorStore:

    def __init__(
        self,
        collection_name: str = "cloudmentor"
    ):

        self.client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR)
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

        logger.info(
            f"Vector collection initialized: {collection_name}"
        )


    def add(
        self,
        chunks: List[Chunk],
        embeddings
    ):

        ids = []
        documents = []
        metadatas = []





        for chunk in chunks:

            ids.append(chunk.id)

            documents.append(
                chunk.text
            )

            metadata = {
                "chunk_index": chunk.chunk_index,
                "document_id": chunk.document_id,
                "subject_id": chunk.subject_id,
                "source": chunk.source,
            }

            if chunk.page is not None:
                metadata["page"] = chunk.page

            elif chunk.line_range is not None:
                line_start, line_end = (
                    chunk.line_range
                )
                metadata["line_start"] = (
                    line_start
                )
                metadata["line_end"] = line_end

            elif (
                chunk.paragraph_range
                is not None
            ):
                (
                    paragraph_start,
                    paragraph_end,
                ) = chunk.paragraph_range

                metadata["paragraph_start"] = (
                    paragraph_start
                )
                metadata["paragraph_end"] = (
                    paragraph_end
                )

            else:
                raise ValueError(
                    "Chunk source location is missing"
                )

            metadatas.append(metadata)


        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings.tolist()
        )


        logger.info(
            f"Stored {len(chunks)} chunks into vector database"
        )

    def list_all_records(
        self,
    ) -> list[dict]:
        results = self.collection.get(
            include=["metadatas"],
        )

        chunk_ids = results.get("ids") or []
        metadatas = (
            results.get("metadatas") or []
        )

        records = []

        for index, chunk_id in enumerate(
            chunk_ids
        ):
            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else None
            )

            record = (
                dict(metadata)
                if isinstance(metadata, dict)
                else {}
            )
            record["chunk_id"] = chunk_id
            records.append(record)

        return records

    def delete_by_chunk_ids(
        self,
        chunk_ids: list[str],
    ) -> int:
        unique_chunk_ids = list(
            dict.fromkeys(chunk_ids)
        )

        if not unique_chunk_ids:
            return 0

        results = self.collection.get(
            ids=unique_chunk_ids,
        )
        existing_chunk_ids = results.get("ids") or []

        if not existing_chunk_ids:
            return 0

        self.collection.delete(
            ids=existing_chunk_ids,
        )
        return len(existing_chunk_ids)

    def delete_by_document_id(self, document_id: str):
        results = self.collection.get(
            where={"document_id": document_id},
        )

        count = len(results["ids"])
        if count == 0:
            return 0
        self.collection.delete(
            where={"document_id": document_id}
        )
        return count
        






    