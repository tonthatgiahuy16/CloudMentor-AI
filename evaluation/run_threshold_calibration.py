"""Run threshold calibration against a live evaluation index.

Requires the evaluation subjects to be ingested (the same subjects
file used by ``run_live_retrieval``). Diagnostic observations include
chunks that the production threshold would drop, which is what makes
the sweep meaningful.
"""

import argparse
import json
from pathlib import Path

from app.rag.embedder import EmbeddingService
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from evaluation.dataset import validate_dataset
from evaluation.live_retrieval import collect_observations
from evaluation.threshold_calibration import (
    build_calibration_report,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--subjects",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--min-hit-rate",
        type=float,
        default=0.9,
    )
    args = parser.parse_args(argv)

    dataset = json.loads(
        args.dataset.read_text(encoding="utf-8-sig")
    )
    validate_dataset(dataset, args.dataset.parent)

    subject_ids = json.loads(
        args.subjects.read_text(encoding="utf-8-sig")
    )

    observations = collect_observations(
        dataset,
        subject_ids,
        EmbeddingService(),
        Retriever(VectorStore()),
        diagnostic_include_filtered=True,
    )["observations"]

    report = build_calibration_report(
        dataset["cases"],
        observations,
        min_hit_rate=args.min_hit_rate,
    )

    args.output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report["recommended"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
