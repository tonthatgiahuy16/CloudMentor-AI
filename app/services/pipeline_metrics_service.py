"""Aggregate pipeline metrics from persisted stage events.

Percentiles are computed in Python over a bounded event window. That
keeps the query portable across PostgreSQL and SQLite and avoids a
database-specific percentile function, at the cost of loading the
window into memory. The window and row cap are explicit in the
response so callers can see what was measured.
"""

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_models.document import Document
from app.db_models.processing_event import (
    PROCESSING_STAGES,
    ProcessingEvent,
)


MAX_EVENT_ROWS = 50_000


def _percentile(
    values: list[int],
    percentile: float,
) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])

    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower

    return round(
        ordered[lower] * (1 - weight)
        + ordered[upper] * weight,
        2,
    )


def _summarize_durations(
    durations: list[int],
) -> dict[str, Any]:
    if not durations:
        return {
            "run_count": 0,
            "average_duration_ms": None,
            "p50_duration_ms": None,
            "p95_duration_ms": None,
            "max_duration_ms": None,
        }

    return {
        "run_count": len(durations),
        "average_duration_ms": round(
            mean(durations),
            2,
        ),
        "p50_duration_ms": _percentile(
            durations,
            0.50,
        ),
        "p95_duration_ms": _percentile(
            durations,
            0.95,
        ),
        "max_duration_ms": max(durations),
    }


class PipelineMetricsService:
    def __init__(self, db: Session):
        self.db = db

    def collect(
        self,
        *,
        window_days: int = 7,
    ) -> dict[str, Any]:
        window_days = max(1, min(window_days, 90))
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=window_days)

        events = (
            self.db.query(ProcessingEvent)
            .filter(ProcessingEvent.occurred_at >= cutoff)
            .order_by(ProcessingEvent.occurred_at.desc())
            .limit(MAX_EVENT_ROWS)
            .all()
        )

        stage_metrics = []
        total_runs = 0
        total_failed = 0

        for stage in PROCESSING_STAGES:
            stage_events = [
                event
                for event in events
                if event.stage == stage
            ]
            succeeded = [
                event
                for event in stage_events
                if event.status == "SUCCEEDED"
            ]
            failed = [
                event
                for event in stage_events
                if event.status == "FAILED"
            ]
            total_runs += len(stage_events)
            total_failed += len(failed)

            stage_metrics.append(
                {
                    "stage": stage,
                    **_summarize_durations(
                        [
                            event.duration_ms
                            for event in succeeded
                        ]
                    ),
                    "success_count": len(succeeded),
                    "failure_count": len(failed),
                    "failure_rate": (
                        round(
                            len(failed) / len(stage_events),
                            4,
                        )
                        if stage_events
                        else None
                    ),
                }
            )

        document_status_counts = {
            status: count
            for status, count in (
                self.db.query(
                    Document.status,
                    func.count(Document.document_id),
                )
                .group_by(Document.status)
                .all()
            )
        }

        recent_failures = [
            {
                "document_id": event.document_id,
                "stage": event.stage,
                "error_code": event.error_code,
                "duration_ms": event.duration_ms,
                "occurred_at": event.occurred_at,
                "request_id": event.request_id,
            }
            for event in events
            if event.status == "FAILED"
        ][:10]

        return {
            "generated_at": now,
            "window_days": window_days,
            "event_row_cap": MAX_EVENT_ROWS,
            "event_count": len(events),
            "document_status_counts": (
                document_status_counts
            ),
            "pipeline": {
                "stage_run_count": total_runs,
                "stage_failure_count": total_failed,
                "stage_failure_rate": (
                    round(total_failed / total_runs, 4)
                    if total_runs
                    else None
                ),
                "stages": stage_metrics,
            },
            "recent_failures": recent_failures,
        }
