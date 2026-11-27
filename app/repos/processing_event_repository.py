from sqlalchemy.orm import Session

from app.db_models.processing_event import ProcessingEvent


class ProcessingEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        document_id: str,
        stage: str,
        status: str,
        duration_ms: int,
        request_id: str | None = None,
        error_code: str | None = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            document_id=document_id,
            stage=stage,
            status=status,
            duration_ms=max(int(duration_ms), 0),
            request_id=request_id,
            error_code=error_code,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
