import json
from types import SimpleNamespace

from app.services.demo_seed_service import DemoSeedService


class FakeSubjectRepository:
    def __init__(self):
        self.subject = None

    def get_by_name(self, _name):
        return self.subject

    def create(self, *, name):
        self.subject = SimpleNamespace(subject_id="demo-subject", name=name)
        return self.subject


class FakePDFService:
    def __init__(self):
        self.digests = set()

    def find_active_duplicate(self, *, content_sha256, **_kwargs):
        return object() if content_sha256 in self.digests else None

    def upload(self, *, content_sha256, **_kwargs):
        self.digests.add(content_sha256)


def test_seed_is_idempotent_for_manifest_documents(tmp_path):
    (tmp_path / "lesson.txt").write_text("pipeline data", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({
            "subject": "Data Engineering Fundamentals",
            "documents": [{"filename": "lesson.txt", "chapter": 1}],
        }),
        encoding="utf-8",
    )
    subject_repo = FakeSubjectRepository()
    pdf_service = FakePDFService()
    service = DemoSeedService(
        subject_repo=subject_repo,
        pdf_service=pdf_service,
        seed_dir=tmp_path,
    )

    first = service.seed()
    second = service.seed()

    assert first == {"subject_id": "demo-subject", "seeded": 1, "skipped": 0}
    assert second == {"subject_id": "demo-subject", "seeded": 0, "skipped": 1}
