import pytest
from unittest.mock import Mock

from app.pipeline import (
    extract_pipeline as extract_pipeline_module,
)
from app.pipeline.extract_pipeline import ExtractPipeline


def test_extract_pipeline_selects_text_loader_from_bytes(
    monkeypatch,
):
    pdf_loader = Mock()
    text_loader = Mock()
    expected_documents = [object()]
    source_data = b"first line\nsecond line"

    text_loader.load.return_value = (
        expected_documents
    )

    monkeypatch.setattr(
        extract_pipeline_module,
        "PDFLoader",
        lambda: pdf_loader,
    )
    monkeypatch.setattr(
        extract_pipeline_module,
        "TextLoader",
        lambda: text_loader,
        raising=False,
    )

    result = ExtractPipeline().run(
        source_data=source_data,
        filename="lesson.txt",
        file_type="txt",
        document_id="document-1",
        subject_id="subject-1",
    )

    assert result == expected_documents
    text_loader.load.assert_called_once_with(
        source_data,
        filename="lesson.txt",
        document_id="document-1",
        subject_id="subject-1",
    )
    pdf_loader.load.assert_not_called()


def test_extract_pipeline_keeps_pdf_loader(
    monkeypatch,
):
    pdf_loader = Mock()
    text_loader = Mock()
    expected_documents = [object()]
    source_data = b"%PDF-1.4"

    pdf_loader.load.return_value = (
        expected_documents
    )

    monkeypatch.setattr(
        extract_pipeline_module,
        "PDFLoader",
        lambda: pdf_loader,
    )
    monkeypatch.setattr(
        extract_pipeline_module,
        "TextLoader",
        lambda: text_loader,
    )

    result = ExtractPipeline().run(
        source_data=source_data,
        filename="lesson.PDF",
        file_type="PDF",
        document_id="document-1",
        subject_id="subject-1",
    )

    assert result == expected_documents
    pdf_loader.load.assert_called_once_with(
        source_data,
        filename="lesson.PDF",
        document_id="document-1",
        subject_id="subject-1",
    )
    text_loader.load.assert_not_called()


def test_extract_pipeline_rejects_unsupported_type():
    pipeline = ExtractPipeline()

    with pytest.raises(
        ValueError,
        match="Unsupported document type: .csv",
    ):
        pipeline.run(
            source_data=b"csv content",
            filename="lesson.csv",
            file_type="csv",
            document_id="document-1",
            subject_id="subject-1",
        )


def test_extract_pipeline_selects_docx_loader(
    monkeypatch,
):
    pdf_loader = Mock()
    text_loader = Mock()
    docx_loader = Mock()
    expected_documents = [object()]
    source_data = b"DOCX package bytes"

    docx_loader.load.return_value = (
        expected_documents
    )

    monkeypatch.setattr(
        extract_pipeline_module,
        "PDFLoader",
        lambda: pdf_loader,
    )
    monkeypatch.setattr(
        extract_pipeline_module,
        "TextLoader",
        lambda: text_loader,
    )
    monkeypatch.setattr(
        extract_pipeline_module,
        "DOCXLoader",
        lambda: docx_loader,
        raising=False,
    )

    result = ExtractPipeline().run(
        source_data=source_data,
        filename="lesson.DOCX",
        file_type=".DOCX",
        document_id="document-1",
        subject_id="subject-1",
    )

    assert result == expected_documents
    docx_loader.load.assert_called_once_with(
        source_data,
        filename="lesson.DOCX",
        document_id="document-1",
        subject_id="subject-1",
    )
    pdf_loader.load.assert_not_called()
    text_loader.load.assert_not_called()
