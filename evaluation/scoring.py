def has_expected_evidence(
    expected_evidence: list[dict],
    observed_evidence: list[dict],
) -> bool:
    for expected in expected_evidence:
        for observed in observed_evidence:
            if _evidence_covers(expected, observed):
                return True

    return False


def _evidence_covers(
    expected: dict,
    observed: dict,
) -> bool:
    if expected.get("source_id") != observed.get("source_id"):
        return False

    if "page" in expected:
        return observed.get("page") == expected["page"]

    if "line_range" in expected:
        return _range_covers(
            expected["line_range"],
            observed.get("line_range"),
        )

    if "paragraph_range" in expected:
        return _range_covers(
            expected["paragraph_range"],
            observed.get("paragraph_range"),
        )

    return False


def _range_covers(
    expected_range: list[int] | tuple[int, int],
    observed_range: list[int] | tuple[int, int] | None,
) -> bool:
    if observed_range is None:
        return False

    expected_start, expected_end = expected_range
    observed_start, observed_end = observed_range

    return (
        observed_start <= expected_start
        and observed_end >= expected_end
    )
