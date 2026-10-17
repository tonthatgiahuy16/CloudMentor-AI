from sqlalchemy.orm import Session

from app.db_models.subject import Subject

from sqlalchemy import func

class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db


    def get_by_id(
        self,
        subject_id: str,
    ) -> Subject | None:
        return (
            self.db.query(Subject)
            .filter(
                Subject.subject_id == subject_id
            )
            .first()
        )


    def list_all(self) -> list[Subject]:
        return (
            self.db.query(Subject)
            .order_by(Subject.name.asc())
            .all()
        )


    def list_active(self) -> list[Subject]:
        return (
            self.db.query(Subject)
            .filter(
                Subject.status == "ACTIVE"
            )
            .order_by(Subject.name.asc())
            .all()
        )


    def list_trash(self) -> list[Subject]:
        return (
            self.db.query(Subject)
            .filter(
                Subject.status != "ACTIVE"
            )
            .order_by(Subject.name.asc())
            .all()
        )


    def mark_deleting(
        self,
        subject_id: str,
    ) -> Subject:
        subject = self.get_by_id(subject_id)

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status not in {
            "ACTIVE",
            "DELETE_FAILED",
        }:
            raise RuntimeError(
                "Subject cannot enter deleting state"
            )

        subject.status = "DELETING"
        subject.lifecycle_error = None

        self.db.commit()
        self.db.refresh(subject)

        return subject


    def mark_deleted(
        self,
        subject_id: str,
    ) -> Subject:
        subject = self.get_by_id(subject_id)

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status == "DELETED":
            return subject

        if subject.status != "DELETING":
            raise RuntimeError(
                "Subject is not deleting"
            )

        subject.status = "DELETED"
        subject.deleted_at = func.now()
        subject.lifecycle_error = None

        self.db.commit()
        self.db.refresh(subject)

        return subject


    def mark_delete_failed(
        self,
        subject_id: str,
        error_message: str,
    ) -> Subject:
        subject = self.get_by_id(subject_id)

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status != "DELETING":
            raise RuntimeError(
                "Subject is not deleting"
            )

        subject.status = "DELETE_FAILED"
        subject.lifecycle_error = error_message

        self.db.commit()
        self.db.refresh(subject)

        return subject


    def mark_restoring(
        self,
        subject_id: str,
    ) -> Subject:
        subject = self.get_by_id(subject_id)

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status not in {
            "DELETED",
            "RESTORE_FAILED",
        }:
            raise RuntimeError(
                "Subject cannot enter restoring state"
            )

        subject.status = "RESTORING"
        subject.lifecycle_error = None

        self.db.commit()
        self.db.refresh(subject)

        return subject


    def mark_active(
    self,
    subject_id: str,
    ) -> Subject:
        subject = self.get_by_id(subject_id)

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status != "RESTORING":
            raise RuntimeError(
                "Subject is not restoring"
        )

        subject.status = "ACTIVE"
        subject.deleted_at = None
        subject.lifecycle_error = None

        self.db.commit()
        self.db.refresh(subject)

        return subject

    def mark_restore_failed(
        self,
        subject_id: str,
        error_message: str,
    ) -> Subject:
        subject = self.get_by_id(subject_id)

        if subject is None:
            raise RuntimeError("Subject not found")

        if subject.status != "RESTORING":
            raise RuntimeError(
                "Subject is not restoring"
            )

        subject.status = "RESTORE_FAILED"
        subject.lifecycle_error = error_message

        self.db.commit()
        self.db.refresh(subject)

        return subject


    def create(self, *, name: str) -> Subject:
        subject = Subject(name=name)
        self.db.add(subject)

        try:
            self.db.commit()
            self.db.refresh(subject)
        except Exception:
            self.db.rollback()
            raise

        return subject
