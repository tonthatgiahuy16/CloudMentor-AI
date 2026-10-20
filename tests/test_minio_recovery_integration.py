import os
import re
import subprocess
import time

from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from minio import Minio

from app.services.pdf_service import (
    PDFService,
    RetainedSourceValidationError,
)
from app.storage.minio_source_storage import (
    MinioSourceStorage,
)
from io import BytesIO


pytestmark = pytest.mark.skipif(
    os.getenv("CLOUDMENTOR_RUN_MINIO_INTEGRATION") != "1",
    reason="Set CLOUDMENTOR_RUN_MINIO_INTEGRATION=1",
)


@pytest.fixture
def live_minio_storage():
    container_name = (
        "cloudmentor-minio-test-"
        + uuid4().hex
    )
    access_key = "test-" + uuid4().hex
    secret_key = uuid4().hex + uuid4().hex
    image = os.getenv(
        "MINIO_INTEGRATION_IMAGE",
        "cloudmentor-minio-integration:2025-10-15",
    )

    started = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--name",
            container_name,
            "--publish",
            "127.0.0.1::9000",
            "--env",
            f"MINIO_ROOT_USER={access_key}",
            "--env",
            f"MINIO_ROOT_PASSWORD={secret_key}",
            image,
            "server",
            "/data",
            "--address",
            ":9000",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert started.returncode == 0, (
        "Unable to start MinIO integration container"
    )

    try:
        port_mapping = subprocess.run(
            [
                "docker",
                "port",
                container_name,
                "9000/tcp",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        port_match = re.search(
            r":(\d+)\s*$",
            port_mapping,
        )
        assert port_match is not None

        client = Minio(
            f"127.0.0.1:{port_match.group(1)}",
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
        bucket_name = (
            "cloudmentor-test-"
            + uuid4().hex
        )

        deadline = time.monotonic() + 20
        while True:
            try:
                client.make_bucket(bucket_name)
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)

        yield client, MinioSourceStorage(
            client=client,
            bucket_name=bucket_name,
        )
    finally:
        subprocess.run(
            [
                "docker",
                "rm",
                "--force",
                container_name,
            ],
            capture_output=True,
            text=True,
            check=False,
        )


def test_real_minio_missing_object_fails_before_index_deletion(
    live_minio_storage,
):
    client, storage = live_minio_storage
    source_data = b"canonical MinIO source"

    stored = storage.store(
        document_id="document-1",
        filename="lesson.txt",
        data=source_data,
    )
    object_key = urlparse(
        stored.source_uri
    ).path.lstrip("/")
    client.remove_object(
        storage.bucket_name,
        object_key,
    )

    document = SimpleNamespace(
        document_id="document-1",
        subject_id="subject-1",
        filename="lesson.txt",
        file_type="txt",
        status="INDEXED",
        source_uri=stored.source_uri,
        content_sha256=sha256(source_data).hexdigest(),
        file_size_bytes=len(source_data),
    )

    service = PDFService.__new__(PDFService)
    service.source_storage = storage
    service.document_repo = Mock()
    service.index = Mock()

    with pytest.raises(
        RetainedSourceValidationError,
        match="Retained source file is missing",
    ):
        service.rebuild_retained_document(document)

    service.document_repo.mark_failed.assert_called_once_with(
        document_id="document-1",
        failed_stage="EXTRACT",
        error_message="Retained source file is missing",
    )
    service.index.delete_by_document_id.assert_not_called()


def test_real_minio_changed_object_fails_before_index_deletion(
    live_minio_storage,
):
    client, storage = live_minio_storage
    expected_data = b"expected source"
    changed_data = b"tampered source"

    assert len(expected_data) == len(changed_data)

    stored = storage.store(
        document_id="document-2",
        filename="lesson.txt",
        data=expected_data,
    )
    object_key = urlparse(
        stored.source_uri
    ).path.lstrip("/")

    client.put_object(
        storage.bucket_name,
        object_key,
        BytesIO(changed_data),
        len(changed_data),
    )

    document = SimpleNamespace(
        document_id="document-2",
        subject_id="subject-1",
        filename="lesson.txt",
        file_type="txt",
        status="INDEXED",
        source_uri=stored.source_uri,
        content_sha256=sha256(
            expected_data
        ).hexdigest(),
        file_size_bytes=len(expected_data),
    )

    service = PDFService.__new__(PDFService)
    service.source_storage = storage
    service.document_repo = Mock()
    service.index = Mock()

    with pytest.raises(
        RetainedSourceValidationError,
        match="checksum does not match",
    ):
        service.rebuild_retained_document(document)

    service.document_repo.mark_failed.assert_called_once_with(
        document_id="document-2",
        failed_stage="EXTRACT",
        error_message=(
            "Retained source checksum does not match"
        ),
    )
    service.index.delete_by_document_id.assert_not_called()
