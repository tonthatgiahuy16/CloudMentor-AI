import argparse
import json
from pathlib import Path

from app.rag.embedder import EmbeddingService
from evaluation.chunking_ablation import run_ablation


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target-paragraph", type=int, required=True)
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = run_ablation(
        source_path=args.source,
        target_paragraph=args.target_paragraph,
        queries=args.query,
        embedder=EmbeddingService(),
    )
    args.output.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
