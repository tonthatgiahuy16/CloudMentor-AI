"""Shared FastAPI authentication and authorization dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.database import SessionLocal
from app.core.security import TokenError, decode_access_token
from app.db_models.user import User
from app.repos.user_repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise _unauthorized("Invalid or expired access token") from exc

    user = UserRepository(db).get_by_employee_id(
        payload["sub"]
    )

    if user is None or not user.is_active:
        raise _unauthorized("User is inactive or unknown")

    return user


def require_authenticated(
    user: User = Depends(get_current_user),
) -> User:
    """Allow any authenticated user, regardless of role."""
    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )

    return user
