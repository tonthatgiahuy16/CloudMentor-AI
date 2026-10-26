import argparse
import json
from dataclasses import asdict
from pathlib import Path

from evaluation.dataset import validate_dataset
from evaluation.runner import score_retrieval


def read_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8-sig")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--observations",
        type=Path,
        required=True,
    )

    args = parser.parse_args(argv)

    dataset = read_json(args.dataset)
    validate_dataset(dataset, args.dataset.parent)

    observations_payload = read_json(args.observations)
    scorecard = score_retrieval(
        dataset["cases"],
        observations_payload["observations"],
    )

    print(json.dumps(asdict(scorecard), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
