from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.demo_seed import get_demo_seed_service, router
from app.core import config


class FakeService:
    def __init__(self): self.calls = 0
    def seed(self):
        self.calls += 1
        return {"subject_id": "demo", "seeded": 4, "skipped": 0}


def make_client(service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_demo_seed_service] = lambda: service
    return TestClient(app)


def test_demo_seed_requires_matching_token(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "DEMO_SEED_TOKEN", "seed-secret")
    service = FakeService()
    client = make_client(service)
    assert client.post("/internal/demo-seed").status_code == 403
    assert client.post("/internal/demo-seed", headers={"X-Demo-Seed-Token": "wrong"}).status_code == 403
    response = client.post("/internal/demo-seed", headers={"X-Demo-Seed-Token": "seed-secret"})
    assert response.status_code == 200
    assert response.json()["seeded"] == 4
    assert service.calls == 1
