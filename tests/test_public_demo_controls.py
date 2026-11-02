from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router as health_router
from app.api.subjects import (
    get_subject_repository,
    router as subjects_router,
)
from app.core import config
from app.core.rate_limit import SlidingWindowRateLimiter


class FakeSubjectRepository:
    def create(self, *, name):
        raise AssertionError("Demo mode must block before repository use")


def test_demo_mode_blocks_subject_creation(monkeypatch):
    app = FastAPI()
    app.include_router(subjects_router)
    app.dependency_overrides[get_subject_repository] = (
        lambda: FakeSubjectRepository()
    )
    monkeypatch.setattr(config, "DEMO_MODE", True)

    response = TestClient(app).post(
        "/subjects/",
        json={"name": "Public demo subject"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Demo mode does not allow data changes",
    }


def test_sliding_window_rate_limiter_blocks_the_next_request():
    limiter = SlidingWindowRateLimiter(limit=1)

    assert limiter.allow("198.51.100.10") is True
    assert limiter.allow("198.51.100.10") is False
    assert limiter.allow("198.51.100.11") is True


def test_liveness_does_not_require_dependencies():
    app = FastAPI()
    app.include_router(health_router)

    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_dependency_failures(monkeypatch):
    app = FastAPI()
    app.include_router(health_router)

    def unavailable_database():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "app.api.health.check_database_connection",
        unavailable_database,
    )

    response = TestClient(app, raise_server_exceptions=False).get(
        "/readyz"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Dependencies are not ready",
    }
