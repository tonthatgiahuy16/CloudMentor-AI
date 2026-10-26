import pytest

from evaluation.runner import score_retrieval


CASES = [
    {
        "case_id": "case-hit",
        "answerable": True,
        "expected_evidence": [
            {
                "source_id": "source-1",
                "line_range": [2, 2],
            }
        ],
    },
    {
        "case_id": "case-miss",
        "answerable": True,
        "expected_evidence": [
            {
                "source_id": "source-2",
                "page": 1,
            }
        ],
    },
    {
        "case_id": "case-unanswerable",
        "answerable": False,
        "expected_evidence": [],
    },
]


def test_scores_retrieval_hits_for_answerable_cases():
    scorecard = score_retrieval(
        CASES,
        [
            {
                "case_id": "case-hit",
                "retrieved_evidence": [
                    {
                        "source_id": "source-1",
                        "line_range": [1, 3],
                    }
                ],
            },
            {
                "case_id": "case-miss",
                "retrieved_evidence": [
                    {
                        "source_id": "source-2",
                        "page": 2,
                    }
                ],
            },
            {
                "case_id": "case-unanswerable",
                "retrieved_evidence": [],
            },
        ],
    )

    assert scorecard.answerable_case_count == 2
    assert scorecard.retrieval_hits == 1
    assert scorecard.retrieval_hit_rate == 0.5
    assert scorecard.unanswerable_case_count == 1
    assert scorecard.unanswerable_cases_with_results == 0


def test_rejects_missing_case_observation():
    with pytest.raises(
        ValueError,
        match="missing observations",
    ):
        score_retrieval(
            CASES,
            [
                {
                    "case_id": "case-hit",
                    "retrieved_evidence": [],
                }
            ],
        )


def test_rejects_unknown_case_observation():
    with pytest.raises(
        ValueError,
        match="unknown observation",
    ):
        score_retrieval(
            CASES,
            [
                {
                    "case_id": "case-hit",
                    "retrieved_evidence": [],
                },
                {
                    "case_id": "case-miss",
                    "retrieved_evidence": [],
                },
                {
                    "case_id": "case-unanswerable",
                    "retrieved_evidence": [],
                },
                {
                    "case_id": "unknown-case",
                    "retrieved_evidence": [],
                },
            ],
        )


def test_counts_unanswerable_cases_with_retrieved_context():
    scorecard = score_retrieval(
        CASES,
        [
            {
                "case_id": "case-hit",
                "retrieved_evidence": [],
            },
            {
                "case_id": "case-miss",
                "retrieved_evidence": [],
            },
            {
                "case_id": "case-unanswerable",
                "retrieved_evidence": [
                    {
                        "source_id": "source-1",
                        "line_range": [1, 3],
                    }
                ],
            },
        ],
    )

    assert scorecard.unanswerable_case_count == 1
    assert scorecard.unanswerable_cases_with_results == 1
