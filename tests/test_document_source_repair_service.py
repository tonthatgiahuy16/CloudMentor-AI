from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.document_source_repair_service import (
    DocumentSourceRepairService,
)


def test_plan_computes_metadata_without_mutating_state(
    tmp_path,
):
    pdf_data = b"%PDF-1.4\nlegacy document"
    source_path = tmp_path / "BigData_Lec06.pdf"
    source_path.write_bytes(pdf_data)

    document_id = "legacy-document-id"
    document = SimpleNamespace(
        document_id=document_id,
        filename="BigData_Lec06.pdf",
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = document

    upload_dir = tmp_path / "uploads"

    service = DocumentSourceRepairService(
        document_repo=document_repo,
        upload_dir=upload_dir,
    )

    plan = service.plan(
        document_id=document_id,
        source_path=source_path,
    )

    expected_target = (
        upload_dir
        / f"{document_id}_BigData_Lec06.pdf"
    )

    assert plan.document_id == document_id
    assert plan.source_path == source_path
    assert plan.target_path == expected_target
    assert plan.source_uri == expected_target.as_posix()
    assert (
        plan.content_sha256
        == sha256(pdf_data).hexdigest()
    )
    assert plan.file_size_bytes == len(pdf_data)

    assert not expected_target.exists()
    document_repo.attach_source_metadata.assert_not_called()


def test_apply_copies_source_and_attaches_metadata(
    tmp_path,
):
    pdf_data = b"%PDF-1.4\nlegacy document"
    source_path = tmp_path / "BigData_Lec06.pdf"
    source_path.write_bytes(pdf_data)

    document_id = "legacy-document-id"
    document = SimpleNamespace(
        document_id=document_id,
        filename="BigData_Lec06.pdf",
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    )
    repaired_document = SimpleNamespace(
        document_id=document_id,
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = document
    document_repo.attach_source_metadata.return_value = (
        repaired_document
    )

    upload_dir = tmp_path / "uploads"

    service = DocumentSourceRepairService(
        document_repo=document_repo,
        upload_dir=upload_dir,
    )
    plan = service.plan(
        document_id=document_id,
        source_path=source_path,
    )

    result = service.apply(plan)

    assert result is repaired_document
    assert plan.target_path.read_bytes() == pdf_data

    document_repo.attach_source_metadata.assert_called_once_with(
        document_id=document_id,
        source_uri=plan.source_uri,
        content_sha256=plan.content_sha256,
        file_size_bytes=plan.file_size_bytes,
    )


def test_apply_rejects_source_changed_after_plan(
    tmp_path,
):
    source_path = tmp_path / "lesson.pdf"
    source_path.write_bytes(
        b"%PDF-1.4\noriginal"
    )

    document = SimpleNamespace(
        document_id="legacy-document-id",
        filename="lesson.pdf",
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = document

    service = DocumentSourceRepairService(
        document_repo=document_repo,
        upload_dir=tmp_path / "uploads",
    )

    plan = service.plan(
        document_id=document.document_id,
        source_path=source_path,
    )

    source_path.write_bytes(
        b"%PDF-1.4\nchanged"
    )

    with pytest.raises(
        RuntimeError,
        match="Source file changed after planning",
    ):
        service.apply(plan)

    assert not plan.target_path.exists()
    document_repo.attach_source_metadata.assert_not_called()


def test_apply_rejects_conflicting_target_file(
    tmp_path,
):
    source_path = tmp_path / "lesson.pdf"
    source_path.write_bytes(
        b"%PDF-1.4\ncorrect source"
    )

    document = SimpleNamespace(
        document_id="legacy-document-id",
        filename="lesson.pdf",
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = document

    service = DocumentSourceRepairService(
        document_repo=document_repo,
        upload_dir=tmp_path / "uploads",
    )

    plan = service.plan(
        document_id=document.document_id,
        source_path=source_path,
    )

    plan.target_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    conflicting_data = (
        b"%PDF-1.4\nunrelated document"
    )
    plan.target_path.write_bytes(
        conflicting_data
    )

    with pytest.raises(
        RuntimeError,
        match="Target source file conflict",
    ):
        service.apply(plan)

    assert (
        plan.target_path.read_bytes()
        == conflicting_data
    )
    document_repo.attach_source_metadata.assert_not_called()


def test_apply_is_idempotent_when_target_matches(
    tmp_path,
):
    pdf_data = b"%PDF-1.4\nlegacy document"
    source_path = tmp_path / "lesson.pdf"
    source_path.write_bytes(pdf_data)

    document = SimpleNamespace(
        document_id="legacy-document-id",
        filename="lesson.pdf",
        source_uri=None,
        content_sha256=None,
        file_size_bytes=None,
    )

    document_repo = Mock()
    document_repo.get_by_id.return_value = document
    document_repo.attach_source_metadata.return_value = (
        document
    )

    service = DocumentSourceRepairService(
        document_repo=document_repo,
        upload_dir=tmp_path / "uploads",
    )
    plan = service.plan(
        document_id=document.document_id,
        source_path=source_path,
    )

    service.apply(plan)
    service.apply(plan)

    assert plan.target_path.read_bytes() == pdf_data
    assert (
        document_repo
        .attach_source_metadata
        .call_count
        == 2
    )
