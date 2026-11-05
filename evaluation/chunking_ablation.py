from pathlib import Path
from uuid import uuid4

import chromadb

from app.core import config
from app.models.chunk import Chunk
from app.rag.loader import read_docx_paragraphs


def build_variants(source_path: Path, target_paragraph: int) -> list[dict]:
    """Create comparable chunks without modifying the source fixture."""
    paragraphs = read_docx_paragraphs(source_path)
    if not 1 <= target_paragraph <= len(paragraphs):
        raise ValueError(
            "target_paragraph is outside the DOCX paragraph range"
        )

    return [
        {
            "name": "baseline_full_document",
            "paragraph_range": [1, len(paragraphs)],
            "text": "\n".join(paragraphs),
        },
        {
            "name": "isolated_target_paragraph",
            "paragraph_range": [target_paragraph, target_paragraph],
            "text": paragraphs[target_paragraph - 1],
        },
    ]


def run_ablation(
    source_path: Path,
    target_paragraph: int,
    queries: list[str],
    embedder,
) -> dict:
    if not queries:
        raise ValueError("at least one query is required")

    variants = build_variants(source_path, target_paragraph)
    document_id = str(uuid4())
    subject_id = str(uuid4())
    chunks = [
        Chunk(
            id=f"chunking-ablation-{variant['name']}",
            document_id=document_id,
            subject_id=subject_id,
            chunk_index=index,
            source=source_path.name,
            text=variant["text"],
            paragraph_range=tuple(variant["paragraph_range"]),
        )
        for index, variant in enumerate(variants)
    ]
    embeddings = embedder.embed(chunks)

    # EphemeralClient keeps this experiment independent from the application's
    # persistent Chroma index and source-of-record data.
    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        name=f"chunking-ablation-{uuid4().hex}",
    )
    collection.add(
        ids=[chunk.id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "variant": variant["name"],
                "paragraph_start": variant["paragraph_range"][0],
                "paragraph_end": variant["paragraph_range"][1],
            }
            for variant in variants
        ],
        embeddings=embeddings.tolist(),
    )

    measurements = []
    for query in queries:
        results = collection.query(
            query_embeddings=[embedder.embed_query(query).tolist()],
            n_results=len(variants),
            include=["distances", "metadatas"],
        )
        candidates = []
        for rank, (distance, metadata) in enumerate(
            zip(results["distances"][0], results["metadatas"][0]),
            start=1,
        ):
            candidates.append(
                {
                    "variant": metadata["variant"],
                    "paragraph_range": [
                        metadata["paragraph_start"],
                        metadata["paragraph_end"],
                    ],
                    "rank": rank,
                    "distance": distance,
                    "passes_production_threshold": (
                        distance <= config.SIMILARITY_THRESHOLD
                    ),
                }
            )
        measurements.append({"query": query, "candidates": candidates})

    return {
        "source_path": str(source_path),
        "target_paragraph": target_paragraph,
        "similarity_threshold": config.SIMILARITY_THRESHOLD,
        "variants": variants,
        "measurements": measurements,
    }
