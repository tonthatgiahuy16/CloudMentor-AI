from pathlib import Path

import pytest

from app.rag import loader as loader_module
from docx import Document as WordDocument
from app.rag.loader import (
    DOCXLoader,
    PDFLoader,
    TextLoader,
)


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    def __init__(self, _path):
        self.pages = [FakePage("first page"), FakePage(None)]


def test_loader_extracts_pages_and_metadata(tmp_path, monkeypatch):
    pdf_path = tmp_path / "lesson.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(loader_module, "PdfReader", FakeReader)

    documents = PDFLoader().load(str(pdf_path), document_id="doc-1", subject_id="subject-1")

    assert [document.text for document in documents] == ["first page", ""]
    assert documents[0].source == "lesson.pdf"
    assert documents[0].page == 1
    assert documents[0].document_id == "doc-1"
    assert documents[0].subject_id == "subject-1"


def test_loader_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        PDFLoader().load(str(tmp_path / "missing.pdf"), document_id="doc-1", subject_id="subject-1")


def test_loader_rejects_non_pdf(tmp_path):
    text_path = tmp_path / "lesson.txt"
    text_path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="PDF"):
        PDFLoader().load(str(text_path), document_id="doc-1", subject_id="subject-1")


def test_text_loader_preserves_exact_line_locations(
    tmp_path,
):
    text_path = tmp_path / "lesson.txt"
    text_path.write_bytes(
        b"first line\r\n\r\nthird line\r\n"
    )

    documents = TextLoader().load(
        str(text_path),
        document_id="doc-1",
        subject_id="subject-1",
    )

    assert len(documents) == 1

    document = documents[0]

    assert document.document_id == "doc-1"
    assert document.subject_id == "subject-1"
    assert document.source == "lesson.txt"
    assert document.text == (
        "first line\n\nthird line"
    )
    assert document.page is None
    assert document.line_range == (1, 3)
    assert document.paragraph_range is None


def test_text_loader_rejects_non_txt(
    tmp_path,
):
    source_path = tmp_path / "lesson.pdf"
    source_path.write_bytes(b"not a text file")

    with pytest.raises(
        ValueError,
        match="TXT",
    ):
        TextLoader().load(
            str(source_path),
            document_id="doc-1",
            subject_id="subject-1",
        )


def test_text_loader_rejects_empty_content(
    tmp_path,
):
    text_path = tmp_path / "empty.txt"
    text_path.write_text(
        " \r\n\t\r\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="empty",
    ):
        TextLoader().load(
            str(text_path),
            document_id="doc-1",
            subject_id="subject-1",
        )


def test_text_loader_rejects_invalid_utf8(
    tmp_path,
):
    text_path = tmp_path / "invalid.txt"
    text_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(
        ValueError,
        match="valid UTF-8",
    ):
        TextLoader().load(
            str(text_path),
            document_id="doc-1",
            subject_id="subject-1",
        )


def test_docx_loader_preserves_exact_paragraph_locations(
    tmp_path,
):
    docx_path = tmp_path / "lesson.docx"

    word_document = WordDocument()
    word_document.add_paragraph(
        "First paragraph"
    )
    word_document.add_paragraph("")
    word_document.add_paragraph(
        "Third paragraph"
    )
    word_document.save(docx_path)

    documents = DOCXLoader().load(
        str(docx_path),
        document_id="doc-1",
        subject_id="subject-1",
    )

    assert len(documents) == 1

    document = documents[0]

    assert document.document_id == "doc-1"
    assert document.subject_id == "subject-1"
    assert document.source == "lesson.docx"
    assert document.text == (
        "First paragraph\n"
        "\n"
        "Third paragraph"
    )
    assert document.page is None
    assert document.line_range is None
    assert document.paragraph_range == (
        1,
        3,
    )


def test_docx_loader_rejects_nonempty_tables(
    tmp_path,
):
    docx_path = tmp_path / "with-table.docx"

    word_document = WordDocument()
    word_document.add_paragraph(
        "Body paragraph"
    )

    table = word_document.add_table(
        rows=1,
        cols=2,
    )
    table.cell(0, 0).text = "Column A"
    table.cell(0, 1).text = "Column B"

    word_document.save(docx_path)

    with pytest.raises(
        ValueError,
        match="DOCX tables are not supported",
    ):
        DOCXLoader().load(
            str(docx_path),
            document_id="doc-1",
            subject_id="subject-1",
        )


def test_docx_loader_rejects_empty_document(
    tmp_path,
):
    docx_path = tmp_path / "empty.docx"

    WordDocument().save(docx_path)

    with pytest.raises(
        ValueError,
        match="DOCX file is empty",
    ):
        DOCXLoader().load(
            str(docx_path),
            document_id="doc-1",
            subject_id="subject-1",
        )


def test_docx_loader_rejects_invalid_container(
    tmp_path,
):
    docx_path = tmp_path / "invalid.docx"
    docx_path.write_bytes(
        b"not a valid DOCX package"
    )

    with pytest.raises(
        ValueError,
        match="DOCX file is not valid",
    ):
        DOCXLoader().load(
            str(docx_path),
            document_id="doc-1",
            subject_id="subject-1",
        )


def test_docx_loader_normalizes_internal_line_breaks(
    tmp_path,
):
    docx_path = tmp_path / "line-breaks.docx"

    word_document = WordDocument()

    first_paragraph = (
        word_document.add_paragraph(
            "First line"
        )
    )
    first_paragraph.add_run().add_break()
    first_paragraph.add_run(
        "same paragraph"
    )

    word_document.add_paragraph(
        "Second paragraph"
    )
    word_document.save(docx_path)

    documents = DOCXLoader().load(
        str(docx_path),
        document_id="doc-1",
        subject_id="subject-1",
    )

    assert documents[0].text == (
        "First line same paragraph\n"
        "Second paragraph"
    )
    assert (
        documents[0].paragraph_range
        == (1, 2)
    )
