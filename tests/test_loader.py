from pathlib import Path

import pytest

from app.rag import loader as loader_module
from app.rag.loader import PDFLoader


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
