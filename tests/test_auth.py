from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import jwt
import pytest

from app.api.auth import router as auth_router
from app.api.deps import (
    get_db,
    require_admin,
    require_authenticated,
)
from app.core import config
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db_models.user import User
from app.repos.user_repository import UserRepository


def test_password_is_hashed_and_verifiable():
    password_hash = hash_password("correct horse battery")

    assert password_hash != "correct horse battery"
    assert password_hash.startswith("$argon2")
    assert verify_password(
        "correct horse battery",
        password_hash,
    )
    assert not verify_password("wrong", password_hash)


def test_access_token_round_trip_contains_role_and_subject():
    token = create_access_token(
        employee_id="alice",
        role="employee",
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "alice"
    assert payload["role"] == "employee"
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_expired_token_is_rejected():
    token = create_access_token(
        employee_id="alice",
        role="employee",
        expires_minutes=-1,
    )

    with pytest.raises(TokenError, match="expired"):
        decode_access_token(token)


def test_token_signed_with_wrong_secret_is_rejected():
    token = jwt.encode(
        {
            "sub": "alice",
            "role": "admin",
            "type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(
                (
                    datetime.now(timezone.utc)
                    + timedelta(minutes=5)
                ).timestamp()
            ),
        },
        "not-the-configured-secret",
        algorithm="HS256",
    )

    with pytest.raises(TokenError, match="invalid token"):
        decode_access_token(token)


def test_token_with_unsupported_role_is_rejected():
    token = jwt.encode(
        {
            "sub": "alice",
            "role": "superuser",
            "type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(
                (
                    datetime.now(timezone.utc)
                    + timedelta(minutes=5)
                ).timestamp()
            ),
        },
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )

    with pytest.raises(TokenError, match="invalid role"):
        decode_access_token(token)


def _client_with_db(db_session):
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/me")
    def me(user=Depends(require_authenticated)):
        return {
            "employee_id": user.employee_id,
            "role": user.role,
        }

    @app.get("/admin-only")
    def admin_only(user=Depends(require_admin)):
        return {"employee_id": user.employee_id}

    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def _create_user(
    db_session,
    *,
    employee_id="alice",
    password="correct horse battery",
    role="employee",
    is_active=True,
):
    user = UserRepository(db_session).create(
        employee_id=employee_id,
        password_hash=hash_password(password),
        role=role,
    )
    if not is_active:
        user.is_active = False
        db_session.commit()
    return user


def test_missing_token_returns_401(quiz_db_session):
    client = _client_with_db(quiz_db_session)

    response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_valid_token_returns_current_user(quiz_db_session):
    _create_user(quiz_db_session)
    client = _client_with_db(quiz_db_session)
    token = create_access_token(
        employee_id="alice",
        role="employee",
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "employee_id": "alice",
        "role": "employee",
    }


def test_inactive_user_cannot_use_an_existing_token(
    quiz_db_session,
):
    _create_user(quiz_db_session, is_active=False)
    client = _client_with_db(quiz_db_session)
    token = create_access_token(
        employee_id="alice",
        role="employee",
    )

    response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_employee_is_forbidden_from_admin_route(quiz_db_session):
    _create_user(quiz_db_session)
    client = _client_with_db(quiz_db_session)
    token = create_access_token(
        employee_id="alice",
        role="employee",
    )

    response = client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_use_admin_route(quiz_db_session):
    _create_user(
        quiz_db_session,
        employee_id="root",
        role="admin",
    )
    client = _client_with_db(quiz_db_session)
    token = create_access_token(
        employee_id="root",
        role="admin",
    )

    response = client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_token_endpoint_issues_bearer_token(quiz_db_session):
    _create_user(
        quiz_db_session,
        employee_id="root",
        role="admin",
    )
    client = _client_with_db(quiz_db_session)

    response = client.post(
        "/auth/token",
        data={
            "username": "root",
            "password": "correct horse battery",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["employee_id"] == "root"
    assert payload["role"] == "admin"
    assert payload["expires_in"] > 0
    assert decode_access_token(
        payload["access_token"]
    )["role"] == "admin"


def test_token_endpoint_rejects_wrong_password(quiz_db_session):
    _create_user(quiz_db_session)
    client = _client_with_db(quiz_db_session)

    response = client.post(
        "/auth/token",
        data={
            "username": "alice",
            "password": "wrong",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Incorrect employee_id or password",
    }
