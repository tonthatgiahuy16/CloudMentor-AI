"""Rebuild the Chroma collection in the pinned cosine space.

The collection must be in cosine space so a threshold expressed as a
cosine similarity has a stable meaning. An existing collection created
with Chroma's default L2 space cannot be converted in place, so this
operator workflow deletes and rebuilds it from PostgreSQL plus retained
source files.

Dry run is the default. Run with ``--apply`` only while the API is
stopped or read-only, because retrieval returns nothing during rebuild.
"""

import argparse

import chromadb

from app.core import config
from app.core.logger import logger
from app.rag.vector_store import VectorStore
from app.repos.document_repository import (
    DocumentRepository,
)
from app.services.pdf_service import PDFService
from app.storage.source_storage_factory import (
    create_source_storage,
)
from app.core.database import SessionLocal


def _indexed_documents(repo: DocumentRepository):
    return [
        document
        for document in repo.list_indexed_for_active_subjects()
        if document.status == "INDEXED"
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild the derived Chroma collection in cosine space"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete and rebuild the collection (default: dry run)",
    )
    parser.add_argument(
        "--collection",
        default=config.COLLECTION_NAME,
    )
    args = parser.parse_args(argv)

    client = chromadb.PersistentClient(
        path=str(config.CHROMA_DIR)
    )

    try:
        existing = client.get_collection(
            args.collection
        )
    except Exception:
        existing = None

    current_space = (
        VectorStore.collection_space(existing)
        if existing is not None
        else None
    )

    db = SessionLocal()

    try:
        repo = DocumentRepository(db)
        documents = _indexed_documents(repo)
    finally:
        db.close()

    print(f"collection={args.collection}")
    print(f"current_space={current_space}")
    print(f"target_space={config.VECTOR_SPACE}")
    print(f"indexed_documents={len(documents)}")

    if not args.apply:
        if current_space == config.VECTOR_SPACE:
            print("Collection already uses the target space.")
            print("Dry run only; pass --apply to force a rebuild.")
        else:
            print(
                "Collection space differs. Rebuild is required; "
                "pass --apply to delete and rebuild."
            )
        return 0

    if existing is not None:
        client.delete_collection(args.collection)
        print("Deleted existing collection.")

    # Creating the collection now pins the cosine metadata before any
    # rebuild writes into it.
    VectorStore(collection_name=args.collection)

    if not documents:
        print("No indexed documents to rebuild.")
        return 0

    db = SessionLocal()
    failures = 0

    try:
        repo = DocumentRepository(db)
        service = PDFService(
            repo,
            source_storage=create_source_storage(),
        )

        for document in documents:
            try:
                chunk_count = service.rebuild_retained_document(
                    document
                )
                print(
                    "rebuilt "
                    f"document_id={document.document_id} "
                    f"chunks={chunk_count}"
                )
            except Exception as exc:
                failures += 1
                logger.exception(
                    "Vector index rebuild failed",
                    extra={
                        "structured": {
                            "event": "vector_index_rebuild",
                            "document_id": document.document_id,
                            "error": type(exc).__name__,
                        },
                    },
                )
                print(
                    "failed "
                    f"document_id={document.document_id} "
                    f"error={type(exc).__name__}"
                )
    finally:
        db.close()

    print(f"failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
