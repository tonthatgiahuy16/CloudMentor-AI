from sqlalchemy.orm import Session

from app.db_models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee_id(
        self,
        employee_id: str,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.employee_id == employee_id)
            .first()
        )

    def create(
        self,
        *,
        employee_id: str,
        password_hash: str,
        role: str,
        display_name: str | None = None,
    ) -> User:
        user = User(
            employee_id=employee_id,
            password_hash=password_hash,
            role=role,
            display_name=display_name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(
        self,
        *,
        user: User,
        password_hash: str,
    ) -> User:
        user.password_hash = password_hash
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_active(
        self,
        *,
        user: User,
        is_active: bool,
    ) -> User:
        user.is_active = is_active
        self.db.commit()
        self.db.refresh(user)
        return user
