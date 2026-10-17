from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from app.services.pdf_service import PDFService


def test_retry_failed_document_reuses_source_and_document_id(
    tmp_path,
):
    pdf_data = b"%PDF-1.4\nretained source"
    source_path = tmp_path / "retained.pdf"
    source_path.write_bytes(pdf_data)

    document = SimpleNamespace(
        document_id="failed-document-id",
        subject_id="subject-id",
        filename="lesson.pdf",
        status="FAILED",
        source_uri=source_path.as_posix(),
        content_sha256=sha256(pdf_data).hexdigest(),
        file_size_bytes=len(pdf_data),
    )

    service = PDFService.__new__(PDFService)

    service.document_repo = Mock()
    service.extract = Mock()
    service.transform = Mock()
    service.chunk = Mock()
    service.embedding = Mock()
    service.index = Mock()

    extracted = [object()]
    transformed = [object()]
    chunks = [object(), object()]
    embeddings = object()

    service.extract.run.return_value = extracted
    service.transform.run.return_value = transformed
    service.chunk.run.return_value = chunks
    service.embedding.run.return_value = embeddings

    result = service.retry_failed_document(document)

    assert result == 2

    service.document_repo.create.assert_not_called()
    service.index.delete_by_document_id.assert_called_once_with(
        "failed-document-id"
    )
    service.document_repo.mark_processing.assert_called_once_with(
        "failed-document-id"
    )
    service.extract.run.assert_called_once_with(
        source_path.as_posix(),
        "failed-document-id",
        "subject-id",
    )
    service.transform.run.assert_called_once_with(
        extracted
    )
    service.chunk.run.assert_called_once_with(
        transformed
    )
    service.embedding.run.assert_called_once_with(
        chunks
    )
    service.index.run.assert_called_once_with(
        chunks,
        embeddings,
    )
    service.document_repo.mark_indexed.assert_called_once_with(
        "failed-document-id"
    )


def test_retry_rejects_source_with_changed_content(
    tmp_path,
):
    original_data = b"%PDF-1.4\noriginal"
    changed_data = b"%PDF-1.4\ntampered"

    assert len(original_data) == len(changed_data)

    source_path = tmp_path / "retained.pdf"
    source_path.write_bytes(changed_data)

    document = SimpleNamespace(
        document_id="failed-document-id",
        subject_id="subject-id",
        filename="lesson.pdf",
        status="FAILED",
        source_uri=source_path.as_posix(),
        content_sha256=sha256(
            original_data
        ).hexdigest(),
        file_size_bytes=len(original_data),
    )

    service = PDFService.__new__(PDFService)
    service.document_repo = Mock()

    with pytest.raises(
        RuntimeError,
        match="checksum does not match",
    ):
        service.retry_failed_document(document)

    service.document_repo.mark_processing.assert_not_called()


def test_processing_failure_records_failed_stage():
    service = PDFService.__new__(PDFService)

    service.document_repo = Mock()
    service.extract = Mock()
    service.transform = Mock()
    service.chunk = Mock()
    service.embedding = Mock()
    service.index = Mock()

    extracted = [object()]

    service.extract.run.return_value = extracted
    service.transform.run.side_effect = RuntimeError(
        "Controlled transform failure"
    )

    with pytest.raises(
        RuntimeError,
        match="Controlled transform failure",
    ):
        service._process_document(
            file_path="retained.pdf",
            document_id="failed-document-id",
            subject_id="subject-id",
        )

    service.document_repo.mark_processing.assert_called_once_with(
        "failed-document-id"
    )
    service.document_repo.mark_failed.assert_called_once_with(
        document_id="failed-document-id",
        failed_stage="TRANSFORM",
        error_message="Controlled transform failure",
    )
    service.document_repo.mark_indexed.assert_not_called()
    service.chunk.run.assert_not_called()
