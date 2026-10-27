from pathlib import Path

from evaluation.scoring import has_expected_evidence


def score_answer_observation(
    case: dict,
    observation: dict,
    source_index: dict[str, dict],
) -> dict[str, bool | None]:
    """Score one human-reviewed chat response."""
    faithful = _reviewed_bool(observation, "faithful")

    if not case["answerable"]:
        return {
            "answer_correct": None,
            "citation_hit": None,
            "faithful": faithful,
            "refusal_correct": _reviewed_bool(
                observation,
                "refusal_correct",
            ),
        }

    observed_evidence = _to_observed_evidence(
        observation["sources"],
        source_index,
    )

    return {
        "answer_correct": _reviewed_bool(
            observation,
            "answer_correct",
        ),
        "citation_hit": has_expected_evidence(
            case["expected_evidence"],
            observed_evidence,
        ),
        "faithful": faithful,
        "refusal_correct": None,
    }


def _reviewed_bool(
    observation: dict,
    field: str,
) -> bool:
    value = observation.get(field)

    if not isinstance(value, bool):
        raise ValueError(
            f"missing or invalid review label: {field}"
        )

    return value


def _to_observed_evidence(
    sources: list[dict],
    source_index: dict[str, dict],
) -> list[dict]:
    source_ids_by_filename = {
        Path(source["path"]).name: source_id
        for source_id, source in source_index.items()
    }
    evidence = []

    for source in sources:
        source_id = (
            source.get("source_id")
            or source_ids_by_filename.get(source.get("source"))
        )
        item = {"source_id": source_id}

        if source.get("page") is not None:
            item["page"] = source["page"]

        elif source.get("line_range") is not None:
            item["line_range"] = source["line_range"]
        elif source.get("paragraph_range") is not None:
            item["paragraph_range"] = source["paragraph_range"]

        evidence.append(item)

    return evidence
