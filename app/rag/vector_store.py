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

            metadatas.append(
                {
                    "chunk_index": chunk.chunk_index,
                    "document_id": chunk.document_id,
                    "subject_id": chunk.subject_id,
                    "page": chunk.page,
                    "source": chunk.source,
                    
                }
            )

    


        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings.tolist()
        )


        logger.info(
            f"Stored {len(chunks)} chunks into vector database"
        )

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
        






    