from app.storage.source_storage import (
    LocalSourceStorage,
)
from app.storage.source_storage_factory import (
    create_local_source_storage,
    create_minio_source_storage,
    create_source_storage,
)
from unittest.mock import Mock
import app.storage.source_storage_factory as factory_module

from app.storage.minio_source_storage import (
    MinioSourceStorage,
)

def test_factory_creates_local_storage(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "CLOUDMENTOR_SOURCE_STORAGE",
        "local",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_UPLOAD_DIR",
        str(tmp_path),
    )

    storage = create_source_storage()

    assert isinstance(
        storage,
        LocalSourceStorage,
    )
    assert storage.root == tmp_path


def test_factory_creates_minio_storage(
    monkeypatch,
):
    client = Mock()
    client_factory = Mock(
        return_value=client
    )

    monkeypatch.setenv(
        "CLOUDMENTOR_SOURCE_STORAGE",
        "minio",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_ENDPOINT",
        "localhost:9000",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_ACCESS_KEY",
        "test-access-key",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_SECRET_KEY",
        "test-secret-key",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_BUCKET",
        "cloudmentor-sources",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_SECURE",
        "false",
    )
    monkeypatch.setattr(
        factory_module,
        "Minio",
        client_factory,
        raising=False,
    )

    storage = create_source_storage()

    assert isinstance(
        storage,
        MinioSourceStorage,
    )
    assert storage.client is client
    assert (
        storage.bucket_name
        == "cloudmentor-sources"
    )

    client_factory.assert_called_once_with(
        "localhost:9000",
        access_key="test-access-key",
        secret_key="test-secret-key",
        secure=False,
    )


def test_factory_creates_explicit_migration_storages(
    monkeypatch,
    tmp_path,
):
    client = Mock()
    client_factory = Mock(
        return_value=client
    )

    monkeypatch.setenv(
        "CLOUDMENTOR_UPLOAD_DIR",
        str(tmp_path),
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_ENDPOINT",
        "localhost:9000",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_ACCESS_KEY",
        "test-access-key",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_SECRET_KEY",
        "test-secret-key",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_BUCKET",
        "cloudmentor-sources",
    )
    monkeypatch.setenv(
        "CLOUDMENTOR_MINIO_SECURE",
        "false",
    )
    monkeypatch.setattr(
        factory_module,
        "Minio",
        client_factory,
    )

    local_storage = (
        create_local_source_storage()
    )
    minio_storage = (
        create_minio_source_storage()
    )

    assert isinstance(
        local_storage,
        LocalSourceStorage,
    )
    assert local_storage.root == tmp_path

    assert isinstance(
        minio_storage,
        MinioSourceStorage,
    )
    assert minio_storage.client is client
    assert (
        minio_storage.bucket_name
        == "cloudmentor-sources"
    )
