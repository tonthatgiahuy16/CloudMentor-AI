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