import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db_models.document import Document
from app.db_models.subject import Subject
from app.repos.document_repository import (
    ActiveDocumentConflictError,
    DocumentRepository,
)

pytestmark = pytest.mark.skipif(
    os.getenv(
        "CLOUDMENTOR_RUN_POSTGRES_INTEGRATION"
    ) != "1",
    reason=(
        "Set CLOUDMENTOR_RUN_POSTGRES_INTEGRATION=1"
    ),
)


@pytest.fixture
def postgres_session_factory():
    container_name = (
        "cloudmentor-postgres-concurrent-"
        + uuid4().hex
    )
    database_name = "cloudmentor_test"
    database_user = "test_" + uuid4().hex[:12]
    database_password = uuid4().hex + uuid4().hex
    image = os.getenv(
        "POSTGRES_INTEGRATION_IMAGE",
        "postgres:16-alpine",
    )
    engine = None

    started = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--name",
            container_name,
            "--publish",
            "127.0.0.1::5432",
            "--env",
            f"POSTGRES_DB={database_name}",
            "--env",
            f"POSTGRES_USER={database_user}",
            "--env",
            f"POSTGRES_PASSWORD={database_password}",
            image,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert started.returncode == 0, (
        "Could not start PostgreSQL integration container"
    )

    try:
        port_result = subprocess.run(
            ["docker", "port", container_name, "5432/tcp"],
            check=True,
            capture_output=True,
            text=True,
        )
        matched_port = re.search(
            r"127\.0\.0\.1:(\d+)",
            port_result.stdout,
        )
        assert matched_port is not None, (
            "Could not determine PostgreSQL host port"
        )
        port = matched_port.group(1)

        database_url = (
            f"postgresql+psycopg://{database_user}:"
            f"{database_password}@127.0.0.1:{port}/"
            f"{database_name}"
        )

        deadline = time.monotonic() + 30
        while True:
            probe_engine = create_engine(database_url)
            try:
                with probe_engine.connect():
                    break
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.5)
            finally:
                probe_engine.dispose()

        migration_environment = os.environ.copy()
        migration_environment["DATABASE_URL"] = database_url

        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=False,
            capture_output=True,
            text=True,
            env=migration_environment,
        )
        assert migrated.returncode == 0, (
            "Alembic migration failed for PostgreSQL integration"
        )

        engine = create_engine(database_url)
        yield sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
        )
    finally:
        if engine is not None:
            engine.dispose()

        subprocess.run(
            ["docker", "rm", "--force", container_name],
            check=False,
            capture_output=True,
            text=True,
        )


def test_two_concurrent_reservations_keep_one_document(
    postgres_session_factory,
):
    setup_session = postgres_session_factory()
    subject = Subject(
        subject_id=str(uuid4()),
        name=f"Concurrent subject {uuid4()}",
    )
    setup_session.add(subject)
    setup_session.commit()
    subject_id = subject.subject_id
    setup_session.close()

    content_sha256 = "f" * 64
    barrier = Barrier(2)

    def reserve_document():
        session = postgres_session_factory()
        repository = DocumentRepository(session)

        try:
            barrier.wait(timeout=10)

            document = repository.create(
                document_id=str(uuid4()),
                subject_id=subject_id,
                filename="same-content.txt",
                file_type="txt",
                chapter=None,
                source_uri=None,
                content_sha256=content_sha256,
                file_size_bytes=10,
            )

            return ("created", document.document_id)

        except ActiveDocumentConflictError as exc:
            return (
                "conflict",
                exc.document.document_id,
            )

        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(reserve_document)
            for _ in range(2)
        ]
        results = [future.result() for future in futures]

    created_ids = [
        document_id
        for result, document_id in results
        if result == "created"
    ]
    conflict_ids = [
        document_id
        for result, document_id in results
        if result == "conflict"
    ]

    assert len(created_ids) == 1
    assert conflict_ids == created_ids

    verification_session = postgres_session_factory()
    try:
        active_documents = (
            verification_session.query(Document)
            .filter(
                Document.subject_id == subject_id,
                Document.content_sha256 == content_sha256,
                Document.status != "DELETED",
            )
            .all()
        )
    finally:
        verification_session.close()

    assert [
        document.document_id
        for document in active_documents
    ] == created_ids
