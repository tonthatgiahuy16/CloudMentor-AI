import pytest

from hashlib import sha256
from unittest.mock import Mock

from app.storage.minio_source_storage import (
    MinioSourceStorage,
)
from app.storage.source_storage import (
    SourceConflictError,
    SourceNotFoundError,
)

from minio.error import S3Error


def test_minio_storage_builds_stable_source_uri_without_writing():
    client = Mock()
    storage = MinioSourceStorage(
        client=client,
        bucket_name="cloudmentor",
    )

    source_uri = storage.source_uri_for(
        document_id="document-1",
        filename="Lesson.TXT",
    )

    assert source_uri == (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )
    client.assert_not_called()


def test_minio_storage_stores_source_and_metadata():
    source_data = b"canonical source content"
    client = Mock()

    storage = MinioSourceStorage(
        client=client,
        bucket_name="cloudmentor",
    )

    storage.read_bytes = Mock(
        side_effect=SourceNotFoundError(
            "Stored source does not exist"
        )
    )

    result = storage.store(
        document_id="document-1",
        filename="Lesson.TXT",
        data=source_data,
    )

    assert result.source_uri == (
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )
    assert result.content_sha256 == (
        sha256(source_data).hexdigest()
    )
    assert result.file_size_bytes == len(
        source_data
    )

    client.put_object.assert_called_once()

    (
        bucket_name,
        object_key,
        stream,
        length,
    ) = client.put_object.call_args.args[:4]

    assert bucket_name == "cloudmentor"
    assert object_key == (
        "documents/document-1/source.txt"
    )
    assert stream.getvalue() == source_data
    assert length == len(source_data)


def test_minio_storage_reads_stored_source():
    source_data = b"retained source"
    client = Mock()
    response = Mock()
    response.read.return_value = source_data
    client.get_object.return_value = response

    storage = MinioSourceStorage(
        client=client,
        bucket_name="cloudmentor",
    )

    result = storage.read_bytes(
        "minio://cloudmentor/"
        "documents/document-1/source.txt"
    )

    assert result == source_data

    client.get_object.assert_called_once_with(
        "cloudmentor",
        "documents/document-1/source.txt",
    )
    response.close.assert_called_once_with()
    response.release_conn.assert_called_once_with()

def test_minio_storage_reuses_same_key_with_same_content():
    source_data = b"canonical source content"
    client = Mock()

    storage = MinioSourceStorage(
        client=client,
        bucket_name="cloudmentor",
    )
    storage.read_bytes = Mock(
        side_effect=[
            SourceNotFoundError(
                "Stored source does not exist"
            ),
            source_data,
        ]
    )

    first_result = storage.store(
        document_id="document-1",
        filename="lesson.txt",
        data=source_data,
    )
    second_result = storage.store(
        document_id="document-1",
        filename="lesson.txt",
        data=source_data,
    )

    assert second_result == first_result
    assert client.put_object.call_count == 1


def test_minio_storage_rejects_conflicting_source():
    client = Mock()

    storage = MinioSourceStorage(
        client=client,
        bucket_name="cloudmentor",
    )
    storage.read_bytes = Mock(
        return_value=b"original content"
    )

    with pytest.raises(
        SourceConflictError,
        match="different content",
    ):
        storage.store(
            document_id="document-1",
            filename="lesson.txt",
            data=b"changed content",
        )

    client.put_object.assert_not_called()


def test_minio_storage_translates_missing_object_error():
    client = Mock()
    client.get_object.side_effect = S3Error(
        response=None,
        code="NoSuchKey",
        message="The specified key does not exist",
        resource=(
            "/cloudmentor/documents/"
            "document-1/source.txt"
        ),
        request_id="request-1",
        host_id="host-1",
    )

    storage = MinioSourceStorage(
        client=client,
        bucket_name="cloudmentor",
    )

    with pytest.raises(
        SourceNotFoundError,
        match="does not exist",
    ):
        storage.read_bytes(
            "minio://cloudmentor/"
            "documents/document-1/source.txt"
        )
