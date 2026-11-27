from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_db
from app.core import config
from app.core.security import (
    create_access_token,
    verify_password,
)
from app.repos.user_repository import UserRepository
from app.schemas.auth import TokenResponse


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/token",
    response_model=TokenResponse,
)
def issue_token(
    form: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    """Exchange employee credentials for a short-lived bearer token.

    `username` is the employee_id. The same generic error is returned for
    an unknown employee and a wrong password to avoid account enumeration.
    """

    employee_id = form.username.strip()
    user = UserRepository(db).get_by_employee_id(
        employee_id
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(
            form.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(
            employee_id=user.employee_id,
            role=user.role,
        ),
        "token_type": "bearer",
        "expires_in": (
            config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ),
        "employee_id": user.employee_id,
        "role": user.role,
    }
