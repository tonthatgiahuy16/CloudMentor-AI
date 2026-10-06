from sqlalchemy.orm import Session

from app.db_models.subject import Subject


class SubjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Subject]:
        return (
            self.db.query(Subject)
            .order_by(Subject.name.asc())
            .all()
        )

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
