from hashlib import sha256
from io import BytesIO
from pathlib import Path

from app.storage.source_storage import (
    SourceConflictError,
    SourceNotFoundError,
    SourceUnavailableError,
    StoredSource,
)
from urllib.parse import urlparse
from minio.error import S3Error
from urllib3.exceptions import HTTPError


class MinioSourceStorage:
    def __init__(
        self,
        *,
        client,
        bucket_name: str,
    ):
        self.client = client
        self.bucket_name = bucket_name

    def source_uri_for(
        self,
        *,
        document_id: str,
        filename: str,
    ) -> str:
        extension = Path(filename).suffix.lower()
        object_key = (
            f"documents/{document_id}/"
            f"source{extension}"
        )

        return (
            f"minio://{self.bucket_name}/"
            f"{object_key}"
        )

    def store(
        self,
        *,
        document_id: str,
        filename: str,
        data: bytes,
    ) -> StoredSource:
        source_uri = self.source_uri_for(
            document_id=document_id,
            filename=filename,
        )
        object_key = urlparse(
            source_uri
        ).path.lstrip("/")

        stored_source = StoredSource(
            source_uri=source_uri,
            content_sha256=sha256(data).hexdigest(),
            file_size_bytes=len(data),
        )

        try:
            existing_data = self.read_bytes(
                source_uri
            )
        except SourceNotFoundError:
            existing_data = None

        if existing_data == data:
            return stored_source

        if existing_data is not None:
            raise SourceConflictError(
                "Stored source has different content"
            )

        self.client.put_object(
            self.bucket_name,
            object_key,
            BytesIO(data),
            len(data),
        )

        return stored_source

    def read_bytes(
        self,
        source_uri: str,
    ) -> bytes:
        parsed_uri = urlparse(source_uri)

        if (
            parsed_uri.scheme != "minio"
            or parsed_uri.netloc
            != self.bucket_name
            or not parsed_uri.path.lstrip("/")
        ):
            raise ValueError(
                "Invalid MinIO source URI"
            )

        object_key = parsed_uri.path.lstrip("/")

        try:
            response = self.client.get_object(
                self.bucket_name,
                object_key,
            )
        except S3Error as exc:
            if exc.code in {
                "NoSuchKey",
                "NoSuchObject",
            }:
                raise SourceNotFoundError(
                    "Stored source does not exist"
                ) from exc

            raise SourceUnavailableError(
                "Source storage is temporarily unavailable"
            ) from exc
        except HTTPError as exc:
            raise SourceUnavailableError(
                "Source storage is temporarily unavailable"
            ) from exc

        try:
            return response.read()
        except HTTPError as exc:
            raise SourceUnavailableError(
                "Source storage is temporarily unavailable"
            ) from exc
        finally:
            response.close()
            response.release_conn()
