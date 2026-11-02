import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4


class DemoSeedService:
    def __init__(self, *, subject_repo, pdf_service, seed_dir: Path):
        self.subject_repo = subject_repo
        self.pdf_service = pdf_service
        self.seed_dir = seed_dir

    def seed(self) -> dict:
        manifest_path = self.seed_dir / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            subject_name = manifest["subject"]
            documents = manifest["documents"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("Demo seed manifest is invalid") from exc

        subject = self.subject_repo.get_by_name(subject_name)
        if subject is None:
            subject = self.subject_repo.create(name=subject_name)

        seeded = 0
        skipped = 0
        for entry in documents:
            filename = entry.get("filename") if isinstance(entry, dict) else None
            chapter = entry.get("chapter") if isinstance(entry, dict) else None
            if not isinstance(filename, str) or Path(filename).name != filename:
                raise RuntimeError("Demo seed manifest contains an invalid filename")
            source_path = self.seed_dir / filename
            data = source_path.read_bytes()
            digest = sha256(data).hexdigest()
            if self.pdf_service.find_active_duplicate(
                subject_id=subject.subject_id, content_sha256=digest,
            ) is not None:
                skipped += 1
                continue
            self.pdf_service.upload(
                source_data=data,
                subject_id=subject.subject_id,
                chapter=chapter,
                document_id=str(uuid4()),
                original_filename=filename,
                content_sha256=digest,
                file_size_bytes=len(data),
            )
            seeded += 1
        return {"subject_id": subject.subject_id, "seeded": seeded, "skipped": skipped}
