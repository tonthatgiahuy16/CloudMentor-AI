from dataclasses import dataclass

from evaluation.scoring import has_expected_evidence


@dataclass(frozen=True)
class RetrievalScorecard:
    unanswerable_cases_with_results: int
    answerable_case_count: int
    retrieval_hits: int
    retrieval_hit_rate: float
    unanswerable_case_count: int


def score_retrieval(
    cases: list[dict],
    observations: list[dict],
) -> RetrievalScorecard:
    cases_by_id = {}

    unanswerable_cases_with_results = 0

    for case in cases:
        case_id = case["case_id"]

        if case_id in cases_by_id:
            raise ValueError(f"duplicate case_id: {case_id}")

        cases_by_id[case_id] = case

    observations_by_id = {}

    for observation in observations:
        case_id = observation["case_id"]

        if case_id in observations_by_id:
            raise ValueError(
                f"duplicate observation: {case_id}"
            )

        if case_id not in cases_by_id:
            raise ValueError(
                f"unknown observation: {case_id}"
            )

        observations_by_id[case_id] = observation

    missing_case_ids = set(cases_by_id) - set(
        observations_by_id
    )

    if missing_case_ids:
        missing = ", ".join(sorted(missing_case_ids))
        raise ValueError(f"missing observations: {missing}")

    answerable_case_count = 0
    retrieval_hits = 0
    unanswerable_case_count = 0

    for case_id, case in cases_by_id.items():
        observation = observations_by_id[case_id]

        if not case["answerable"]:
            unanswerable_case_count += 1

            if observation["retrieved_evidence"]:
                unanswerable_cases_with_results += 1

            continue

        answerable_case_count += 1
        retrieved_evidence = observation[
            "retrieved_evidence"
        ]

        if has_expected_evidence(
            case["expected_evidence"],
            retrieved_evidence,
        ):
            retrieval_hits += 1

    retrieval_hit_rate = (
        retrieval_hits / answerable_case_count
        if answerable_case_count
        else 0.0
    )

    return RetrievalScorecard(
        answerable_case_count=answerable_case_count,
        retrieval_hits=retrieval_hits,
        retrieval_hit_rate=retrieval_hit_rate,
        unanswerable_case_count=unanswerable_case_count,
        unanswerable_cases_with_results=(
            unanswerable_cases_with_results
        ),
    )
