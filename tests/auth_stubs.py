"""Shared authentication stubs for router-level API tests.

These tests build a small FastAPI app around one router, so they
override the auth dependencies instead of issuing real tokens. The
route-inventory and auth behaviour tests in ``test_auth.py`` and
``test_route_authorization.py`` exercise the real dependencies.
"""

from types import SimpleNamespace

from app.api.deps import (
    require_admin,
    require_authenticated,
)


def make_user(
    *,
    role: str = "admin",
    employee_id: str = "admin-test",
):
    return SimpleNamespace(
        user_id="user-test",
        employee_id=employee_id,
        role=role,
        is_active=True,
    )


def override_auth(
    app,
    *,
    role: str = "admin",
    employee_id: str = "admin-test",
):
    user = make_user(role=role, employee_id=employee_id)

    app.dependency_overrides[require_admin] = lambda: user
    app.dependency_overrides[require_authenticated] = lambda: user

    return user
