from hashlib import sha256

import pytest

from app.storage.source_storage import (
    LocalSourceStorage,
    SourceConflictError,
)


def test_local_storage_stores_source_and_metadata(
    tmp_path,
):
    source_data = b"canonical source content"

    storage = LocalSourceStorage(
        root=tmp_path,
    )

    result = storage.store(
        document_id="document-1",
        filename="lesson.txt",
        data=source_data,
    )

    expected_path = (
        tmp_path
        / "document-1_lesson.txt"
    )

    assert result.source_uri == (
        expected_path.as_posix()
    )
    assert result.content_sha256 == (
        sha256(source_data).hexdigest()
    )
    assert result.file_size_bytes == len(
        source_data
    )
    assert expected_path.read_bytes() == (
        source_data
    )


def test_local_storage_rejects_conflicting_source(
    tmp_path,
):
    storage = LocalSourceStorage(
        root=tmp_path,
    )

    storage.store(
        document_id="document-1",
        filename="lesson.txt",
        data=b"original content",
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

    assert (
        tmp_path
        / "document-1_lesson.txt"
    ).read_bytes() == b"original content"


def test_local_storage_reads_stored_source(
    tmp_path,
):
    source_data = b"retained source"

    storage = LocalSourceStorage(
        root=tmp_path,
    )

    stored = storage.store(
        document_id="document-1",
        filename="lesson.txt",
        data=source_data,
    )

    assert storage.read_bytes(
        stored.source_uri
    ) == source_data
