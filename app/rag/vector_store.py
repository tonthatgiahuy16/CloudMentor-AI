from typing import List

import chromadb

from app.models.chunk import Chunk
from app.core.logger import logger


class VectorStore:

    def __init__(
        self,
        collection_name: str = "cloudmentor"
    ):

        self.client = chromadb.PersistentClient(
            path="./chroma_db"
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
        vectors = []


        for i,  chunk in enumerate(chunks):

            ids.append(chunk.id)

            documents.append(
                chunk.text
            )
            vectors.append(
                embeddings[i].tolist()
            )

            metadatas.append(
                {
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