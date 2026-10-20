from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

@dataclass(frozen=True)


class StoredSource:
    source_uri: str
    content_sha256: str
    file_size_bytes: int


class SourceStorage(Protocol):
    def store(
        self,
        *,
        document_id: str,
        filename: str,
        data: bytes,
    ) -> StoredSource:
        ...

    def read_bytes(
        self,
        source_uri: str,
    ) -> bytes:
        ...

class SourceStorageError(RuntimeError):
    pass


class SourceNotFoundError(SourceStorageError):
    pass


class SourceUnavailableError(SourceStorageError):
    pass


class SourceConflictError(SourceStorageError):
    pass


class LocalSourceStorage:
    def __init__(
        self,
        *,
        root: Path,
    ):
        self.root = root

    def read_bytes(
        self,
        source_uri: str,
    ) -> bytes:
        return Path(source_uri).read_bytes()

    def store(
        self,
        *,
        document_id: str,
        filename: str,
        data: bytes,
    ) -> StoredSource:
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = (
            self.root
            / f"{document_id}_{filename}"
        )

        if target_path.exists():
            existing_data = target_path.read_bytes()

            if existing_data != data:
                raise SourceConflictError(
                    "Stored source has different content"
                )
        else:
            target_path.write_bytes(data)

        return StoredSource(
            source_uri=target_path.as_posix(),
            content_sha256=(
                sha256(data).hexdigest()
            ),
            file_size_bytes=len(data),
        )
