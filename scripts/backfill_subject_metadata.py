"""One-off, idempotent backfill for existing indexed Cloud Computing chunks."""

from argparse import ArgumentParser
from pathlib import Path

import chromadb


BACKEND_DIR = Path(__file__).resolve().parents[1]
CHROMA_PATH = BACKEND_DIR / "chroma_db"
BACKUP_PATH = BACKEND_DIR.parent / "chroma_db_before_subject_backfill"
COLLECTION_NAME = "cloudmentor"
SUBJECT_ID = "1f51e907-c539-48a8-a25f-d355db5afd55"
EXPECTED_DOCUMENT_CHUNKS = {
    "508249f0-3b23-400f-a7eb-6d0866a7bd12": 46,
    "2cf52e9b-877e-4c81-bc7e-38cca3a6a344": 177,
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write metadata after all safety checks pass.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not (BACKUP_PATH / "chroma.sqlite3").is_file():
        raise RuntimeError(f"Missing Chroma backup at {BACKUP_PATH}")

    collection = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
    ).get_collection(COLLECTION_NAME)

    pending: list[tuple[str, dict]] = []

    for document_id, expected_count in EXPECTED_DOCUMENT_CHUNKS.items():
        result = collection.get(
            where={"document_id": document_id},
            include=["metadatas"],
        )
        ids = result["ids"]
        metadatas = result["metadatas"] or []

        if len(ids) != expected_count:
            raise RuntimeError(
                f"{document_id}: expected {expected_count} chunks, found {len(ids)}"
            )

        for chunk_id, metadata in zip(ids, metadatas, strict=True):
            if metadata is None or metadata.get("document_id") != document_id:
                raise RuntimeError(f"Invalid lineage metadata for chunk {chunk_id}")

            current_subject_id = metadata.get("subject_id")
            if current_subject_id not in (None, SUBJECT_ID):
                raise RuntimeError(
                    f"Chunk {chunk_id} belongs to another subject: "
                    f"{current_subject_id}"
                )

            if current_subject_id is None:
                pending.append(
                    (chunk_id, {**metadata, "subject_id": SUBJECT_ID})
                )

    print(f"Validated {sum(EXPECTED_DOCUMENT_CHUNKS.values())} chunks")
    print(f"Chunks missing subject_id: {len(pending)}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to update metadata.")
        return

    batch_size = 100
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        collection.update(
            ids=[chunk_id for chunk_id, _ in batch],
            metadatas=[metadata for _, metadata in batch],
        )

    for document_id, expected_count in EXPECTED_DOCUMENT_CHUNKS.items():
        verified = collection.get(
            where={
                "$and": [
                    {"document_id": document_id},
                    {"subject_id": SUBJECT_ID},
                ]
            },
            include=["metadatas"],
        )
        if len(verified["ids"]) != expected_count:
            raise RuntimeError(
                f"Verification failed for document {document_id}"
            )

    print(f"Backfill complete: {len(pending)} chunks updated")


if __name__ == "__main__":
    main()
