from dataclasses import asdict

from evaluation.answer_runner import score_answers


def test_aggregates_answer_quality_metrics():
    sources = [
        {
            "source_id": "storage-basics-txt",
            "path": "fixtures/storage_basics.txt",
        }
    ]
    cases = [
        {
            "case_id": "storage-001",
            "answerable": True,
            "expected_facts": [
                "The original source file is retained in configured source storage."
            ],
            "expected_evidence": [
                {
                    "source_id": "storage-basics-txt",
                    "line_range": [2, 2],
                }
            ],
        },
        {
            "case_id": "backup-002",
            "answerable": False,
            "expected_facts": [],
            "expected_evidence": [],
        },
    ]
    observations = [
        {
            "case_id": "storage-001",
            "answer": (
                "The original source file is retained in configured source storage."
            ),
            "answer_correct": True,
            "sources": [
                {
                    "source": "storage_basics.txt",
                    "line_range": [1, 3],
                }
            ],
            "faithful": True,
        },
        {
            "case_id": "backup-002",
            "answer": "I cannot find that information in the provided documents.",
            "refusal_correct": True,
            "sources": [],
            "faithful": True,
        },
    ]

    scorecard = score_answers(sources, cases, observations)

    assert asdict(scorecard) == {
        "answerable_case_count": 1,
        "answer_correct_count": 1,
        "answer_correct_rate": 1.0,
        "citation_hit_count": 1,
        "citation_hit_rate": 1.0,
        "faithful_count": 1,
        "faithful_rate": 1.0,
        "unanswerable_case_count": 1,
        "refusal_correct_count": 1,
        "refusal_correct_rate": 1.0,
    }
