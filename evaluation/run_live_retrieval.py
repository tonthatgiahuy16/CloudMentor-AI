import argparse
import json
from pathlib import Path

from app.rag.embedder import EmbeddingService
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from evaluation.dataset import validate_dataset
from evaluation.live_retrieval import collect_observations


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--subjects", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-include-filtered", action="store_true")
    args = parser.parse_args(argv)
    dataset = json.loads(args.dataset.read_text(encoding="utf-8-sig"))
    validate_dataset(dataset, args.dataset.parent)
    subject_ids = json.loads(args.subjects.read_text(encoding="utf-8-sig"))
    payload = collect_observations(
        dataset, subject_ids, EmbeddingService(), Retriever(VectorStore()),
        diagnostic_include_filtered=args.diagnostic_include_filtered,
    )
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
