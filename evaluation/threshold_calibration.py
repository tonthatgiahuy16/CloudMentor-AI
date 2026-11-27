"""Threshold calibration for retrieval relevance.

The retriever drops chunks whose cosine distance exceeds
``1 - min_similarity``. Choosing that cutoff by intuition is fragile,
so this module turns diagnostic observations (distances for every
candidate, including filtered ones) into a threshold sweep with the
two error rates that matter:

* false refusal: an answerable case loses its supporting evidence;
* false answer: an unanswerable case still returns any chunk.

The recommended cutoff keeps the answerable hit rate at or above a
minimum while minimising false answers. The sweep is intentionally
printed, not hidden, so a threshold can be justified in review.
"""

from dataclasses import asdict, dataclass
from typing import Any

from evaluation.scoring import _evidence_covers


@dataclass(frozen=True)
class ThresholdPoint:
    min_similarity: float
    max_distance: float
    answerable_hit_count: int
    answerable_case_count: int
    answerable_hit_rate: float
    unanswerable_with_results: int
    unanswerable_case_count: int
    false_answer_rate: float


def default_thresholds(
    start: float = 0.0,
    stop: float = 0.95,
    step: float = 0.05,
) -> list[float]:
    thresholds = []
    value = start

    while value <= stop + 1e-9:
        thresholds.append(round(value, 4))
        value += step

    return thresholds


def evaluate_thresholds(
    cases: list[dict],
    observations: list[dict],
    thresholds: list[float] | None = None,
) -> list[ThresholdPoint]:
    if thresholds is None:
        thresholds = default_thresholds()

    cases_by_id = {
        case["case_id"]: case for case in cases
    }
    observations_by_id = {
        observation["case_id"]: observation
        for observation in observations
    }

    missing = set(cases_by_id) - set(
        observations_by_id
    )
    if missing:
        raise ValueError(
            "missing observations: "
            + ", ".join(sorted(missing))
        )

    points = []

    for min_similarity in thresholds:
        if not 0 <= min_similarity <= 1:
            raise ValueError(
                "min_similarity must be between 0 and 1"
            )

        max_distance = 1.0 - min_similarity
        hit_count = 0
        answerable_count = 0
        unanswerable_with_results = 0
        unanswerable_count = 0

        for case_id, case in cases_by_id.items():
            observation = observations_by_id[
                case_id
            ]
            candidates = [
                candidate
                for candidate in observation.get(
                    "diagnostic_results",
                    [],
                )
                if candidate.get("distance", 2.0)
                <= max_distance
            ]

            if not case["answerable"]:
                unanswerable_count += 1
                if candidates:
                    unanswerable_with_results += 1
                continue

            answerable_count += 1
            expected_evidence = case[
                "expected_evidence"
            ]

            if any(
                _evidence_covers(expected, candidate)
                for expected in expected_evidence
                for candidate in candidates
            ):
                hit_count += 1

        points.append(
            ThresholdPoint(
                min_similarity=min_similarity,
                max_distance=round(max_distance, 4),
                answerable_hit_count=hit_count,
                answerable_case_count=answerable_count,
                answerable_hit_rate=(
                    round(hit_count / answerable_count, 4)
                    if answerable_count
                    else 0.0
                ),
                unanswerable_with_results=(
                    unanswerable_with_results
                ),
                unanswerable_case_count=(
                    unanswerable_count
                ),
                false_answer_rate=(
                    round(
                        unanswerable_with_results
                        / unanswerable_count,
                        4,
                    )
                    if unanswerable_count
                    else 0.0
                ),
            )
        )

    return points


def recommend_threshold(
    points: list[ThresholdPoint],
    *,
    min_hit_rate: float = 0.9,
) -> ThresholdPoint:
    if not points:
        raise ValueError("threshold points are required")

    eligible = [
        point
        for point in points
        if point.answerable_hit_rate >= min_hit_rate
    ]

    if not eligible:
        return max(
            points,
            key=lambda point: (
                point.answerable_hit_rate,
                -point.false_answer_rate,
                -point.min_similarity,
            ),
        )

    return min(
        eligible,
        key=lambda point: (
            point.false_answer_rate,
            -point.answerable_hit_rate,
            -point.min_similarity,
        ),
    )


def build_calibration_report(
    cases: list[dict],
    observations: list[dict],
    thresholds: list[float] | None = None,
    min_hit_rate: float = 0.9,
) -> dict[str, Any]:
    points = evaluate_thresholds(
        cases,
        observations,
        thresholds,
    )
    recommended = recommend_threshold(
        points,
        min_hit_rate=min_hit_rate,
    )

    return {
        "min_hit_rate": min_hit_rate,
        "recommended": asdict(recommended),
        "sweep": [asdict(point) for point in points],
    }
