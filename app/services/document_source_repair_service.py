from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class DocumentSourceRepairPlan:
    document_id: str
    source_path: Path
    target_path: Path
    source_uri: str
    content_sha256: str
    file_size_bytes: int


class DocumentSourceRepairService:
    def __init__(
        self,
        *,
        document_repo,
        upload_dir: Path,
    ):
        self.document_repo = document_repo
        self.upload_dir = upload_dir

    def plan(
        self,
        *,
        document_id: str,
        source_path: Path,
    ) -> DocumentSourceRepairPlan:
        document = self.document_repo.get_by_id(
            document_id
        )

        if document is None:
            raise RuntimeError("Document not found")

        if not source_path.is_file():
            raise RuntimeError("Source file not found")

        if source_path.suffix.lower() != ".pdf":
            raise RuntimeError(
                "Source file must be a PDF"
            )

        source_data = source_path.read_bytes()

        if not source_data.startswith(b"%PDF-"):
            raise RuntimeError(
                "Source file content is not a PDF"
            )

        original_name = document.filename

        if (
            Path(original_name).name != original_name
            or "\\" in original_name
        ):
            raise RuntimeError(
                "Document filename is unsafe"
            )

        target_path = (
            self.upload_dir
            / f"{document_id}_{original_name}"
        )

        return DocumentSourceRepairPlan(
            document_id=document_id,
            source_path=source_path,
            target_path=target_path,
            source_uri=target_path.as_posix(),
            content_sha256=(
                sha256(source_data).hexdigest()
            ),
            file_size_bytes=len(source_data),
        )

    def apply(
        self,
        plan: DocumentSourceRepairPlan,
    ):
        source_data = plan.source_path.read_bytes()
        source_sha256 = sha256(
            source_data
        ).hexdigest()

        if (
            len(source_data) != plan.file_size_bytes
            or source_sha256
            != plan.content_sha256
        ):
            raise RuntimeError(
                "Source file changed after planning"
            )

        plan.target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with plan.target_path.open("xb") as target:
                target.write(source_data)

        except FileExistsError:
            existing_data = (
                plan.target_path.read_bytes()
            )

            if (
                len(existing_data)
                != plan.file_size_bytes
                or sha256(
                    existing_data
                ).hexdigest()
                != plan.content_sha256
            ):
                raise RuntimeError(
                    "Target source file conflict"
                )

        except Exception:
            plan.target_path.unlink(
                missing_ok=True
            )
            raise

        return (
            self.document_repo
            .attach_source_metadata(
                document_id=plan.document_id,
                source_uri=plan.source_uri,
                content_sha256=(
                    plan.content_sha256
                ),
                file_size_bytes=(
                    plan.file_size_bytes
                ),
            )
        )