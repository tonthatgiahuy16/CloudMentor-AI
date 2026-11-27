import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core import config
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from evaluation.dataset import validate_dataset
from evaluation.threshold_calibration import (
    build_calibration_report,
    default_thresholds,
    evaluate_thresholds,
    recommend_threshold,
)


CASES = [
    {
        "case_id": "case-a1",
        "answerable": True,
        "expected_evidence": [
            {
                "source_id": "source-1",
                "line_range": [2, 2],
            }
        ],
    },
    {
        "case_id": "case-a2",
        "answerable": True,
        "expected_evidence": [
            {
                "source_id": "source-2",
                "page": 1,
            }
        ],
    },
    {
        "case_id": "case-u1",
        "answerable": False,
        "expected_evidence": [],
    },
]


OBSERVATIONS = [
    {
        "case_id": "case-a1",
        "diagnostic_results": [
            {
                "source_id": "source-1",
                "line_range": [2, 2],
                "distance": 0.2,
            },
            {
                "source_id": "source-9",
                "line_range": [1, 1],
                "distance": 0.8,
            },
        ],
    },
    {
        "case_id": "case-a2",
        "diagnostic_results": [
            {
                "source_id": "source-2",
                "page": 1,
                "distance": 0.6,
            }
        ],
    },
    {
        "case_id": "case-u1",
        "diagnostic_results": [
            {
                "source_id": "source-9",
                "line_range": [5, 5],
                "distance": 0.45,
            }
        ],
    },
]


def test_sweep_trades_false_refusal_for_false_answers():
    points = evaluate_thresholds(
        CASES,
        OBSERVATIONS,
        thresholds=[0.4, 0.6],
    )

    loose, strict = points

    assert loose.min_similarity == 0.4
    assert loose.max_distance == 0.6
    assert loose.answerable_hit_count == 2
    assert loose.unanswerable_with_results == 1
    assert loose.false_answer_rate == 1.0

    assert strict.answerable_hit_count == 1
    assert strict.unanswerable_with_results == 0
    assert strict.false_answer_rate == 0.0


def test_recommendation_keeps_hit_rate_and_minimises_false_answers():
    points = evaluate_thresholds(
        CASES,
        OBSERVATIONS,
        thresholds=[0.4, 0.6],
    )

    recommended = recommend_threshold(
        points,
        min_hit_rate=0.5,
    )

    assert recommended.min_similarity == 0.6
    assert recommended.answerable_hit_rate == 0.5
    assert recommended.false_answer_rate == 0.0


def test_recommendation_falls_back_to_best_hit_rate():
    points = evaluate_thresholds(
        CASES,
        OBSERVATIONS,
        thresholds=[0.9],
    )

    recommended = recommend_threshold(
        points,
        min_hit_rate=0.9,
    )

    assert recommended.min_similarity == 0.9
    assert recommended.answerable_hit_rate == 0.0


def test_calibration_report_is_serializable():
    report = build_calibration_report(
        CASES,
        OBSERVATIONS,
        thresholds=[0.4, 0.6],
        min_hit_rate=0.5,
    )

    assert report["recommended"]["min_similarity"] == 0.6
    assert len(report["sweep"]) == 2


def test_default_threshold_grid_is_bounded():
    thresholds = default_thresholds()

    assert thresholds[0] == 0.0
    assert thresholds[-1] == 0.95
    assert all(0 <= value <= 1 for value in thresholds)


def test_project_dataset_has_stratified_groups_and_boundaries():
    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "evaluation"
        / "cases.json"
    )
    dataset = json.loads(
        dataset_path.read_text(encoding="utf-8-sig")
    )
    validate_dataset(dataset, dataset_path.parent)

    cases = dataset["cases"]
    assert 30 <= len(cases) <= 50

    categories = {
        case["category"] for case in cases
    }
    assert {
        "lineage",
        "date-window",
        "unanswerable",
        "validation",
    } <= categories

    date_window_cases = [
        case
        for case in cases
        if case["category"] == "date-window"
    ]
    assert len(date_window_cases) >= 5
    assert all(
        evidence["source_id"] == "policy-windows-txt"
        for case in date_window_cases
        for evidence in case["expected_evidence"]
    )

    assert any(
        not case["answerable"] for case in cases
    )
    assert any(
        case["answerable"] for case in cases
    )


def test_vector_space_metadata_is_read_defensively():
    assert (
        VectorStore.collection_space(
            SimpleNamespace(metadata=None)
        )
        == "l2"
    )
    assert (
        VectorStore.collection_space(
            SimpleNamespace(metadata={"hnsw:space": "cosine"})
        )
        == "cosine"
    )


def test_retriever_drops_below_similarity_floor():
    class FakeCollection:
        def query(self, **_kwargs):
            return {
                "ids": [["chunk-1", "chunk-2"]],
                "documents": [["relevant", "weak"]],
                "metadatas": [
                    [{"document_id": "doc-1"}, {"document_id": "doc-1"}]
                ],
                "distances": [[0.3, 0.6]],
            }

    store = SimpleNamespace(collection=FakeCollection())

    results = Retriever(store).search([1.0])

    assert [result["chunk_id"] for result in results] == [
        "chunk-1"
    ]
    assert config.SIMILARITY_THRESHOLD == pytest.approx(
        1.0 - config.MIN_COSINE_SIMILARITY
    )
