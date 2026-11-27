from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from app.db_models.document import Document
from app.db_models.processing_event import ProcessingEvent
from app.db_models.subject import Subject
from app.repos.processing_event_repository import (
    ProcessingEventRepository,
)
from app.services.pdf_service import PDFService
from app.services.pipeline_metrics_service import (
    PipelineMetricsService,
    _percentile,
)


class FakeDocumentRepository:
    def __init__(self, db):
        self.db = db
        self.failed = None

    def mark_processing(self, document_id):
        pass

    def record_processing_heartbeat(
        self,
        *,
        document_id,
        stage,
    ):
        pass

    def mark_indexed(
        self,
        document_id,
        *,
        indexed_chunk_count,
    ):
        pass

    def mark_failed(
        self,
        *,
        document_id,
        failed_stage,
        error_message,
    ):
        self.failed = (
            document_id,
            failed_stage,
            error_message,
        )


class FakePipeline:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def run(self, *args, **kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class FakeIndexPipeline(FakePipeline):
    def __init__(self):
        super().__init__(result=1)
        self.deleted = []

    def delete_by_document_id(self, document_id):
        self.deleted.append(document_id)
        return 0


def _service(db):
    # Bypass __init__ so this test does not import the transformer and
    # vector-index stacks; the constructor's only job here is wiring,
    # which is replaced with deterministic fakes.
    service = PDFService.__new__(PDFService)
    service.document_repo = FakeDocumentRepository(db)
    service.event_repo = None
    service.extract = FakePipeline(result=["document"])
    service.transform = FakePipeline(result=["clean"])
    service.chunk = FakePipeline(result=["chunk"])
    service.embedding = FakePipeline(result=[])
    service.index = FakeIndexPipeline()
    return service


def _events(db):
    return list(
        db.execute(
            select(ProcessingEvent).order_by(
                ProcessingEvent.occurred_at
            )
        ).scalars()
    )


def test_successful_pipeline_records_one_event_per_stage(
    quiz_db_session,
):
    service = _service(quiz_db_session)

    chunk_count = service._process_document(
        source_data=b"content",
        filename="note.txt",
        file_type="txt",
        document_id=str(uuid4()),
        subject_id=str(uuid4()),
    )

    assert chunk_count == 1
    events = _events(quiz_db_session)
    assert [event.stage for event in events] == [
        "EXTRACT",
        "TRANSFORM",
        "CHUNK",
        "EMBEDDING",
        "INDEX",
    ]
    assert all(
        event.status == "SUCCEEDED" for event in events
    )
    assert all(
        event.duration_ms >= 0 for event in events
    )


def test_failed_stage_records_failed_event_and_stops_pipeline(
    quiz_db_session,
):
    service = _service(quiz_db_session)
    service.chunk = FakePipeline(
        error=ValueError("bad chunk"),
    )

    try:
        service._process_document(
            source_data=b"content",
            filename="note.txt",
            file_type="txt",
            document_id=str(uuid4()),
            subject_id=str(uuid4()),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("pipeline should fail")

    events = _events(quiz_db_session)
    assert [event.stage for event in events] == [
        "EXTRACT",
        "TRANSFORM",
        "CHUNK",
    ]
    assert events[-1].status == "FAILED"
    assert events[-1].error_code == "ValueError"
    assert service.document_repo.failed[1] == "CHUNK"


def test_metrics_aggregates_stage_durations_and_failures(
    quiz_db_session,
):
    subject = Subject(
        subject_id=str(uuid4()),
        name="Policies",
    )
    quiz_db_session.add(subject)
    quiz_db_session.commit()

    document = Document(
        document_id=str(uuid4()),
        subject_id=subject.subject_id,
        filename="policy.txt",
        file_type="txt",
        status="INDEXED",
    )
    quiz_db_session.add(document)
    quiz_db_session.commit()

    repository = ProcessingEventRepository(
        quiz_db_session
    )
    for duration in (10, 20, 30):
        repository.record(
            document_id=document.document_id,
            stage="EXTRACT",
            status="SUCCEEDED",
            duration_ms=duration,
        )
    repository.record(
        document_id=document.document_id,
        stage="EMBEDDING",
        status="FAILED",
        duration_ms=500,
        error_code="RuntimeError",
        request_id="request-1",
    )

    report = PipelineMetricsService(
        quiz_db_session
    ).collect(window_days=7)

    extract = next(
        stage
        for stage in report["pipeline"]["stages"]
        if stage["stage"] == "EXTRACT"
    )
    embedding = next(
        stage
        for stage in report["pipeline"]["stages"]
        if stage["stage"] == "EMBEDDING"
    )

    assert extract["run_count"] == 3
    assert extract["average_duration_ms"] == 20
    assert extract["p50_duration_ms"] == 20
    assert extract["p95_duration_ms"] == 29
    assert extract["max_duration_ms"] == 30
    assert embedding["failure_count"] == 1
    assert embedding["failure_rate"] == 1.0
    assert report["pipeline"]["stage_run_count"] == 4
    assert report["pipeline"]["stage_failure_rate"] == 0.25
    assert report["document_status_counts"] == {
        "INDEXED": 1,
    }
    assert report["recent_failures"][0][
        "request_id"
    ] == "request-1"


def test_percentile_handles_empty_and_single_values():
    assert _percentile([], 0.95) is None
    assert _percentile([7], 0.95) == 7.0
    assert _percentile([1, 2, 3, 4], 0.5) == 2.5
