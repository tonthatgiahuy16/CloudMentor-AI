from dataclasses import dataclass

from evaluation.answer_scoring import score_answer_observation


@dataclass(frozen=True)
class AnswerScorecard:
    answerable_case_count: int
    answer_correct_count: int
    answer_correct_rate: float
    citation_hit_count: int
    citation_hit_rate: float
    faithful_count: int
    faithful_rate: float
    unanswerable_case_count: int
    refusal_correct_count: int
    refusal_correct_rate: float


def score_answers(
    sources: list[dict],
    cases: list[dict],
    observations: list[dict],
) -> AnswerScorecard:
    source_index = _index_by_id(sources, "source")
    cases_by_id = _index_by_id(cases, "case")
    observations_by_id = _index_observations(
        observations,
        cases_by_id,
    )

    missing_case_ids = set(cases_by_id) - set(
        observations_by_id
    )
    if missing_case_ids:
        missing = ", ".join(sorted(missing_case_ids))
        raise ValueError(f"missing observations: {missing}")

    answerable_case_count = 0
    answer_correct_count = 0
    citation_hit_count = 0
    faithful_count = 0
    unanswerable_case_count = 0
    refusal_correct_count = 0

    for case_id, case in cases_by_id.items():
        result = score_answer_observation(
            case,
            observations_by_id[case_id],
            source_index,
        )

        if case["answerable"]:
            answerable_case_count += 1
            answer_correct_count += (
                result["answer_correct"] is True
            )
            citation_hit_count += (
                result["citation_hit"] is True
            )
            faithful_count += result["faithful"] is True
        else:
            unanswerable_case_count += 1
            refusal_correct_count += (
                result["refusal_correct"] is True
            )

    return AnswerScorecard(
        answerable_case_count=answerable_case_count,
        answer_correct_count=answer_correct_count,
        answer_correct_rate=_rate(
            answer_correct_count,
            answerable_case_count,
        ),
        citation_hit_count=citation_hit_count,
        citation_hit_rate=_rate(
            citation_hit_count,
            answerable_case_count,
        ),
        faithful_count=faithful_count,
        faithful_rate=_rate(
            faithful_count,
            answerable_case_count,
        ),
        unanswerable_case_count=unanswerable_case_count,
        refusal_correct_count=refusal_correct_count,
        refusal_correct_rate=_rate(
            refusal_correct_count,
            unanswerable_case_count,
        ),
    )


def _index_by_id(
    items: list[dict],
    item_label: str,
) -> dict[str, dict]:
    indexed = {}

    for item in items:
        item_id = item[f"{item_label}_id"]

        if item_id in indexed:
            raise ValueError(
                f"duplicate {item_label}_id: {item_id}"
            )

        indexed[item_id] = item

    return indexed


def _index_observations(
    observations: list[dict],
    cases_by_id: dict[str, dict],
) -> dict[str, dict]:
    indexed = {}

    for observation in observations:
        case_id = observation["case_id"]

        if case_id in indexed:
            raise ValueError(
                f"duplicate observation: {case_id}"
            )

        if case_id not in cases_by_id:
            raise ValueError(
                f"unknown observation: {case_id}"
            )

        indexed[case_id] = observation

    return indexed


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0
